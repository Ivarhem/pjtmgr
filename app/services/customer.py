from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.auth.authorization import list_accessible_contract_ids
from app.auth.constants import ROLE_ADMIN
from app.models.customer import Customer
from app.models.customer_contact import CustomerContact
from app.models.customer_contact_role import CustomerContactRole
from app.models.contract import Contract
from app.models.contract_contact import ContractContact
from app.models.contract_period import ContractPeriod
from app.models.transaction_line import TransactionLine
from app.models.receipt import Receipt
from app.models.receipt_match import ReceiptMatch
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.customer_contact import CustomerContactCreate, CustomerContactUpdate
from app.exceptions import NotFoundError, BusinessRuleError, DuplicateError


def list_customers(
    db: Session, current_user=None, *, my_only: bool = False
) -> list[dict]:
    """거래처 목록 (요약 데이터 포함: active_count, total_revenue)."""
    if my_only and current_user:
        contract_ids = _get_owner_contract_ids(db, current_user.id)
        if not contract_ids:
            return []
        customer_ids = _collect_customer_ids(db, contract_ids)
        if not customer_ids:
            return []
        customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).order_by(Customer.name).all()
    elif not current_user or current_user.role == ROLE_ADMIN:
        customers = db.query(Customer).order_by(Customer.name).all()
    else:
        contract_ids = list_accessible_contract_ids(db, current_user)
        if not contract_ids:
            return []
        customer_ids = _collect_customer_ids(db, contract_ids)
        if not customer_ids:
            return []
        customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).order_by(Customer.name).all()

    if not customers:
        return []

    return _enrich_customers_with_summary(db, customers)


def _enrich_customers_with_summary(db: Session, customers: list[Customer]) -> list[dict]:
    """거래처 ORM 목록에 active_count, total_revenue 요약을 추가하여 dict 리스트로 반환."""
    customer_ids = [c.id for c in customers]

    # 1) customer_id별 진행중 사업 건수 (stage != '계약완료')
    # end_customer 또는 period customer로 연결된 사업 기준
    active_q = (
        db.query(
            Customer.id,
            func.count(func.distinct(Contract.id)),
        )
        .outerjoin(Contract, Contract.end_customer_id == Customer.id)
        .outerjoin(ContractPeriod, ContractPeriod.contract_id == Contract.id)
        .filter(
            Customer.id.in_(customer_ids),
            Contract.status != "cancelled",
            ContractPeriod.stage != "계약완료",
        )
        .group_by(Customer.id)
        .all()
    )
    active_map = {cid: cnt for cid, cnt in active_q}

    # 2) customer_id별 매출 합계 (TransactionLine에서 해당 customer가 매출처인 것)
    rev_q = (
        db.query(
            TransactionLine.customer_id,
            func.sum(TransactionLine.supply_amount),
        )
        .filter(
            TransactionLine.customer_id.in_(customer_ids),
            TransactionLine.line_type == "revenue",
        )
        .group_by(TransactionLine.customer_id)
        .all()
    )
    rev_map = {cid: total or 0 for cid, total in rev_q}

    result = []
    for c in customers:
        result.append({
            "id": c.id,
            "name": c.name,
            "business_no": c.business_no,
            "notes": c.notes,
            "contacts": [_contact_to_dict(cc) for cc in c.contacts],
            "active_count": active_map.get(c.id, 0),
            "total_revenue": rev_map.get(c.id, 0),
        })
    return result


def _get_owner_contract_ids(db: Session, user_id: int) -> list[int]:
    """사용자가 담당(owner)인 계약 ID 목록 (Contract 또는 Period 레벨)."""
    # Contract 레벨 owner
    q1 = db.query(Contract.id).filter(
        Contract.owner_user_id == user_id,
        Contract.status != "cancelled",
    )
    # Period 레벨 owner (Period.owner_user_id가 설정된 경우)
    q2 = (
        db.query(ContractPeriod.contract_id)
        .join(ContractPeriod.contract)
        .filter(
            ContractPeriod.owner_user_id == user_id,
            Contract.status != "cancelled",
        )
        .distinct()
    )
    ids = {row[0] for row in q1.all()}
    ids.update(row[0] for row in q2.all())
    return list(ids)


def _collect_customer_ids(db: Session, contract_ids: list[int]) -> set[int]:
    """계약 ID 목록으로부터 관련 거래처 ID를 수집."""
    customer_ids: set[int] = set()
    customer_ids.update(
        cid
        for cid, in db.query(Contract.end_customer_id)
        .filter(Contract.id.in_(contract_ids), Contract.end_customer_id.isnot(None))
        .all()
    )
    # Period 매출처
    customer_ids.update(
        cid
        for cid, in db.query(ContractPeriod.customer_id)
        .filter(ContractPeriod.contract_id.in_(contract_ids), ContractPeriod.customer_id.isnot(None))
        .distinct()
        .all()
    )
    customer_ids.update(
        cid
        for cid, in db.query(TransactionLine.customer_id)
        .filter(TransactionLine.contract_id.in_(contract_ids), TransactionLine.customer_id.isnot(None))
        .distinct()
        .all()
    )
    customer_ids.update(
        cid
        for cid, in db.query(Receipt.customer_id)
        .filter(Receipt.contract_id.in_(contract_ids), Receipt.customer_id.isnot(None))
        .distinct()
        .all()
    )
    customer_ids.update(
        cid
        for cid, in db.query(ContractContact.customer_id)
        .join(ContractContact.contract_period)
        .filter(ContractPeriod.contract_id.in_(contract_ids), ContractContact.customer_id.isnot(None))
        .distinct()
        .all()
    )
    return customer_ids


def get_customer(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def get_or_create_by_name(
    db: Session,
    name: str,
    *,
    tax_contact_name: str | None = None,
    tax_contact_phone: str | None = None,
    tax_contact_email: str | None = None,
) -> Customer:
    name = name.strip()
    obj = db.query(Customer).filter(Customer.name == name).first()
    if not obj:
        obj = Customer(name=name)
        db.add(obj)
        db.flush()

    # 세금계산서 담당자 정보가 있으면 customer_contacts에 추가 (중복 방지)
    if tax_contact_name and tax_contact_name.strip():
        tc_name = tax_contact_name.strip()
        existing = (
            db.query(CustomerContact)
            .filter(
                CustomerContact.customer_id == obj.id,
                CustomerContact.name == tc_name,
            )
            .first()
        )
        if existing:
            # 기존 담당자에 세금계산서 역할 추가 (없으면)
            has_tax_role = any(r.role_type == "세금계산서" for r in existing.roles)
            if not has_tax_role:
                role = CustomerContactRole(
                    customer_contact_id=existing.id,
                    role_type="세금계산서",
                    is_default=True,
                )
                db.add(role)
                db.flush()
        else:
            contact = CustomerContact(
                customer_id=obj.id,
                name=tc_name,
                phone=tax_contact_phone.strip() if tax_contact_phone else None,
                email=tax_contact_email.strip() if tax_contact_email else None,
            )
            db.add(contact)
            db.flush()
            role = CustomerContactRole(
                customer_contact_id=contact.id,
                role_type="세금계산서",
                is_default=True,
            )
            db.add(role)
            db.flush()

    return obj


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    existing = db.query(Customer).filter(Customer.name == data.name.strip()).first()
    if existing:
        raise DuplicateError(f"동일한 거래처명이 이미 존재합니다: {data.name}")
    obj = Customer(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_customer(db: Session, customer_id: int) -> None:
    obj = db.get(Customer, customer_id)
    if not obj:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    # 참조 데이터가 있으면 삭제 불가
    if obj.contracts:
        raise BusinessRuleError("END 고객으로 등록된 사업이 있어 삭제할 수 없습니다.")
    transaction_line_count = db.query(TransactionLine).filter(TransactionLine.customer_id == customer_id).count()
    if transaction_line_count > 0:
        raise BusinessRuleError("매출/매입 실적이 있어 삭제할 수 없습니다.")
    receipt_count = db.query(Receipt).filter(Receipt.customer_id == customer_id).count()
    if receipt_count > 0:
        raise BusinessRuleError("입금 내역이 있어 삭제할 수 없습니다.")
    db.delete(obj)
    db.commit()


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    obj = db.get(Customer, customer_id)
    if not obj:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── CustomerContact CRUD ──────────────────────────────────────


def get_contacts(db: Session, customer_id: int) -> list[dict]:
    contacts = (
        db.query(CustomerContact)
        .options(joinedload(CustomerContact.roles))
        .filter(CustomerContact.customer_id == customer_id)
        .order_by(CustomerContact.name, CustomerContact.id)
        .all()
    )
    return [_contact_to_dict(c) for c in contacts]


def create_contact(db: Session, customer_id: int, data: CustomerContactCreate) -> dict:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    obj = CustomerContact(
        customer_id=customer_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
    )
    db.add(obj)
    db.flush()
    for role_data in data.roles:
        if role_data.is_default:
            _clear_default(db, customer_id, role_data.role_type)
        role = CustomerContactRole(
            customer_contact_id=obj.id,
            role_type=role_data.role_type,
            is_default=role_data.is_default,
        )
        db.add(role)
    db.commit()
    db.refresh(obj)
    return _contact_to_dict(obj)


def update_contact(db: Session, contact_id: int, data: CustomerContactUpdate) -> dict:
    obj = db.get(CustomerContact, contact_id)
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    updates = data.model_dump(exclude_unset=True)
    # 기본 필드 업데이트
    for field in ("name", "phone", "email"):
        if field in updates:
            setattr(obj, field, updates[field])
    # 역할 업데이트 (전달된 경우 전체 교체)
    if "roles" in updates and updates["roles"] is not None:
        # 기존 역할 삭제
        for role in list(obj.roles):
            db.delete(role)
        db.flush()
        # 새 역할 추가
        for role_data in data.roles:
            if role_data.is_default:
                _clear_default(db, obj.customer_id, role_data.role_type, exclude_contact_id=obj.id)
            role = CustomerContactRole(
                customer_contact_id=obj.id,
                role_type=role_data.role_type,
                is_default=role_data.is_default,
            )
            db.add(role)
    db.commit()
    db.refresh(obj)
    return _contact_to_dict(obj)


def delete_contact(db: Session, contact_id: int) -> None:
    obj = db.get(CustomerContact, contact_id)
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    db.delete(obj)
    db.commit()


def list_related_contracts(db: Session, customer_id: int, current_user=None) -> dict:
    """거래처와 관련된 사업 목록 (역할, 재무 요약 포함).

    Returns:
        {"summary": {active_count, completed_count, total_revenue}, "contracts": [...]}
    """
    # ── 1) 관련 사업 ID 수집 + 역할별 분류 ──
    end_cust_ids = {
        r[0] for r in db.query(Contract.id).filter(Contract.end_customer_id == customer_id).all()
    }
    period_cust_ids = {
        r[0]
        for r in db.query(ContractPeriod.contract_id)
        .filter(ContractPeriod.customer_id == customer_id)
        .distinct()
        .all()
    }
    contact_cust_ids = {
        r[0]
        for r in db.query(ContractPeriod.contract_id)
        .join(ContractContact, ContractContact.contract_period_id == ContractPeriod.id)
        .filter(ContractContact.customer_id == customer_id)
        .distinct()
        .all()
    }
    cost_cust_ids = {
        r[0]
        for r in db.query(TransactionLine.contract_id)
        .filter(TransactionLine.customer_id == customer_id, TransactionLine.line_type == "cost")
        .distinct()
        .all()
    }
    revenue_cust_ids = {
        r[0]
        for r in db.query(TransactionLine.contract_id)
        .filter(TransactionLine.customer_id == customer_id, TransactionLine.line_type == "revenue")
        .distinct()
        .all()
    }
    receipt_cust_ids = {
        r[0]
        for r in db.query(Receipt.contract_id).filter(Receipt.customer_id == customer_id).distinct().all()
    }

    contract_ids = end_cust_ids | period_cust_ids | contact_cust_ids | cost_cust_ids | revenue_cust_ids | receipt_cust_ids
    if not contract_ids:
        return {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    if current_user and current_user.role != ROLE_ADMIN:
        visible_ids = set(list_accessible_contract_ids(db, current_user))
        contract_ids &= visible_ids
    if not contract_ids:
        return {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    # ── 2) 사업 조회 (Period 있는 활성 사업) ──
    contracts = (
        db.query(Contract)
        .options(joinedload(Contract.end_customer), joinedload(Contract.owner))
        .filter(
            Contract.id.in_(contract_ids),
            Contract.status != "cancelled",
            Contract.periods.any(),
        )
        .order_by(Contract.id.desc())
        .all()
    )
    if not contracts:
        return {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    active_contract_ids = [c.id for c in contracts]

    # ── 3) 사업별 매출/매입 벌크 집계 ──
    fin_rows = (
        db.query(
            TransactionLine.contract_id,
            TransactionLine.line_type,
            func.sum(TransactionLine.supply_amount),
        )
        .filter(TransactionLine.contract_id.in_(active_contract_ids))
        .group_by(TransactionLine.contract_id, TransactionLine.line_type)
        .all()
    )
    fin_map: dict[int, dict[str, int]] = {}
    for cid, lt, total in fin_rows:
        fin_map.setdefault(cid, {"revenue": 0, "cost": 0})
        if lt == "revenue":
            fin_map[cid]["revenue"] = total or 0
        elif lt == "cost":
            fin_map[cid]["cost"] = total or 0

    # ── 4) 최신 Period 정보 (stage, 기간) ──
    all_periods = (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id.in_(active_contract_ids))
        .order_by(ContractPeriod.period_year.desc())
        .all()
    )
    latest_period_map: dict[int, ContractPeriod] = {}
    period_range_map: dict[int, str] = {}
    # 사업별 모든 period 완료 여부: 하나라도 미완료면 진행중
    all_completed_map: dict[int, bool] = {}
    for p in all_periods:
        if p.contract_id not in latest_period_map:
            latest_period_map[p.contract_id] = p
        if p.contract_id not in all_completed_map:
            all_completed_map[p.contract_id] = True
        if not p.is_completed:
            all_completed_map[p.contract_id] = False
    # 기간 범위: 전체 Period의 min start ~ max end
    for p in all_periods:
        cid = p.contract_id
        if cid not in period_range_map:
            period_range_map[cid] = ""
    # 벌크로 min/max 계산
    range_rows = (
        db.query(
            ContractPeriod.contract_id,
            func.min(ContractPeriod.start_month),
            func.max(ContractPeriod.end_month),
        )
        .filter(ContractPeriod.contract_id.in_(active_contract_ids))
        .group_by(ContractPeriod.contract_id)
        .all()
    )
    for cid, smin, emax in range_rows:
        s = smin[:7] if smin else ""
        e = emax[:7] if emax else ""
        period_range_map[cid] = f"{s} ~ {e}" if s or e else ""

    # ── 5) 결과 생성 ──
    result = []
    total_revenue = 0
    active_count = 0
    completed_count = 0

    for c in contracts:
        fin = fin_map.get(c.id, {"revenue": 0, "cost": 0})
        rev = fin["revenue"]
        cost = fin["cost"]
        gp_pct = round((rev - cost) / rev * 100, 1) if rev > 0 else None
        latest_p = latest_period_map.get(c.id)
        stage = latest_p.stage if latest_p else ""

        # 역할 판별
        roles: list[str] = []
        is_revenue = c.id in period_cust_ids or c.id in revenue_cust_ids
        if c.id in end_cust_ids and not is_revenue:
            roles.append("END고객")
        if is_revenue:
            roles.append("매출처")
        if c.id in cost_cust_ids:
            roles.append("매입처")
        if c.id in contact_cust_ids:
            roles.append("담당자")

        owner_name = c.owner.name if c.owner else None
        end_customer_name = c.end_customer.name if c.end_customer else None
        latest_period_id = latest_p.id if latest_p else None
        is_all_completed = all_completed_map.get(c.id, False)
        result.append({
            "id": c.id,
            "latest_period_id": latest_period_id,
            "contract_code": c.contract_code,
            "contract_name": c.contract_name,
            "contract_type": c.contract_type,
            "status": c.status,
            "stage": stage,
            "is_all_completed": is_all_completed,
            "period_range": period_range_map.get(c.id, ""),
            "revenue_amount": rev,
            "cost_amount": cost,
            "gp_pct": gp_pct,
            "end_customer_name": end_customer_name,
            "owner_name": owner_name,
            "roles": roles,
            "notes": c.notes,
        })

        total_revenue += rev
        if is_all_completed:
            completed_count += 1
        else:
            active_count += 1

    return {
        "summary": {
            "active_count": active_count,
            "completed_count": completed_count,
            "total_revenue": total_revenue,
        },
        "contracts": result,
    }


def list_customer_financials(db: Session, customer_id: int, current_user=None) -> dict:
    """거래처 기준 매출·매입 월별 집계 + 미수금.

    Returns:
        {"summary": {total_revenue, total_cost, ar}, "months": [...]}
    """
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundError("거래처를 찾을 수 없습니다.")

    # 접근 제어: 거래처와 관련된 사업 중 열람 가능한 것만
    related = list_related_contracts(db, customer_id, current_user=current_user)
    contract_ids = [c["id"] for c in related["contracts"]]
    if not contract_ids:
        return {"summary": {"total_revenue": 0, "total_cost": 0, "ar": 0}, "months": []}

    # 월별 매출/매입 집계 (해당 거래처가 customer인 라인 + 관련 사업 범위)
    rows = (
        db.query(
            TransactionLine.revenue_month,
            TransactionLine.line_type,
            func.sum(TransactionLine.supply_amount),
        )
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
        )
        .group_by(TransactionLine.revenue_month, TransactionLine.line_type)
        .order_by(TransactionLine.revenue_month)
        .all()
    )

    month_map: dict[str, dict[str, int]] = {}
    total_revenue = 0
    total_cost = 0
    for month, lt, total in rows:
        month_map.setdefault(month, {"month": month, "revenue": 0, "cost": 0})
        amt = total or 0
        if lt == "revenue":
            month_map[month]["revenue"] = amt
            total_revenue += amt
        elif lt == "cost":
            month_map[month]["cost"] = amt
            total_cost += amt

    months = []
    for m in sorted(month_map.keys()):
        d = month_map[m]
        rev, cost = d["revenue"], d["cost"]
        gp = rev - cost
        gp_pct = round(gp / rev * 100, 1) if rev > 0 else None
        months.append({
            "month": m[:7] if len(m) >= 7 else m,
            "revenue": rev,
            "cost": cost,
            "gp": gp,
            "gp_pct": gp_pct,
        })

    # 미수금: 해당 거래처의 매출 확정 합계 - ReceiptMatch 합계
    confirmed_revenue = (
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
            TransactionLine.line_type == "revenue",
            TransactionLine.status == "확정",
        )
        .scalar()
    )
    matched_total = (
        db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0))
        .join(ReceiptMatch.transaction_line)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
            TransactionLine.line_type == "revenue",
        )
        .scalar()
    )
    ar = confirmed_revenue - matched_total

    return {
        "summary": {"total_revenue": total_revenue, "total_cost": total_cost, "ar": ar},
        "months": months,
    }


def list_customer_receipts(db: Session, customer_id: int, current_user=None) -> dict:
    """거래처 기준 입금 내역 + 미수금 잔액.

    Returns:
        {"summary": {total_receipt, ar_balance}, "receipts": [...]}
    """
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundError("거래처를 찾을 수 없습니다.")

    # 접근 제어
    related = list_related_contracts(db, customer_id, current_user=current_user)
    contract_ids = [c["id"] for c in related["contracts"]]
    if not contract_ids:
        return {"summary": {"total_receipt": 0, "ar_balance": 0}, "receipts": []}

    rows = (
        db.query(Receipt)
        .filter(
            Receipt.contract_id.in_(contract_ids),
            Receipt.customer_id == customer_id,
        )
        .order_by(Receipt.receipt_date.desc())
        .all()
    )

    # 사업명 매핑
    contract_map: dict[int, str] = {}
    for c in related["contracts"]:
        contract_map[c["id"]] = c["contract_name"]

    total_receipt = 0
    receipts = []
    for r in rows:
        total_receipt += r.amount
        receipts.append({
            "id": r.id,
            "receipt_date": r.receipt_date,
            "amount": r.amount,
            "contract_id": r.contract_id,
            "contract_name": contract_map.get(r.contract_id, ""),
            "description": r.description,
            "revenue_month": r.revenue_month[:7] if r.revenue_month and len(r.revenue_month) >= 7 else r.revenue_month,
        })

    # 미수금 잔액: 매출 확정 - ReceiptMatch 합계
    confirmed_revenue = (
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
            TransactionLine.line_type == "revenue",
            TransactionLine.status == "확정",
        )
        .scalar()
    )
    matched_total = (
        db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0))
        .join(ReceiptMatch.transaction_line)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
            TransactionLine.line_type == "revenue",
        )
        .scalar()
    )
    ar_balance = confirmed_revenue - matched_total

    return {
        "summary": {"total_receipt": total_receipt, "ar_balance": ar_balance},
        "receipts": receipts,
    }


def _clear_default(
    db: Session, customer_id: int, role_type: str, *, exclude_contact_id: int | None = None,
) -> None:
    """같은 거래처·같은 역할에서 기존 기본 담당자를 해제."""
    query = (
        db.query(CustomerContactRole)
        .join(CustomerContact)
        .filter(
            CustomerContact.customer_id == customer_id,
            CustomerContactRole.role_type == role_type,
            CustomerContactRole.is_default.is_(True),
        )
    )
    if exclude_contact_id:
        query = query.filter(CustomerContactRole.customer_contact_id != exclude_contact_id)
    for r in query.all():
        r.is_default = False


def _contact_to_dict(obj: CustomerContact) -> dict:
    """CustomerContact ORM 객체를 dict로 변환."""
    return {
        "id": obj.id,
        "customer_id": obj.customer_id,
        "name": obj.name,
        "phone": obj.phone,
        "email": obj.email,
        "roles": [
            {"id": r.id, "role_type": r.role_type, "is_default": r.is_default}
            for r in obj.roles
        ],
    }
