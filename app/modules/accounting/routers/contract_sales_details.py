from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth.dependencies import get_current_user, require_module_access
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.contract_sales_detail import (
    ContractSalesDetailRead,
    ContractSalesDetailUpdate,
)
from app.modules.accounting.services import contract_sales_detail as svc

router = APIRouter(prefix="/api/v1/contract-periods", tags=["contract-sales-details"])


@router.get("/{period_id}/sales-detail", response_model=ContractSalesDetailRead)
def get_sales_detail(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractSalesDetailRead:
    return svc.get_or_create_sales_detail(db, period_id, current_user=current_user)


@router.patch(
    "/{period_id}/sales-detail",
    response_model=ContractSalesDetailRead,
    dependencies=[require_module_access("accounting", "full")],
)
def update_sales_detail(
    period_id: int,
    data: ContractSalesDetailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractSalesDetailRead:
    return svc.update_sales_detail(db, period_id, data, current_user=current_user)
