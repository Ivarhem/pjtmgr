from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.ip_subnet import (
    IpSubnetCreate,
    IpSubnetRead,
    IpSubnetUpdate,
)
from app.modules.infra.services.network_service import (
    create_subnet,
    delete_subnet,
    get_subnet,
    list_subnets,
    update_subnet,
)


router = APIRouter(prefix="/api/v1/ip-subnets", tags=["infra-ip-subnets"])


@router.get("", response_model=list[IpSubnetRead])
def list_subnets_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IpSubnetRead]:
    return list_subnets(db, partner_id)


@router.post(
    "",
    response_model=IpSubnetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subnet_endpoint(
    payload: IpSubnetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IpSubnetRead:
    return create_subnet(db, payload, current_user)


@router.get("/{subnet_id}", response_model=IpSubnetRead)
def get_subnet_endpoint(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IpSubnetRead:
    return get_subnet(db, subnet_id)


@router.patch("/{subnet_id}", response_model=IpSubnetRead)
def update_subnet_endpoint(
    subnet_id: int,
    payload: IpSubnetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IpSubnetRead:
    return update_subnet(db, subnet_id, payload, current_user)


@router.delete("/{subnet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subnet_endpoint(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_subnet(db, subnet_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
