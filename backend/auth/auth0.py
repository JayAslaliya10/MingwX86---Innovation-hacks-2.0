import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.connection import get_db
from backend.database.models import User

settings = get_settings()
bearer_scheme = HTTPBearer()

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
        if not rsa_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_api_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token error: {str(e)}")


async def get_current_user(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> User:
    auth0_id = payload.get("sub")
    if not auth0_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.query(User).filter(User.auth0_id == auth0_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not registered")
    return user
