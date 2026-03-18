"""Accounting module aggregated router package."""
from fastapi import APIRouter

from app.modules.accounting.routers.contracts import router as contracts_router
from app.modules.accounting.routers.contract_contacts import router as contract_contacts_router
from app.modules.accounting.routers.contract_types import router as contract_types_router
from app.modules.accounting.routers.dashboard import router as dashboard_router
from app.modules.accounting.routers.excel import router as excel_router
from app.modules.accounting.routers.forecasts import router as forecasts_router
from app.modules.accounting.routers.receipt_matches import router as receipt_matches_router
from app.modules.accounting.routers.receipts import router as receipts_router
from app.modules.accounting.routers.reports import router as reports_router
from app.modules.accounting.routers.transaction_lines import router as transaction_lines_router
from app.modules.accounting.routers.pages import router as pages_router

api_router = APIRouter()
api_router.include_router(dashboard_router)
api_router.include_router(contracts_router)
api_router.include_router(contract_contacts_router)
api_router.include_router(contract_types_router)
api_router.include_router(forecasts_router)
api_router.include_router(transaction_lines_router)
api_router.include_router(receipts_router)
api_router.include_router(receipt_matches_router)
api_router.include_router(excel_router)
api_router.include_router(reports_router)
api_router.include_router(pages_router)

# Re-export individual routers for backward compatibility
from app.modules.accounting.routers import contracts  # noqa: E402, F811
from app.modules.accounting.routers import contract_contacts  # noqa: E402, F811
from app.modules.accounting.routers import contract_types  # noqa: E402, F811
from app.modules.accounting.routers import dashboard  # noqa: E402, F811
from app.modules.accounting.routers import excel  # noqa: E402, F811
from app.modules.accounting.routers import forecasts  # noqa: E402, F811
from app.modules.accounting.routers import receipt_matches  # noqa: E402, F811
from app.modules.accounting.routers import receipts  # noqa: E402, F811
from app.modules.accounting.routers import reports  # noqa: E402, F811
from app.modules.accounting.routers import transaction_lines  # noqa: E402, F811

__all__ = [
    "api_router",
    "contracts",
    "contract_contacts",
    "contract_types",
    "dashboard",
    "excel",
    "forecasts",
    "receipt_matches",
    "receipts",
    "reports",
    "transaction_lines",
]
