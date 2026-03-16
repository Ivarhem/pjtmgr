import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.authorization import check_contract_access
from app.models.user import User
from app.services import report as svc

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _default_date_from() -> str:
    return f"{datetime.date.today().year}-01"


def _default_date_to() -> str:
    return f"{datetime.date.today().year}-12"


# ── 공통 필터 파라미터 → ReportFilter ────────────────────────────


def _make_filter(
    date_from: str | None,
    date_to: str | None,
    owner_id: list[int] | None,
    department: list[str] | None,
    contract_type: list[str] | None,
    stage: list[str] | None,
) -> svc.ReportFilter:
    return svc._build_filter(
        date_from or _default_date_from(),
        date_to or _default_date_to(),
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        stage=stage,
    )


# ═══ 보고서 1: 요약 현황 ═════════════════════════════════════════


@router.get("/summary")
def get_summary(
    date_from: str | None = Query(None, description="시작월 (YYYY-MM)"),
    date_to: str | None = Query(None, description="종료월 (YYYY-MM)"),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """요약 현황 데이터 조회."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    return svc.get_summary(db, filt, current_user=current_user)


@router.get("/summary/export")
def export_summary(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """요약 현황 Excel 다운로드."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    content = svc.export_summary(db, filt, current_user=current_user)
    return Response(content=content, media_type=XLSX_MEDIA,
                    headers={"Content-Disposition": "attachment; filename=summary.xlsx"})


# ═══ 보고서 2: Forecast vs Actual ════════════════════════════════


@router.get("/forecast-vs-actual")
def get_forecast_vs_actual(
    date_from: str | None = Query(None, description="시작월 (YYYY-MM)"),
    date_to: str | None = Query(None, description="종료월 (YYYY-MM)"),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Forecast vs Actual 데이터 조회."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    return svc.list_forecast_vs_actual(db, filt, current_user=current_user)


@router.get("/forecast-vs-actual/export")
def export_forecast_vs_actual(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Forecast vs Actual Excel 다운로드."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    content = svc.export_forecast_vs_actual(db, filt, current_user=current_user)
    return Response(content=content, media_type=XLSX_MEDIA,
                    headers={"Content-Disposition": "attachment; filename=forecast_vs_actual.xlsx"})


# ═══ 보고서 3: 미수 현황 ═════════════════════════════════════════


@router.get("/receivables")
def get_receivables(
    date_from: str | None = Query(None, description="시작월 (YYYY-MM)"),
    date_to: str | None = Query(None, description="종료월 (YYYY-MM)"),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """미수 현황 데이터 조회."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    return svc.list_receivables(db, filt, current_user=current_user)


@router.get("/receivables/export")
def export_receivables(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """미수 현황 Excel 다운로드."""
    filt = _make_filter(date_from, date_to, owner_id, department, contract_type, stage)
    content = svc.export_receivables(db, filt, current_user=current_user)
    return Response(content=content, media_type=XLSX_MEDIA,
                    headers={"Content-Disposition": "attachment; filename=receivables.xlsx"})


# ═══ 보고서 4: 매입매출관리 (기존 유지) ══════════════════════════


@router.get("/contract-pnl/{contract_id}")
def get_contract_pnl(
    contract_id: int,
    period_year: int | None = Query(None, description="조회 연도 (미지정 시 전체)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """매입매출관리 보고서 데이터 조회."""
    check_contract_access(db, contract_id, current_user)
    return svc.get_contract_pnl(db, contract_id, period_year)


@router.get("/contract-pnl/{contract_id}/export")
def export_contract_pnl(
    contract_id: int,
    period_year: int | None = Query(None, description="조회 연도 (미지정 시 전체)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """매입매출관리 보고서 Excel 다운로드."""
    check_contract_access(db, contract_id, current_user)
    content = svc.export_contract_pnl(db, contract_id, period_year)
    return Response(content=content, media_type=XLSX_MEDIA,
                    headers={"Content-Disposition": "attachment; filename=contract_pnl.xlsx"})
