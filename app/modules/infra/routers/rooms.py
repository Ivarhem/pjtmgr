from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.rack import RackCreate, RackRead
from app.modules.infra.schemas.room import RoomRead, RoomUpdate
from app.modules.infra.services.layout_service import (
    create_rack,
    delete_room,
    list_racks,
    update_room,
)


router = APIRouter(tags=["infra-rooms"])


@router.patch("/api/v1/rooms/{room_id}", response_model=RoomRead)
def update_room_endpoint(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomRead:
    return update_room(db, room_id, payload, current_user)


@router.delete("/api/v1/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_room(db, room_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/rooms/{room_id}/racks", response_model=list[RackRead])
def list_room_racks_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RackRead]:
    return list_racks(db, room_id)


@router.post("/api/v1/rooms/{room_id}/racks", response_model=RackRead, status_code=status.HTTP_201_CREATED)
def create_room_rack_endpoint(
    room_id: int,
    payload: RackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RackRead:
    payload.room_id = room_id
    return create_rack(db, payload, current_user)
