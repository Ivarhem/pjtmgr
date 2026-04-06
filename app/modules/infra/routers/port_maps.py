from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.port_map import (
    PortMapCreate,
    PortMapRead,
    PortMapUpdate,
)
from app.modules.infra.services.network_service import (
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps,
    update_port_map,
)


router = APIRouter(prefix="/api/v1/port-maps", tags=["infra-port-maps"])


@router.get("", response_model=list[PortMapRead])
def list_port_maps_endpoint(
    partner_id: int,
    period_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortMapRead]:
    return list_port_maps(db, partner_id, period_id)


@router.post(
    "",
    response_model=PortMapRead,
    status_code=status.HTTP_201_CREATED,
)
def create_port_map_endpoint(
    payload: PortMapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortMapRead:
    return create_port_map(db, payload, current_user)


@router.get("/{port_map_id}", response_model=PortMapRead)
def get_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortMapRead:
    return get_port_map(db, port_map_id)


@router.patch("/{port_map_id}", response_model=PortMapRead)
def update_port_map_endpoint(
    port_map_id: int,
    payload: PortMapUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortMapRead:
    return update_port_map(db, port_map_id, payload, current_user)


@router.delete("/{port_map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_port_map(db, port_map_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
