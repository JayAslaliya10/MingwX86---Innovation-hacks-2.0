from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.auth.auth0 import verify_token, get_current_user
from backend.database.connection import get_db
from backend.database.models import User, HealthCardPolicyMap, PolicyUpdateNotification
from backend.database.schemas import UserRegister, UserOut, HealthCardLookupOut, PolicyUpdateNotificationOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserOut)
async def register_user(
    body: UserRegister,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    auth0_id = payload.get("sub")
    existing = db.query(User).filter(User.auth0_id == auth0_id).first()
    if existing:
        return existing

    user = User(
        auth0_id=auth0_id,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        health_card_number=body.health_card_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/login")
async def on_login(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Called by frontend on every login.
    Updates last_login and triggers background change detection.
    """
    current_user.last_login = datetime.utcnow()
    db.commit()

    # Trigger change detection in background
    background_tasks.add_task(_run_change_detection, current_user.id, db)

    return {"status": "ok", "last_login": current_user.last_login}


async def _run_change_detection(user_id, db: Session):
    """Background task: check all user-associated policies for updates."""
    try:
        from backend.scraping.change_detector import run_change_detection_for_user
        await run_change_detection_for_user(user_id, db)
    except Exception as e:
        print(f"[change_detection] Error for user {user_id}: {e}")


@router.get("/notifications", response_model=list[PolicyUpdateNotificationOut])
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.database.models import PolicyUpdate, Policy, Payer
    notifications = (
        db.query(PolicyUpdateNotification)
        .filter(PolicyUpdateNotification.user_id == current_user.id)
        .order_by(PolicyUpdateNotification.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for n in notifications:
        update = db.query(PolicyUpdate).filter(PolicyUpdate.id == n.update_id).first()
        policy = db.query(Policy).filter(Policy.id == update.policy_id).first() if update else None
        payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
        result.append(PolicyUpdateNotificationOut(
            id=n.id,
            update_id=n.update_id,
            policy_id=update.policy_id if update else None,
            policy_title=policy.title if policy else None,
            payer_name=payer.name if payer else None,
            diff_summary=update.diff_summary if update else None,
            change_class=update.change_class if update else None,
            effective_from=update.effective_from if update else None,
            detected_at=n.created_at,
            seen=n.seen,
        ))
    return result


@router.patch("/notifications/{notification_id}/seen")
async def mark_notification_seen(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.query(PolicyUpdateNotification).filter(
        PolicyUpdateNotification.id == notification_id,
        PolicyUpdateNotification.user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.seen = True
    db.commit()
    return {"status": "ok"}


@router.get("/health-card", response_model=HealthCardLookupOut)
async def lookup_health_card(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.health_card_number:
        raise HTTPException(status_code=400, detail="No health card number on file")
    mapping = db.query(HealthCardPolicyMap).filter(
        HealthCardPolicyMap.health_card_number == current_user.health_card_number
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Health card number not found in system")
    return mapping
