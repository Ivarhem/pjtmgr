from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.rack import RackRead, RackUpdate
from app.modules.infra.services.layout_service import delete_rack, update_rack


router = APIRouter(tags=["infra-racks"])


@router.patch("/api/v1/racks/{rack_id}", response_model=RackRead)
def update_rack_endpoint(
    rack_id: int,
    payload: RackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RackRead:
    return update_rack(db, rack_id, payload, current_user)


@router.delete("/api/v1/racks/{rack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rack_endpoint(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_rack(db, rack_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
