from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql://medpolicy:medpolicy123@localhost:5432/medpolicydb"
    postgres_user: str = "medpolicy"
    postgres_password: str = "medpolicy123"
    postgres_db: str = "medpolicydb"

    # Auth0
    auth0_domain: str = "your-tenant.us.auth0.com"
    auth0_api_audience: str = "https://your-api-audience"
    auth0_client_id: str = "your-auth0-client-id"
    auth0_client_secret: str = "your-auth0-client-secret"

    # Gemini
    gemini_api_key: str = "your-gemini-api-key"

    # LlamaParse
    llama_cloud_api_key: str = "your-llama-cloud-api-key"

    # RxNorm
    rxnorm_api_base: str = "https://rxnav.nlm.nih.gov/REST"

    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
