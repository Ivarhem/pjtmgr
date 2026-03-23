"""Accounting-specific contract/period 서비스 (원장 목록, 템플릿, 요약).

Common CRUD는 app.modules.common.services.contract로 이관됨.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import apply_contract_scope
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.accounting.models.contract_sales_detail import ContractSalesDetail

if TYPE_CHECKING:
    from app.modules.common.models.user import User


# ── dict 변환 헬퍼 ───────────────────────────────────────────

def _period_list_dict(period: ContractPeriod, sales_detail: ContractSalesDetail | None) -> dict:
    contract = period.contract
    # Period 담당자 우선, 없으면 Contract 담당자 fallback
    owner = period.owner or contract.owner
    return {
        "id": period.id,
        "contract_id": contract.id,
        "contract_code": contract.contract_code,
        "contract_name": contract.contract_name,
        "contract_type": contract.contract_type,
        "end_customer_name": contract.end_customer.name if contract.end_customer else None,
        "customer_name": period.customer.name if period.customer else None,
        "owner_name": owner.name if owner else None,
        "owner_department": owner.department if owner else None,
        "status": contract.status,
        "period_year": period.period_year,
        "period_label": period.period_label,
        "period_code": period.period_code,
        "stage": period.stage,
        "start_month": period.start_month,
        "end_month": period.end_month,
        "expected_revenue_amount": sales_detail.expected_revenue_amount if sales_detail else 0,
        "expected_gp_amount": sales_detail.expected_gp_amount if sales_detail else 0,
        "is_planned": period.is_planned,
    }


# ── 템플릿 / 목록 ──────────────────────────────────────────

def list_periods_for_template(db: Session) -> list[dict]:
    """Excel 템플릿용 기간 목록 (period_id, year, contract_name)."""
    periods = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .order_by(ContractPeriod.period_year, Contract.contract_name)
        .all()
    )
    return [
        {"period_id": p.id, "period_year": p.period_year, "contract_name": p.contract.contract_name}
        for p in periods
    ]


def list_periods_flat(
    db: Session,
    period_year: list[int] | None = None,
    calendar_year: list[int] | None = None,
    contract_type: list[str] | None = None,
    stage: list[str] | None = None,
    owner_department: list[str] | None = None,
    owner_id: list[int] | None = None,
    current_user: User | None = None,
    active_month: str | None = None,
) -> list[dict]:
    """원장 목록: contract_periods + contracts + sales_detail JOIN (flat)"""
    from app.modules.common.models.user import User as UserModel

    q = (
        db.query(ContractPeriod, ContractSalesDetail)
        .outerjoin(ContractSalesDetail, ContractSalesDetail.contract_period_id == ContractPeriod.id)
        .join(ContractPeriod.contract)
        .filter(Contract.status != "cancelled")
        .options(
            joinedload(ContractPeriod.contract).joinedload(Contract.end_customer),
            joinedload(ContractPeriod.contract).joinedload(Contract.owner),
            joinedload(ContractPeriod.owner),
            joinedload(ContractPeriod.customer),
        )
    )
    # 역할 기반 데이터 가시 범위 적용
    if current_user:
        q = apply_contract_scope(q, current_user)
    if active_month:
        q = q.filter(
            ContractPeriod.start_month.isnot(None),
            ContractPeriod.end_month.isnot(None),
            ContractPeriod.start_month <= active_month,
            ContractPeriod.end_month >= active_month,
        )
    if period_year:
        q = q.filter(ContractPeriod.period_year.in_(period_year))
    if calendar_year:
        # 달력 연도 필터: start_month~end_month 범위가 해당 연도와 겹치는 Period
        year_conditions = []
        for y in calendar_year:
            year_start = f"{y}-01-01"
            year_end = f"{y}-12-01"
            year_conditions.append(
                (ContractPeriod.start_month <= year_end) & (ContractPeriod.end_month >= year_start)
            )
        q = q.filter(or_(*year_conditions))
    if contract_type:
        q = q.filter(Contract.contract_type.in_(contract_type))
    if stage:
        q = q.filter(ContractPeriod.stage.in_(stage))
    if owner_department:
        q = q.filter(
            or_(
                ContractPeriod.owner.has(UserModel.department.in_(owner_department)),
                and_(
                    ContractPeriod.owner_user_id.is_(None),
                    Contract.owner.has(UserModel.department.in_(owner_department)),
                ),
            )
        )
    if owner_id:
        q = q.filter(
            or_(
                ContractPeriod.owner_user_id.in_(owner_id),
                and_(
                    ContractPeriod.owner_user_id.is_(None),
                    Contract.owner_user_id.in_(owner_id),
                ),
            )
        )
    rows = q.order_by(ContractPeriod.period_year.desc(), Contract.contract_code).all()
    return [_period_list_dict(period, sales_detail) for period, sales_detail in rows]
