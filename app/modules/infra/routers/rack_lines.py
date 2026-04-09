from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.rack_line import RackLineCreate, RackLineUpdate
from app.modules.infra.services.layout_service import (
    create_rack_line,
    delete_rack_line,
    list_rack_lines,
    update_rack_line,
)

router = APIRouter(tags=["infra-rack-lines"])


@router.get("/api/v1/rooms/{room_id}/rack-lines")
def list_rack_lines_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_rack_lines(db, room_id)


@router.post("/api/v1/rooms/{room_id}/rack-lines", status_code=status.HTTP_201_CREATED)
def create_rack_line_endpoint(
    room_id: int,
    payload: RackLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_rack_line(db, room_id, payload, current_user)


@router.patch("/api/v1/rack-lines/{line_id}")
def update_rack_line_endpoint(
    line_id: int,
    payload: RackLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_rack_line(db, line_id, payload, current_user)


@router.delete("/api/v1/rack-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rack_line_endpoint(
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_rack_line(db, line_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
