"""Contract / ContractPeriod 공통 CRUD 서비스.

영업(accounting)·인프라(infra) 모듈이 공유하는 기본 CRUD만 포함.
검수/청구서(inspection/invoice) 로직은 accounting 모듈에 남긴다.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import (
    apply_contract_scope,
    check_contract_access,
    check_period_access,
)
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.schemas.contract import ContractCreate, ContractUpdate
from app.modules.common.schemas.contract_period import (
    ContractPeriodCreate,
    ContractPeriodUpdate,
)

if TYPE_CHECKING:
    from app.modules.common.models.user import User


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
        "notes": contract.notes,
    }


def _period_read_dict(period: ContractPeriod) -> dict:
    """Period 상세 응답용 dict."""
    return {
        "id": period.id,
        "contract_id": period.contract_id,
        "period_year": period.period_year,
        "period_label": period.period_label,
        "stage": period.stage,
        "start_month": period.start_month,
        "end_month": period.end_month,
        "description": period.description,
        "owner_user_id": period.owner_user_id,
        "owner_name": period.owner.name if period.owner else None,
        "customer_id": period.customer_id,
        "customer_name": period.customer.name if period.customer else None,
        "is_completed": period.is_completed,
        "is_planned": period.is_planned,
        "notes": period.notes,
    }


# ── 목록 ─────────────────────────────────────────────────────


def list_periods(
    db: Session,
    customer_id: int | None = None,
) -> list[dict]:
    """계약단위 목록. customer_id 지정 시 해당 고객사의 period만 반환."""
    q = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .filter(Contract.status != "cancelled")
        .options(
            joinedload(ContractPeriod.contract).joinedload(Contract.end_customer),
            joinedload(ContractPeriod.owner),
            joinedload(ContractPeriod.customer),
        )
    )
    if customer_id is not None:
        q = q.filter(
            or_(
                Contract.end_customer_id == customer_id,
                ContractPeriod.customer_id == customer_id,
            )
        )
    periods = q.order_by(ContractPeriod.period_year.desc(), Contract.contract_name).all()
    return [
        {
            "id": p.id,
            "contract_id": p.contract_id,
            "contract_name": p.contract.contract_name,
            "contract_code": p.contract.contract_code,
            "contract_type": p.contract.contract_type,
            "period_year": p.period_year,
            "period_label": p.period_label,
            "stage": p.stage,
            "description": p.description,
            "customer_id": p.customer_id or p.contract.end_customer_id,
            "is_completed": p.is_completed,
            "start_month": p.start_month,
            "end_month": p.end_month,
        }
        for p in periods
    ]


def get_contract_periods(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> list[dict]:
    """특정 사업의 모든 period 목록 (연도 탭용)."""
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
            "description": p.description,
            "owner_user_id": p.owner_user_id,
            "owner_name": p.owner.name if p.owner else None,
            "customer_id": p.customer_id,
            "customer_name": p.customer.name if p.customer else None,
            "is_completed": p.is_completed,
            "is_planned": p.is_planned,
            "notes": p.notes,
        }
        for p in periods
    ]


# ── Contract CRUD ─────────────────────────────────────────────────


def get_contract(db: Session, contract_id: int, *, current_user: User | None = None) -> dict:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    contract = (
        db.query(Contract)
        .options(
            joinedload(Contract.end_customer),
            joinedload(Contract.owner),
            joinedload(Contract.periods),
        )
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    return _contract_read_dict(contract)


def create_contract(db: Session, data: ContractCreate, *, created_by: int | None = None) -> dict:
    """사업 생성. owner_user_id 미지정 시 created_by를 자동 지정.

    검수/청구서 기본값은 적용하지 않는다 (accounting 모듈 전용).
    contract_type 유효성만 검증한다.
    """
    from app.modules.common.services.contract_type_config import get_valid_codes

    if data.owner_user_id is None and created_by is not None:
        data.owner_user_id = created_by

    valid = get_valid_codes(db)
    if data.contract_type not in valid:
        raise BusinessRuleError(f"유효하지 않은 사업유형: {data.contract_type}")

    contract = Contract(
        contract_name=data.contract_name,
        contract_type=data.contract_type,
        end_customer_id=data.end_customer_id,
        owner_user_id=data.owner_user_id,
        status=data.status,
        notes=data.notes,
    )
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
    contract = (
        db.query(Contract)
        .options(joinedload(Contract.end_customer), joinedload(Contract.owner))
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status == "cancelled":
        raise BusinessRuleError("삭제된 사업은 수정할 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return _contract_read_dict(contract)


def delete_contract(db: Session, contract_id: int) -> None:
    """Contract 소프트 삭제 (status → cancelled). 하위 데이터는 보존."""
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    contract.status = "cancelled"
    db.commit()


def restore_contract(db: Session, contract_id: int) -> dict:
    """삭제(cancelled)된 사업을 복구 (status → active)."""
    contract = (
        db.query(Contract)
        .options(joinedload(Contract.end_customer), joinedload(Contract.owner))
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status != "cancelled":
        raise BusinessRuleError("삭제 상태가 아닌 사업은 복구할 수 없습니다.")
    contract.status = "active"
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


def get_period(db: Session, period_id: int, *, current_user: User | None = None) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)
    period = (
        db.query(ContractPeriod)
        .options(
            joinedload(ContractPeriod.contract).joinedload(Contract.end_customer),
            joinedload(ContractPeriod.contract).joinedload(Contract.owner),
            joinedload(ContractPeriod.owner),
            joinedload(ContractPeriod.customer),
        )
        .filter(ContractPeriod.id == period_id)
        .first()
    )
    if not period:
        raise NotFoundError("기간을 찾을 수 없습니다.")
    return _period_read_dict(period)


def create_period(
    db: Session,
    contract_id: int,
    data: ContractPeriodCreate,
    *,
    current_user: User | None = None,
) -> dict:
    """Period 생성. 검수/청구서 필드는 상속하지 않는다 (accounting 전용).

    상속 필드: owner_user_id, customer_id (← Contract.end_customer_id).
    """
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

    # 담당자/매출처 필드: 미지정 시 Contract의 값을 복사
    _inherit_fields = ["owner_user_id", "customer_id"]
    provided = data.model_dump(exclude_unset=True)
    # Contract 필드명이 다른 경우 매핑 (Period.customer_id ← Contract.end_customer_id)
    _contract_field_map = {"customer_id": "end_customer_id"}
    inherit_vals: dict = {}
    for f in _inherit_fields:
        if f in provided:
            inherit_vals[f] = provided[f]
        else:
            contract_attr = _contract_field_map.get(f, f)
            inherit_vals[f] = getattr(contract, contract_attr, None)

    period = ContractPeriod(
        contract_id=contract_id,
        period_year=data.period_year,
        period_label=label,
        stage=data.stage,
        start_month=data.start_month,
        end_month=data.end_month,
        description=data.description,
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
    period = (
        db.query(ContractPeriod)
        .options(
            joinedload(ContractPeriod.owner),
            joinedload(ContractPeriod.customer),
        )
        .filter(ContractPeriod.id == period_id)
        .first()
    )
    if not period:
        raise NotFoundError("사업 기간을 찾을 수 없습니다.")
    updates = data.model_dump(exclude_unset=True)

    # start_month > end_month 방지 (부분 업데이트 시 기존 값과 비교)
    new_start = updates.get("start_month", period.start_month)
    new_end = updates.get("end_month", period.end_month)
    if new_start and new_end and new_start > new_end:
        raise BusinessRuleError("시작월이 종료월보다 클 수 없습니다.", status_code=422)

    for field, value in updates.items():
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
