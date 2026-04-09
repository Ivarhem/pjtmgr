from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.services.code_generation_service import (
    preview_period_codes,
    generate_period_codes,
)

router = APIRouter(tags=["infra-code-generation"])


@router.get("/api/v1/contract-periods/{period_id}/preview-codes")
def preview_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return preview_period_codes(db, period_id, target)


@router.post("/api/v1/contract-periods/{period_id}/generate-codes")
def generate_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return generate_period_codes(db, period_id, target)
