from __future__ import annotations
import datetime
from typing import TYPE_CHECKING
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.transaction_line import TransactionLine
from app.models.receipt import Receipt
from app.schemas.contract import ContractCreate, ContractUpdate, ContractPeriodCreate, ContractPeriodUpdate
from app.schemas.transaction_line import TransactionLineCreate, TransactionLineUpdate
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.services.customer import get_or_create_by_name as _get_or_create_customer
from app.auth.authorization import apply_contract_scope, check_contract_access
from app.exceptions import NotFoundError, BusinessRuleError

if TYPE_CHECKING:
    from app.models.user import User


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
    }


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


def get_contract_periods(db: Session, contract_id: int) -> list[dict]:
    """특정 사업의 모든 period 목록 (연도 탭용)"""
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


def get_contract(db: Session, contract_id: int) -> dict:
    contract = db.query(Contract).options(
        joinedload(Contract.end_customer),
        joinedload(Contract.owner),
        joinedload(Contract.periods),
    ).filter(Contract.id == contract_id).first()
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    return _contract_read_dict(contract)


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
        "invoice_holiday_adjust": period.invoice_holiday_adjust,
        "notes": period.notes,
    }


def get_period(db: Session, period_id: int) -> dict:
    period = db.query(ContractPeriod).options(
        joinedload(ContractPeriod.contract).joinedload(Contract.end_customer),
        joinedload(ContractPeriod.contract).joinedload(Contract.owner),
        joinedload(ContractPeriod.owner),
        joinedload(ContractPeriod.customer),
    ).filter(ContractPeriod.id == period_id).first()
    if not period:
        raise NotFoundError("기간을 찾을 수 없습니다.")
    return _period_read_dict(period)


def _generate_month_range(start: str, end: str) -> list[str]:
    """YYYY-MM 형태의 시작/종료월로부터 월 목록 생성. 결과는 YYYY-MM-01 형태."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    months: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y}-{str(m).zfill(2)}-01")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def create_contract(db: Session, data: ContractCreate, *, created_by: int | None = None) -> dict:
    """사업 생성. owner_user_id 미지정 시 created_by를 자동 지정."""
    from app.services.contract_type_config import get_valid_codes
    from app.models.contract_type_config import ContractTypeConfig

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


def update_contract(db: Session, contract_id: int, data: ContractUpdate) -> dict:
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

def create_period(db: Session, contract_id: int, data: ContractPeriodCreate) -> ContractPeriod:
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
        notes=data.notes,
        **inherit_vals,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return _period_read_dict(period)


def update_period(db: Session, period_id: int, data: ContractPeriodUpdate) -> dict:
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


def delete_period(db: Session, period_id: int) -> None:
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


# ── Forecast ──────────────────────────────────────────────────

def get_forecasts(db: Session, period_id: int) -> list:
    from app.models.monthly_forecast import MonthlyForecast
    return (
        db.query(MonthlyForecast)
        .filter(MonthlyForecast.contract_period_id == period_id, MonthlyForecast.is_current.is_(True))
        .order_by(MonthlyForecast.forecast_month)
        .all()
    )


def list_all_forecasts(db: Session, contract_id: int) -> list[dict]:
    """Contract의 모든 Period에 대한 Forecast를 반환."""
    from app.models.monthly_forecast import MonthlyForecast
    period_ids = [
        p.id for p in db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id == contract_id)
        .order_by(ContractPeriod.period_year)
        .all()
    ]
    if not period_ids:
        return []
    rows = (
        db.query(MonthlyForecast)
        .filter(MonthlyForecast.contract_period_id.in_(period_ids), MonthlyForecast.is_current.is_(True))
        .order_by(MonthlyForecast.forecast_month)
        .all()
    )
    return [
        {
            "contract_period_id": f.contract_period_id,
            "forecast_month": f.forecast_month,
            "revenue_amount": f.revenue_amount,
            "gp_amount": f.gp_amount,
        }
        for f in rows
    ]


def upsert_forecasts(db: Session, period_id: int, items: list, *, created_by: int | None = None) -> list:
    from app.models.monthly_forecast import MonthlyForecast
    existing = {
        f.forecast_month: f
        for f in db.query(MonthlyForecast)
        .filter(MonthlyForecast.contract_period_id == period_id, MonthlyForecast.is_current.is_(True))
        .all()
    }
    incoming_months = set()
    for item in items:
        incoming_months.add(item.forecast_month)
        if item.forecast_month in existing:
            existing[item.forecast_month].revenue_amount = item.revenue_amount
            existing[item.forecast_month].gp_amount = item.gp_amount
        else:
            db.add(MonthlyForecast(
                contract_period_id=period_id,
                forecast_month=item.forecast_month,
                revenue_amount=item.revenue_amount,
                gp_amount=item.gp_amount,
                created_by=created_by,
            ))
    # 전송 목록에 없는 기존 행 삭제
    for month, row in existing.items():
        if month not in incoming_months:
            db.delete(row)
    db.commit()
    return get_forecasts(db, period_id)


# ── Transaction Lines ───────────────────────────────────────────────────

def get_transaction_lines(db: Session, contract_id: int) -> list[dict]:
    from app.models.transaction_line import TransactionLine
    rows = (
        db.query(TransactionLine)
        .options(joinedload(TransactionLine.customer))
        .filter(TransactionLine.contract_id == contract_id)
        .order_by(TransactionLine.revenue_month, TransactionLine.line_type)
        .all()
    )
    return [_transaction_line_dict(r) for r in rows]


def _transaction_line_dict(a: TransactionLine) -> dict:
    return {
        "id": a.id,
        "contract_id": a.contract_id,
        "revenue_month": a.revenue_month,
        "line_type": a.line_type,
        "customer_id": a.customer_id,
        "customer_name": a.customer.name if a.customer else None,
        "supply_amount": a.supply_amount,
        "invoice_issue_date": a.invoice_issue_date,
        "status": a.status or "확정",
        "description": a.description,
    }


def _auto_status(fields: dict) -> str:
    """거래처·발행일 유무로 상태를 자동 판별."""
    from app.models.transaction_line import STATUS_EXPECTED, STATUS_CONFIRMED
    has_customer = fields.get("customer_id") is not None
    has_date = bool(fields.get("invoice_issue_date"))
    return STATUS_CONFIRMED if (has_customer and has_date) else STATUS_EXPECTED


def _resolve_customer(db: Session, data_dict: dict) -> dict:
    """customer_id가 없고 customer_name이 있으면 자동 생성/조회."""
    name = data_dict.pop("customer_name", None)
    if not data_dict.get("customer_id") and name and name.strip():
        customer = _get_or_create_customer(db, name.strip())
        data_dict["customer_id"] = customer.id
    return data_dict


def create_transaction_line(db: Session, contract_id: int, data: TransactionLineCreate, *, created_by: int | None = None) -> dict:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status == "cancelled":
        raise BusinessRuleError("삭제된 사업에는 매출/매입을 추가할 수 없습니다.")
    fields = _resolve_customer(db, data.model_dump())
    # status: 명시적으로 전달되지 않았으면 자동 판별
    if not fields.get("status"):
        fields["status"] = _auto_status(fields)
    row = TransactionLine(contract_id=contract_id, created_by=created_by, **fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _transaction_line_dict(row)


def update_transaction_line(db: Session, transaction_line_id: int, data: TransactionLineUpdate, *, current_user: "User | None" = None) -> dict:
    row = db.query(TransactionLine).options(
        joinedload(TransactionLine.customer)
    ).filter(TransactionLine.id == transaction_line_id).first()
    if not row:
        raise NotFoundError("실적을 찾을 수 없습니다.")
    if current_user:
        check_contract_access(db, row.contract_id, current_user)
    fields = _resolve_customer(db, data.model_dump(exclude_unset=True))
    for field, value in fields.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _transaction_line_dict(row)


def delete_transaction_line(db: Session, transaction_line_id: int) -> None:
    row = db.get(TransactionLine, transaction_line_id)
    if not row:
        raise NotFoundError("실적을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


def bulk_confirm_transaction_lines(db: Session, contract_id: int) -> dict:
    """거래처+발행일이 있는 '예정' 매출/매입 행을 일괄 확정 처리."""
    from app.models.transaction_line import STATUS_EXPECTED, STATUS_CONFIRMED
    rows = (
        db.query(TransactionLine)
        .filter(
            TransactionLine.contract_id == contract_id,
            TransactionLine.status == STATUS_EXPECTED,
            TransactionLine.customer_id.isnot(None),
            TransactionLine.invoice_issue_date.isnot(None),
            TransactionLine.invoice_issue_date != "",
        )
        .all()
    )
    for row in rows:
        row.status = STATUS_CONFIRMED
    db.commit()
    return {"confirmed": len(rows)}


# ── Receipts ──────────────────────────────────────────────────

def get_receipts(db: Session, contract_id: int) -> list[dict]:
    rows = (
        db.query(Receipt)
        .options(joinedload(Receipt.customer))
        .filter(Receipt.contract_id == contract_id)
        .order_by(Receipt.receipt_date)
        .all()
    )
    return [_receipt_dict(r) for r in rows]


def _receipt_dict(p: Receipt) -> dict:
    return {
        "id": p.id,
        "contract_id": p.contract_id,
        "customer_id": p.customer_id,
        "customer_name": p.customer.name if p.customer else None,
        "receipt_date": p.receipt_date,
        "revenue_month": p.revenue_month,
        "amount": p.amount,
        "description": p.description,
    }


def create_receipt(db: Session, contract_id: int, data: ReceiptCreate, *, created_by: int | None = None) -> dict:
    from app.services.receipt_match import auto_match_receipt

    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")
    if contract.status == "cancelled":
        raise BusinessRuleError("삭제된 사업에는 입금을 추가할 수 없습니다.")
    row = Receipt(contract_id=contract_id, created_by=created_by, **data.model_dump())
    db.add(row)
    db.flush()
    auto_match_receipt(db, row.id, created_by=created_by)
    db.commit()
    db.refresh(row)
    return _receipt_dict(row)


def update_receipt(db: Session, receipt_id: int, data: ReceiptUpdate, *, current_user: "User | None" = None) -> dict:
    from app.services.receipt_match import auto_match_receipt

    row = db.query(Receipt).options(
        joinedload(Receipt.customer)
    ).filter(Receipt.id == receipt_id).first()
    if not row:
        raise NotFoundError("입금 정보를 찾을 수 없습니다.")
    if current_user:
        check_contract_access(db, row.contract_id, current_user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    # 금액 변경 시 자동 배분 재계산
    if "amount" in data.model_dump(exclude_unset=True):
        auto_match_receipt(db, receipt_id, created_by=current_user.id if current_user else None)
    db.commit()
    db.refresh(row)
    return _receipt_dict(row)


def delete_receipt(db: Session, receipt_id: int) -> None:
    row = db.get(Receipt, receipt_id)
    if not row:
        raise NotFoundError("입금 정보를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


# ── Forecast → TransactionLine 변환 ────────────────────────────────────

def _calc_invoice_date(src, revenue_month: str) -> str | None:
    """발행일 규칙에 따라 invoice_issue_date를 계산.

    src: ContractPeriod 또는 Contract (invoice_day_type 등 속성 보유 객체)
    revenue_month: "YYYY-MM-01" 형식
    반환: "YYYY-MM-DD" 또는 None (규칙 미설정 시)
    """
    import calendar
    from dateutil.relativedelta import relativedelta

    if not src.invoice_day_type:
        return None

    base = datetime.datetime.strptime(revenue_month, "%Y-%m-%d").date()

    # 월 오프셋 적용 (0=당월, 1=익월, ...)
    offset = src.invoice_month_offset or 0
    target = base + relativedelta(months=offset)

    # 일자 결정
    if src.invoice_day_type == "1일":
        day = 1
    elif src.invoice_day_type == "말일":
        day = calendar.monthrange(target.year, target.month)[1]
    elif src.invoice_day_type == "특정일" and src.invoice_day:
        last_day = calendar.monthrange(target.year, target.month)[1]
        day = min(src.invoice_day, last_day)
    else:
        return None

    return target.replace(day=day).strftime("%Y-%m-%d")


def _all_forecast_months(db: Session, contract_id: int) -> dict[str, dict]:
    """사업의 전체 period에 걸친 forecast 월별 매출 합산.

    Returns:
        {month: {"amount": int, "period_id": int}} — period_id는 마지막으로 기여한 period
    """
    from app.models.monthly_forecast import MonthlyForecast
    from app.models.contract_period import ContractPeriod

    period_ids = [
        p.id for p in db.query(ContractPeriod.id).filter(ContractPeriod.contract_id == contract_id).all()
    ]
    if not period_ids:
        return {}
    forecasts = (
        db.query(MonthlyForecast)
        .filter(
            MonthlyForecast.contract_period_id.in_(period_ids),
            MonthlyForecast.is_current.is_(True),
        )
        .all()
    )
    result: dict[str, dict] = {}
    for f in forecasts:
        if f.revenue_amount:
            if f.forecast_month in result:
                result[f.forecast_month]["amount"] += f.revenue_amount
            else:
                result[f.forecast_month] = {"amount": f.revenue_amount, "period_id": f.contract_period_id}
    return result


def preview_forecast_sync(db: Session, contract_id: int) -> dict:
    """Forecast ↔ TransactionLine 대조 미리보기 (전체 period 기준, DB 변경 없음)."""
    from app.models.transaction_line import STATUS_EXPECTED

    forecast_months = _all_forecast_months(db, contract_id)

    transaction_lines = (
        db.query(TransactionLine)
        .filter(TransactionLine.contract_id == contract_id, TransactionLine.line_type == "revenue")
        .all()
    )
    tl_by_month: dict[str, list] = {}
    for a in transaction_lines:
        tl_by_month.setdefault(a.revenue_month, []).append(a)

    to_create = []
    for month, info in sorted(forecast_months.items()):
        if month not in tl_by_month:
            to_create.append({"revenue_month": month, "amount": info["amount"]})

    to_delete = []
    for month, rows in sorted(tl_by_month.items()):
        if month not in forecast_months:
            for a in rows:
                if a.status == STATUS_EXPECTED and a.customer_id is None:
                    to_delete.append({
                        "id": a.id,
                        "revenue_month": a.revenue_month,
                        "amount": a.supply_amount,
                    })

    return {"to_create": to_create, "to_delete": to_delete}


def sync_transaction_lines_from_forecast(db: Session, contract_id: int, delete_ids: list[int]) -> dict:
    """Forecast 기반 TransactionLine 동기화 (전체 period): 생성 + 선택된 행 삭제."""
    from app.models.transaction_line import STATUS_EXPECTED

    contract = db.get(Contract, contract_id)
    if not contract:
        return {"created": 0, "deleted": 0}

    # 삭제 (예정 상태만 삭제 가능)
    deleted = 0
    if delete_ids:
        rows = (
            db.query(TransactionLine)
            .filter(
                TransactionLine.id.in_(delete_ids),
                TransactionLine.contract_id == contract_id,
                TransactionLine.line_type == "revenue",
                TransactionLine.status == STATUS_EXPECTED,
            )
            .all()
        )
        for row in rows:
            db.delete(row)
            deleted += 1

    # 생성 (전체 period forecast 기준)
    forecast_months = _all_forecast_months(db, contract_id)
    existing = {
        (a.revenue_month, a.line_type)
        for a in db.query(TransactionLine)
        .filter(TransactionLine.contract_id == contract_id)
        .all()
    }
    # Period별 정보 조회 (매출처 + 발행일 규칙 결정용)
    period_map: dict[int, ContractPeriod] = {
        p.id: p
        for p in db.query(ContractPeriod).filter(ContractPeriod.contract_id == contract_id).all()
    }
    created = []
    for month, info in sorted(forecast_months.items()):
        if (month, "revenue") not in existing:
            period = period_map.get(info["period_id"])
            # Period의 매출처 우선, 없으면 Contract의 end_customer fallback
            period_cust = period.customer_id if period else None
            customer_id = period_cust if period_cust is not None else contract.end_customer_id
            # 발행일: Period 설정 우선, 없으면 Contract fallback
            invoice_src = period if (period and period.invoice_day_type) else contract
            row = TransactionLine(
                contract_id=contract_id,
                revenue_month=month,
                line_type="revenue",
                customer_id=customer_id,
                supply_amount=info["amount"],
                invoice_issue_date=_calc_invoice_date(invoice_src, month),
                status=STATUS_EXPECTED,
            )
            db.add(row)
            created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return {"created": len(created), "deleted": deleted, "rows": [_transaction_line_dict(r) for r in created]}


# ── Ledger (매출/매입 실적 뷰) ─────────────────────────────────

def get_ledger(db: Session, contract_id: int) -> list[dict]:
    """매출/매입 실적 원장"""
    transaction_lines = get_transaction_lines(db, contract_id)

    rows: list[dict] = []
    for a in transaction_lines:
        rows.append({
            "row_key": f"a_{a['id']}",
            "record_type": "transaction_line",
            "transaction_line_id": a["id"],
            "type": "매출" if a["line_type"] == "revenue" else "매입",
            "revenue_month": a["revenue_month"],
            "date": a["invoice_issue_date"],
            "customer_name": a["customer_name"],
            "amount": a["supply_amount"],
            "status": a["status"],
            "description": a["description"],
        })

    rows.sort(key=lambda r: (r["revenue_month"] or "9999-99-99", r.get("date") or ""))
    return rows


# ── 내 사업 요약 ─────────────────────────────────────────────

def get_my_contracts_summary(
    db: Session,
    current_user: "User",
    *,
    period_year: list[int] | None = None,
    calendar_year: list[int] | None = None,
    active_month: str | None = None,
) -> dict:
    """현재 사용자의 사업 요약 통계.

    Returns:
        contract_count: 진행 중인 사업 수
        revenue_confirmed: 매출 확정 합계
        cost_confirmed: 매입 확정 합계
        gp: GP (매출 - 매입)
        gp_pct: GP% (GP / 매출 * 100)
        receipt_total: 입금 합계
        ar: 미수금 (매출 확정 - 입금)
        current_month_revenue: 이번 달 매출 확정
    """
    from sqlalchemy import func
    from app.models.transaction_line import TransactionLine, STATUS_CONFIRMED
    from app.services.metrics import (
        load_actuals,
        load_allocated_totals,
        load_payments,
    )

    q = db.query(ContractPeriod.contract_id).join(ContractPeriod.contract)
    q = q.filter(
        or_(
            ContractPeriod.owner_user_id == current_user.id,
            and_(
                ContractPeriod.owner_user_id.is_(None),
                Contract.owner_user_id == current_user.id,
            ),
        )
    )
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
        year_conditions = []
        for y in calendar_year:
            year_start = f"{y}-01-01"
            year_end = f"{y}-12-01"
            year_conditions.append(
                (ContractPeriod.start_month <= year_end) & (ContractPeriod.end_month >= year_start)
            )
        q = q.filter(or_(*year_conditions))
    contract_ids = [r[0] for r in q.distinct().all()]

    if not contract_ids:
        return {
            "contract_count": 0, "revenue_confirmed": 0, "cost_confirmed": 0,
            "gp": 0, "gp_pct": None, "receipt_total": 0, "ar": 0,
            "current_month_revenue": 0,
        }

    # 사업 수 (active 상태만)
    contract_count = (
        db.query(func.count(Contract.id))
        .filter(Contract.id.in_(contract_ids), Contract.status == "active")
        .scalar()
    )

    # 매출/매입 확정 합계
    def _sum_transaction_lines(line_type: str) -> int:
        val = (
            db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
            .filter(
                TransactionLine.contract_id.in_(contract_ids),
                TransactionLine.line_type == line_type,
                TransactionLine.status == STATUS_CONFIRMED,
            )
            .scalar()
        )
        return int(val)

    revenue_confirmed = _sum_transaction_lines("revenue")
    cost_confirmed = _sum_transaction_lines("cost")
    gp = revenue_confirmed - cost_confirmed
    gp_pct = round(gp / revenue_confirmed * 100, 1) if revenue_confirmed > 0 else None

    current_years = sorted(set(period_year or []) | set(calendar_year or []))
    if current_years:
        date_from = f"{min(current_years)}-01-01"
        date_to = f"{max(current_years)}-12-01"
    else:
        years = [
            row[0]
            for row in db.query(ContractPeriod.period_year)
            .filter(ContractPeriod.contract_id.in_(contract_ids))
            .distinct()
            .all()
        ]
        if years:
            date_from = f"{min(years)}-01-01"
            date_to = f"{max(years)}-12-01"
        else:
            today = datetime.date.today()
            date_from = f"{today.year}-01-01"
            date_to = f"{today.year}-12-01"

    act_map = load_actuals(db, contract_ids, date_from, date_to)
    pay_map = load_payments(db, contract_ids, date_from, date_to)
    alloc_map = load_allocated_totals(db, contract_ids, date_from, date_to)

    payment_total = sum(pay_map.get(did, 0) for did in contract_ids)
    total_revenue = sum(
        sum(v["revenue"] for v in act_map.get(did, {}).values())
        for did in contract_ids
    )
    total_allocated = sum(alloc_map.get(did, 0) for did in contract_ids)
    ar = total_revenue - total_allocated

    # 이번 달 매출
    today = datetime.date.today()
    current_month = f"{today.year}-{str(today.month).zfill(2)}-01"
    current_month_revenue = int(
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.line_type == "revenue",
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.revenue_month == current_month,
        )
        .scalar()
    )

    return {
        "contract_count": contract_count,
        "revenue_confirmed": revenue_confirmed,
        "cost_confirmed": cost_confirmed,
        "gp": gp,
        "gp_pct": gp_pct,
        "receipt_total": payment_total,
        "ar": ar,
        "current_month_revenue": current_month_revenue,
    }
