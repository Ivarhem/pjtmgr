"""Contract / ContractPeriod CRUD 서비스."""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.authorization import apply_contract_scope, check_contract_access, check_period_access
from app.exceptions import BusinessRuleError, NotFoundError
from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.schemas.contract import (
    ContractCreate,
    ContractPeriodCreate,
    ContractPeriodUpdate,
    ContractUpdate,
)

if TYPE_CHECKING:
    from app.models.user import User


# ── dict 변환 헬퍼 ───────────────────────────────────────────

def _period_label(year: int) -> str:
    return f"Y{str(year)[-2:]}"


def _contract_read_dict(contract: Contract) -> dict:
    return {
        "id": contract.id,
        "contract_code": contract.contract_code,
        "contract_name": contract.contract_name,
        "contract_type": contract.contract_type,
        "end_customer_id": contract.end_customer_id,
        "end_customer_name": contract.end_customer.name if contract.end_customer else None,
        "owner_user_id": contract.owner_user_id,
        "owner_name": contract.owner.name if contract.owner else None,
        "status": contract.status,
        "inspection_day": contract.inspection_day,
        "inspection_date": str(contract.inspection_date) if contract.inspection_date else None,
        "invoice_month_offset": contract.invoice_month_offset,
        "invoice_day_type": contract.invoice_day_type,
        "invoice_day": contract.invoice_day,
        "invoice_holiday_adjust": contract.invoice_holiday_adjust,
    }


def _period_list_dict(period: ContractPeriod) -> dict:
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
        "stage": period.stage,
        "start_month": period.start_month,
        "end_month": period.end_month,
        "expected_revenue_total": period.expected_revenue_total,
        "expected_gp_total": period.expected_gp_total,
        "is_planned": period.is_planned,
    }


def _period_read_dict(period: ContractPeriod) -> dict:
    """Period 상세 응답용 dict."""
    return {
        "id": period.id,
        "contract_id": period.contract_id,
        "period_year": period.period_year,
        "period_label": period.period_label,
        "stage": period.stage,
        "expected_revenue_total": period.expected_revenue_total,
        "expected_gp_total": period.expected_gp_total,
        "start_month": period.start_month,
        "end_month": period.end_month,
        "owner_user_id": period.owner_user_id,
        "owner_name": period.owner.name if period.owner else None,
        "customer_id": period.customer_id,
        "customer_name": period.customer.name if period.customer else None,
        "inspection_day": period.inspection_day,
        "inspection_date": str(period.inspection_date) if period.inspection_date else None,
        "invoice_month_offset": period.invoice_month_offset,
        "invoice_day_type": period.invoice_day_type,
        "invoice_day": period.invoice_day,
        "is_completed": period.is_completed,
        "is_planned": period.is_planned,
        "invoice_holiday_adjust": period.invoice_holiday_adjust,
        "notes": period.notes,
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


def get_contract_periods(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> list[dict]:
    """특정 사업의 모든 period 목록 (연도 탭용)"""
    if current_user:
        check_contract_access(db, contract_id, current_user)
    periods = (
        db.query(ContractPeriod)
        .options(joinedload(ContractPeriod.owner), joinedload(ContractPeriod.customer))
        .filter(ContractPeriod.contract_id == contract_id)
        .order_by(ContractPeriod.period_year)
        .all()
    )
    return [
        {
            "id": p.id,
            "period_year": p.period_year,
            "period_label": p.period_label,
            "stage": p.stage,
            "start_month": p.start_month,
            "end_month": p.end_month,
            "expected_revenue_total": p.expected_revenue_total,
            "expected_gp_total": p.expected_gp_total,
            "owner_user_id": p.owner_user_id,
            "owner_name": p.owner.name if p.owner else None,
            "customer_id": p.customer_id,
            "customer_name": p.customer.name if p.customer else None,
            "inspection_day": p.inspection_day,
            "inspection_date": str(p.inspection_date) if p.inspection_date else None,
            "invoice_month_offset": p.invoice_month_offset,
            "invoice_day_type": p.invoice_day_type,
            "invoice_day": p.invoice_day,
            "invoice_holiday_adjust": p.invoice_holiday_adjust,
            "is_completed": p.is_completed,
            "is_planned": p.is_planned,
            "notes": p.notes,
        }
        for p in periods
    ]


# ── Contract CRUD ─────────────────────────────────────────────────

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
    """원장 목록: contract_periods + contracts JOIN (flat)"""
    from app.models.user import User as UserModel

    q = (
        db.query(ContractPeriod)
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
    periods = q.order_by(ContractPeriod.period_year.desc(), Contract.contract_code).all()
    return [_period_list_dict(p) for p in periods]


def get_contract(db: Session, contract_id: int, *, current_user: User | None = None) -> dict:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    contract = db.query(Contract).options(
        joinedload(Contract.end_customer),
        joinedload(Contract.owner),
        joinedload(Contract.periods),
    ).filter(Contract.id == contract_id).first()
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    return _contract_read_dict(contract)


def get_period(db: Session, period_id: int, *, current_user: User | None = None) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)
    period = db.query(ContractPeriod).options(
        joinedload(ContractPeriod.contract).joinedload(Contract.end_customer),
        joinedload(ContractPeriod.contract).joinedload(Contract.owner),
        joinedload(ContractPeriod.owner),
        joinedload(ContractPeriod.customer),
    ).filter(ContractPeriod.id == period_id).first()
    if not period:
        raise NotFoundError("기간을 찾을 수 없습니다.")
    return _period_read_dict(period)


def create_contract(db: Session, data: ContractCreate, *, created_by: int | None = None) -> dict:
    """사업 생성. owner_user_id 미지정 시 created_by를 자동 지정."""
    from app.models.contract_type_config import ContractTypeConfig
    from app.services.contract_type_config import get_valid_codes

    if data.owner_user_id is None and created_by is not None:
        data.owner_user_id = created_by

    valid = get_valid_codes(db)
    if data.contract_type not in valid:
        raise BusinessRuleError(f"유효하지 않은 사업유형: {data.contract_type}")

    # 사업유형 기본값 적용
    dtc = db.query(ContractTypeConfig).filter(ContractTypeConfig.code == data.contract_type).first()

    contract = Contract(
        contract_name=data.contract_name,
        contract_type=data.contract_type,
        end_customer_id=data.end_customer_id,
        owner_user_id=data.owner_user_id,
        status=data.status,
    )
    if dtc:
        if dtc.default_inspection_day is not None:
            contract.inspection_day = dtc.default_inspection_day
        if dtc.default_invoice_month_offset is not None:
            contract.invoice_month_offset = dtc.default_invoice_month_offset
        if dtc.default_invoice_day_type is not None:
            contract.invoice_day_type = dtc.default_invoice_day_type
        if dtc.default_invoice_day is not None:
            contract.invoice_day = dtc.default_invoice_day
        if dtc.default_invoice_holiday_adjust is not None:
            contract.invoice_holiday_adjust = dtc.default_invoice_holiday_adjust
    db.add(contract)
    db.flush()

    # contract_code 자동생성: {사업유형}-{현재연도}-{ID 4자리}
    cur_year = datetime.date.today().year
    contract.contract_code = f"{data.contract_type}-{cur_year}-{contract.id:04d}"

    db.commit()
    db.refresh(contract)
    return _contract_read_dict(contract)


def update_contract(
    db: Session,
    contract_id: int,
    data: ContractUpdate,
    *,
    current_user: User | None = None,
) -> dict:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    contract = db.query(Contract).options(
        joinedload(Contract.end_customer), joinedload(Contract.owner)
    ).filter(Contract.id == contract_id).first()
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status == "cancelled":
        raise BusinessRuleError("삭제된 사업은 수정할 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "inspection_date" and value:
            value = datetime.date.fromisoformat(value)
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return _contract_read_dict(contract)


def bulk_assign_owner(db: Session, contract_ids: list[int], owner_user_id: int | None) -> int:
    """여러 사업 및 소속 Period의 담당자를 일괄 변경. 변경된 Contract 수 반환."""
    count = (
        db.query(Contract)
        .filter(Contract.id.in_(contract_ids), Contract.status != "cancelled")
        .update({"owner_user_id": owner_user_id}, synchronize_session="fetch")
    )
    db.query(ContractPeriod).filter(ContractPeriod.contract_id.in_(contract_ids)).update(
        {"owner_user_id": owner_user_id}, synchronize_session="fetch"
    )
    db.commit()
    return count


# ── ContractPeriod CRUD ───────────────────────────────────────────

def create_period(
    db: Session,
    contract_id: int,
    data: ContractPeriodCreate,
    *,
    current_user: User | None = None,
) -> ContractPeriod:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status == "cancelled":
        raise BusinessRuleError("삭제된 사업에는 Period를 추가할 수 없습니다.")
    label = data.period_label or _period_label(data.period_year)

    # start_month > end_month 방지
    if data.start_month and data.end_month and data.start_month > data.end_month:
        raise BusinessRuleError("시작월이 종료월보다 클 수 없습니다.", status_code=422)

    # 검수/계산서/담당자/매출처 필드: 미지정 시 Contract의 값을 복사
    _inherit_fields = [
        "owner_user_id", "customer_id",
        "inspection_day", "inspection_date", "invoice_month_offset",
        "invoice_day_type", "invoice_day", "invoice_holiday_adjust",
    ]
    provided = data.model_dump(exclude_unset=True)
    # Contract 필드명이 다른 경우 매핑 (Period.customer_id ← Contract.end_customer_id)
    _contract_field_map = {"customer_id": "end_customer_id"}
    inherit_vals = {}
    for f in _inherit_fields:
        if f in provided:
            inherit_vals[f] = provided[f]
        else:
            contract_attr = _contract_field_map.get(f, f)
            inherit_vals[f] = getattr(contract, contract_attr, None)

    # inspection_date 문자열 → date 변환
    if isinstance(inherit_vals.get("inspection_date"), str):
        inherit_vals["inspection_date"] = datetime.date.fromisoformat(inherit_vals["inspection_date"])

    period = ContractPeriod(
        contract_id=contract_id,
        period_year=data.period_year,
        period_label=label,
        stage=data.stage,
        expected_revenue_total=data.expected_revenue_total,
        expected_gp_total=data.expected_gp_total,
        start_month=data.start_month,
        end_month=data.end_month,
        is_planned=data.is_planned,
        notes=data.notes,
        **inherit_vals,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return _period_read_dict(period)


def update_period(
    db: Session,
    period_id: int,
    data: ContractPeriodUpdate,
    *,
    current_user: User | None = None,
) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)
    period = db.query(ContractPeriod).options(
        joinedload(ContractPeriod.owner),
        joinedload(ContractPeriod.customer),
    ).filter(ContractPeriod.id == period_id).first()
    if not period:
        raise NotFoundError("사업 기간을 찾을 수 없습니다.")
    updates = data.model_dump(exclude_unset=True)

    # start_month > end_month 방지 (부분 업데이트 시 기존 값과 비교)
    new_start = updates.get("start_month", period.start_month)
    new_end = updates.get("end_month", period.end_month)
    if new_start and new_end and new_start > new_end:
        raise BusinessRuleError("시작월이 종료월보다 클 수 없습니다.", status_code=422)

    for field, value in updates.items():
        if field == "inspection_date" and isinstance(value, str):
            value = datetime.date.fromisoformat(value)
        setattr(period, field, value)
    db.commit()
    db.refresh(period)
    return _period_read_dict(period)


def delete_period(db: Session, period_id: int, *, current_user: User | None = None) -> None:
    if current_user:
        check_period_access(db, period_id, current_user)
    period = db.get(ContractPeriod, period_id)
    if not period:
        raise NotFoundError("사업 기간을 찾을 수 없습니다.")
    contract_id = period.contract_id
    db.delete(period)
    db.flush()
    # 남은 period가 없으면 contract를 cancelled 처리 (소프트 삭제)
    remaining = db.query(ContractPeriod).filter(ContractPeriod.contract_id == contract_id).count()
    if remaining == 0:
        contract = db.get(Contract, contract_id)
        if contract:
            contract.status = "cancelled"
    db.commit()


def delete_contract(db: Session, contract_id: int) -> None:
    """Contract 소프트 삭제 (status → cancelled). 하위 데이터는 보존."""
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    contract.status = "cancelled"
    db.commit()


def restore_contract(db: Session, contract_id: int) -> dict:
    """삭제(cancelled)된 사업을 복구 (status → active)."""
    contract = db.query(Contract).options(
        joinedload(Contract.end_customer), joinedload(Contract.owner)
    ).filter(Contract.id == contract_id).first()
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status != "cancelled":
        raise BusinessRuleError("삭제 상태가 아닌 사업은 복구할 수 없습니다.")
    contract.status = "active"
    db.commit()
    db.refresh(contract)
    return _contract_read_dict(contract)
