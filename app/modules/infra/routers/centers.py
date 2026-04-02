from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.center import CenterCreate, CenterRead, CenterUpdate
from app.modules.infra.schemas.room import RoomCreate, RoomRead
from app.modules.infra.services.layout_service import (
    create_center,
    create_room,
    delete_center,
    list_centers,
    list_rooms,
    update_center,
)


router = APIRouter(tags=["infra-centers"])


@router.get("/api/v1/centers", response_model=list[CenterRead])
def list_centers_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CenterRead]:
    return list_centers(db, partner_id)


@router.post("/api/v1/centers", response_model=CenterRead, status_code=status.HTTP_201_CREATED)
def create_center_endpoint(
    payload: CenterCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CenterRead:
    return create_center(db, payload, current_user)


@router.patch("/api/v1/centers/{center_id}", response_model=CenterRead)
def update_center_endpoint(
    center_id: int,
    payload: CenterUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CenterRead:
    return update_center(db, center_id, payload, current_user)


@router.delete("/api/v1/centers/{center_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_center_endpoint(
    center_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_center(db, center_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/centers/{center_id}/rooms", response_model=list[RoomRead])
def list_center_rooms_endpoint(
    center_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RoomRead]:
    return list_rooms(db, center_id)


@router.post("/api/v1/centers/{center_id}/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def create_center_room_endpoint(
    center_id: int,
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RoomRead:
    payload.center_id = center_id
    return create_room(db, payload, current_user)
