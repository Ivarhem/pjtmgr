from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.setting import SettingRead, SettingUpdate
from app.services import setting as svc

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=SettingRead)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SettingRead:
    return SettingRead(
        org_name=svc.get_setting(db, "org_name"),
        password_min_length=svc.get_password_min_length(db),
    )


@router.patch("", response_model=SettingRead)
def update_settings(
    data: SettingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SettingRead:
    svc.update_settings(db, data)
    return SettingRead(
        org_name=svc.get_setting(db, "org_name"),
        password_min_length=svc.get_password_min_length(db),
    )
