from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services import user_preference as svc

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


@router.get("/{key}")
def get_preference(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    value = svc.get_preference(db, current_user.id, key)
    return {"key": key, "value": value}


@router.patch("/{key}")
def update_preference(
    key: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    svc.update_preference(db, current_user.id, key, body.get("value"))
    return {"key": key, "value": body.get("value")}
