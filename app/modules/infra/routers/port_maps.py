from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
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


router = APIRouter(tags=["infra-port-maps"])


@router.get(
    "/api/v1/projects/{project_id}/port-maps",
    response_model=list[PortMapRead],
)
def list_port_maps_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PortMapRead]:
    return list_port_maps(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/port-maps",
    response_model=PortMapRead,
    status_code=status.HTTP_201_CREATED,
)
def create_port_map_endpoint(
    project_id: int,
    payload: PortMapCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    payload.project_id = project_id
    return create_port_map(db, payload, current_user)


@router.get(
    "/api/v1/port-maps/{port_map_id}",
    response_model=PortMapRead,
)
def get_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    return get_port_map(db, port_map_id)


@router.patch(
    "/api/v1/port-maps/{port_map_id}",
    response_model=PortMapRead,
)
def update_port_map_endpoint(
    port_map_id: int,
    payload: PortMapUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    return update_port_map(db, port_map_id, payload, current_user)


@router.delete(
    "/api/v1/port-maps/{port_map_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_port_map(db, port_map_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
