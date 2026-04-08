from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.user import User
from app.modules.infra.models.center import Center
from app.modules.infra.models.room import Room
from app.modules.infra.services.code_generation_service import (
    generate_rack_codes,
    preview_rack_codes,
)

router = APIRouter(tags=["infra-code-generation"])


@router.get("/api/v1/contract-periods/{period_id}/preview-codes")
def preview_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period = db.get(ContractPeriod, period_id)
    if not period:
        raise NotFoundError("ContractPeriod not found")
    template = (
        period.rack_project_code_template if target == "rack" else period.asset_project_code_template
    )
    if not template:
        return {"template": None, "changes": [], "summary": {"total": 0, "will_update": 0, "skipped": 0}}
    room_ids = _get_period_room_ids(db, period)
    return preview_rack_codes(db, template, room_ids)


@router.post("/api/v1/contract-periods/{period_id}/generate-codes")
def generate_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period = db.get(ContractPeriod, period_id)
    if not period:
        raise NotFoundError("ContractPeriod not found")
    template = (
        period.rack_project_code_template if target == "rack" else period.asset_project_code_template
    )
    if not template:
        raise BusinessRuleError("프로젝트코드 템플릿이 설정되지 않았습니다.", status_code=422)
    room_ids = _get_period_room_ids(db, period)
    return generate_rack_codes(db, template, room_ids)


def _get_period_room_ids(db: Session, period: ContractPeriod) -> list[int]:
    centers = list(db.scalars(select(Center).where(Center.partner_id == period.partner_id)))
    room_ids = []
    for center in centers:
        rooms = list(db.scalars(select(Room.id).where(Room.center_id == center.id)))
        room_ids.extend(rooms)
    return room_ids
