from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.setting import SettingsRead, SettingsUpdate
from app.services import setting as svc

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SettingsRead(org_name=svc.get_setting(db, "org_name"))


@router.patch("", response_model=SettingsRead)
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if data.org_name is not None:
        svc.update_setting(db, "org_name", data.org_name or None)
    return SettingsRead(org_name=svc.get_setting(db, "org_name"))
