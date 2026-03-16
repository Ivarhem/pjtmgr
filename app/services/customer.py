from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.authorization import has_full_contract_scope, list_accessible_contract_ids

if TYPE_CHECKING:
    from app.models.user import User
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
    db: Session, current_user: User | None = None, *, my_only: bool = False
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
    elif not current_user or has_full_contract_scope(current_user):
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


def _related_contract_ids(db: Session, customer_id: int) -> set[int]:
    """거래처와 관련된 모든 사업 ID를 수집한다."""
    roles = _related_contract_roles(db, customer_id)
    result: set[int] = set()
    for ids in roles.values():
        result |= ids
    return result


def _related_contract_roles(db: Session, customer_id: int) -> dict[str, set[int]]:
    """거래처와 관련된 사업 ID를 역할별로 분류하여 반환한다."""
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
    return {
        "end_customer": end_cust_ids,
        "period_customer": period_cust_ids,
        "contact": contact_cust_ids,
        "cost": cost_cust_ids,
        "revenue": revenue_cust_ids,
        "receipt": receipt_cust_ids,
    }


def list_related_contracts(db: Session, customer_id: int, current_user: User | None = None) -> dict:
    """거래처와 관련된 사업 목록 (역할, 재무 요약 포함).

    Returns:
        {"summary": {active_count, completed_count, total_revenue}, "contracts": [...]}
    """
    _empty = {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    # ── 1) 관련 사업 ID 수집 + 역할별 분류 ──
    roles_map = _related_contract_roles(db, customer_id)
    end_cust_ids = roles_map["end_customer"]
    contract_ids: set[int] = set()
    for ids in roles_map.values():
        contract_ids |= ids
    if not contract_ids:
        return _empty

    if current_user and not has_full_contract_scope(current_user):
        visible_ids = set(list_accessible_contract_ids(db, current_user))
        contract_ids &= visible_ids
    if not contract_ids:
        return _empty

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

    # ── 3) Period 조회 ──
    all_periods = (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id.in_(active_contract_ids))
        .order_by(ContractPeriod.contract_id.desc(), ContractPeriod.period_year.desc())
        .all()
    )
    contract_map: dict[int, Contract] = {c.id: c for c in contracts}

    # ── 4) Period 단위 매출/매입 벌크 집계 ──
    # period_id → {revenue, cost} 매핑 (revenue_month 범위 기준)
    period_ids = [p.id for p in all_periods]
    fin_map: dict[int, dict[str, int]] = {}
    if period_ids:
        fin_rows = (
            db.query(
                ContractPeriod.id,
                TransactionLine.line_type,
                func.sum(TransactionLine.supply_amount),
            )
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .group_by(ContractPeriod.id, TransactionLine.line_type)
            .all()
        )
        for pid, lt, total in fin_rows:
            fin_map.setdefault(pid, {"revenue": 0, "cost": 0})
            if lt == "revenue":
                fin_map[pid]["revenue"] = total or 0
            elif lt == "cost":
                fin_map[pid]["cost"] = total or 0

    # ── 5) Period 단위 역할 판별 ──
    # Period별 매출처/매입처 세분화
    period_revenue_set: set[int] = set()
    period_cost_set: set[int] = set()
    if period_ids:
        rev_period_rows = (
            db.query(ContractPeriod.id)
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.customer_id == customer_id,
                TransactionLine.line_type == "revenue",
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .distinct()
            .all()
        )
        period_revenue_set = {r[0] for r in rev_period_rows}

        cost_period_rows = (
            db.query(ContractPeriod.id)
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.customer_id == customer_id,
                TransactionLine.line_type == "cost",
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .distinct()
            .all()
        )
        period_cost_set = {r[0] for r in cost_period_rows}

    # Period별 담당자 관계
    period_contact_set: set[int] = set()
    if period_ids:
        contact_period_rows = (
            db.query(ContractContact.contract_period_id)
            .filter(
                ContractContact.contract_period_id.in_(period_ids),
                ContractContact.customer_id == customer_id,
            )
            .distinct()
            .all()
        )
        period_contact_set = {r[0] for r in contact_period_rows}

    # Period별 매출처 (ContractPeriod.customer_id)
    period_cust_set: set[int] = {
        p.id for p in all_periods if p.customer_id == customer_id
    }

    # ── 6) Period 단위 결과 생성 ──
    result = []
    total_revenue = 0
    active_count = 0
    completed_count = 0

    for p in all_periods:
        c = contract_map.get(p.contract_id)
        if not c:
            continue

        fin = fin_map.get(p.id, {"revenue": 0, "cost": 0})
        rev = fin["revenue"]
        cost = fin["cost"]
        gp_pct = round((rev - cost) / rev * 100, 1) if rev > 0 else None

        is_period_completed = p.is_completed

        # 기간 범위
        s = p.start_month[:7] if p.start_month else ""
        e = p.end_month[:7] if p.end_month else ""
        period_range = f"{s} ~ {e}" if s or e else ""

        # 역할 판별 (Period 단위)
        roles: list[str] = []
        is_revenue = p.id in period_cust_set or p.id in period_revenue_set
        if c.id in end_cust_ids and not is_revenue:
            roles.append("END고객")
        if is_revenue:
            roles.append("매출처")
        if p.id in period_cost_set:
            roles.append("매입처")
        if p.id in period_contact_set:
            roles.append("담당자")

        owner_name = c.owner.name if c.owner else None
        end_customer_name = c.end_customer.name if c.end_customer else None

        result.append({
            "id": c.id,
            "period_id": p.id,
            "period_label": p.period_label or f"Y{str(p.period_year)[-2:]}",
            "contract_code": c.contract_code,
            "contract_name": c.contract_name,
            "contract_type": c.contract_type,
            "status": c.status,
            "stage": p.stage or "",
            "is_completed": is_period_completed,
            "period_range": period_range,
            "revenue_amount": rev,
            "cost_amount": cost,
            "gp_pct": gp_pct,
            "end_customer_name": end_customer_name,
            "owner_name": owner_name,
            "roles": roles,
            "notes": c.notes,
        })

        if is_period_completed:
            completed_count += 1
        else:
            active_count += 1
        total_revenue += rev

    return {
        "summary": {
            "active_count": active_count,
            "completed_count": completed_count,
            "total_revenue": total_revenue,
        },
        "contracts": result,
    }


def _build_contract_completed_map(db: Session, contract_ids: list[int]) -> dict[int, bool]:
    """사업별 완료 여부 맵 (모든 period가 is_completed이면 True)."""
    periods = (
        db.query(ContractPeriod.contract_id, ContractPeriod.is_completed)
        .filter(ContractPeriod.contract_id.in_(contract_ids))
        .all()
    )
    completed_map: dict[int, bool] = {}
    for cid, is_comp in periods:
        if cid not in completed_map:
            completed_map[cid] = True
        if not is_comp:
            completed_map[cid] = False
    return completed_map


def _build_period_lookup(db: Session, contract_ids: list[int]) -> list[ContractPeriod]:
    """관련 사업의 모든 period를 조회한다."""
    return (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id.in_(contract_ids))
        .order_by(ContractPeriod.contract_id, ContractPeriod.period_year)
        .all()
    )


def _match_period(periods: list[ContractPeriod], contract_id: int, revenue_month: str) -> ContractPeriod | None:
    """revenue_month가 속하는 period를 찾는다 (start_month <= revenue_month <= end_month)."""
    for p in periods:
        if p.contract_id != contract_id:
            continue
        if p.start_month and p.end_month and p.start_month <= revenue_month <= p.end_month:
            return p
    # 범위 밖이면 가장 가까운 period 반환
    contract_periods = [p for p in periods if p.contract_id == contract_id]
    return contract_periods[-1] if contract_periods else None


def list_customer_financials(db: Session, customer_id: int, current_user: User | None = None) -> dict:
    """거래처 기준 매출·매입 period 단위 집계 + 미수금.

    Returns:
        {"summary": {total_revenue, total_cost, ar}, "lines": [...]}
        lines: 사업 그룹 행(_is_group=True) + period 디테일 행
    """
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundError("거래처를 찾을 수 없습니다.")

    related = list_related_contracts(db, customer_id, current_user=current_user)
    contract_ids = list({c["id"] for c in related["contracts"]})
    if not contract_ids:
        return {"summary": {"total_revenue": 0, "total_cost": 0, "ar": 0}, "lines": []}

    # period 조회 + 사업명 매핑
    all_periods = _build_period_lookup(db, contract_ids)
    contract_name_map: dict[int, str] = {}
    for c in related["contracts"]:
        contract_name_map.setdefault(c["id"], c["contract_name"])

    # 개별 TransactionLine 조회 → period 매칭
    txn_rows = (
        db.query(TransactionLine)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.customer_id == customer_id,
        )
        .all()
    )

    # period별 집계: key = (contract_id, period_id)
    period_fin: dict[tuple[int, int], dict] = {}
    for txn in txn_rows:
        p = _match_period(all_periods, txn.contract_id, txn.revenue_month or "")
        pid = p.id if p else 0
        key = (txn.contract_id, pid)
        if key not in period_fin:
            period_fin[key] = {
                "contract_id": txn.contract_id,
                "period_id": pid,
                "period_label": (p.period_label or f"Y{str(p.period_year)[-2:]}") if p else "",
                "is_completed": p.is_completed if p else False,
                "revenue": 0,
                "cost": 0,
            }
        amt = txn.supply_amount or 0
        if txn.line_type == "revenue":
            period_fin[key]["revenue"] += amt
        elif txn.line_type == "cost":
            period_fin[key]["cost"] += amt

    # 사업별 그룹 + period 디테일 행 구성
    # contract_id별로 모음
    from collections import defaultdict
    by_contract: dict[int, list[dict]] = defaultdict(list)
    for (cid, _pid), d in period_fin.items():
        by_contract[cid].append(d)

    total_revenue = 0
    total_cost = 0
    lines: list[dict] = []

    for cid in sorted(by_contract.keys(), key=lambda x: contract_name_map.get(x, "")):
        details = sorted(by_contract[cid], key=lambda x: x["period_label"])
        g_rev = sum(d["revenue"] for d in details)
        g_cost = sum(d["cost"] for d in details)
        g_gp = g_rev - g_cost
        g_gp_pct = round(g_gp / g_rev * 100, 1) if g_rev > 0 else None
        g_completed = all(d["is_completed"] for d in details)
        total_revenue += g_rev
        total_cost += g_cost

        # 그룹 행
        lines.append({
            "_is_group": True,
            "_group_key": cid,
            "contract_id": cid,
            "contract_name": contract_name_map.get(cid, ""),
            "period_label": "",
            "revenue": g_rev,
            "cost": g_cost,
            "gp": g_gp,
            "gp_pct": g_gp_pct,
            "is_completed": g_completed,
        })
        # 디테일 행
        for d in details:
            rev, cost = d["revenue"], d["cost"]
            gp = rev - cost
            gp_pct = round(gp / rev * 100, 1) if rev > 0 else None
            lines.append({
                "_is_group": False,
                "_group_key": cid,
                "contract_id": cid,
                "contract_name": "",
                "period_label": d["period_label"],
                "revenue": rev,
                "cost": cost,
                "gp": gp,
                "gp_pct": gp_pct,
                "is_completed": d["is_completed"],
            })

    # 미수금
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
        "lines": lines,
    }


def list_customer_receipts(db: Session, customer_id: int, current_user: User | None = None) -> dict:
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
        .order_by(Receipt.contract_id, Receipt.receipt_date.desc())
        .all()
    )

    contract_name_map: dict[int, str] = {}
    for c in related["contracts"]:
        contract_name_map.setdefault(c["id"], c["contract_name"])

    all_periods = _build_period_lookup(db, contract_ids)

    # 사업+period별 그룹화
    from collections import defaultdict
    by_group: dict[tuple[int, int], list[dict]] = defaultdict(list)
    total_receipt = 0

    for r in rows:
        total_receipt += r.amount
        p = _match_period(all_periods, r.contract_id, r.revenue_month or "")
        pid = p.id if p else 0
        by_group[(r.contract_id, pid)].append({
            "id": r.id,
            "receipt_date": r.receipt_date,
            "amount": r.amount,
            "description": r.description,
            "revenue_month": r.revenue_month[:7] if r.revenue_month and len(r.revenue_month) >= 7 else r.revenue_month,
        })

    # 그룹 행 + 디테일 행
    receipts: list[dict] = []
    # 사업별로 모음
    by_contract: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for (cid, pid) in by_group:
        by_contract[cid].append((cid, pid))

    period_map = {p.id: p for p in all_periods}

    for cid in sorted(by_contract.keys(), key=lambda x: contract_name_map.get(x, "")):
        keys = sorted(by_contract[cid], key=lambda k: (period_map.get(k[1]).period_year if period_map.get(k[1]) else 0))
        c_total = sum(r["amount"] for k in keys for r in by_group[k])
        c_completed = all(period_map[k[1]].is_completed for k in keys if k[1] in period_map)

        # 사업 그룹 행
        receipts.append({
            "_is_group": True,
            "_group_key": cid,
            "contract_id": cid,
            "contract_name": contract_name_map.get(cid, ""),
            "period_label": "",
            "receipt_date": "",
            "amount": c_total,
            "description": f"{len([r for k in keys for r in by_group[k]])}건",
            "revenue_month": "",
            "is_completed": c_completed,
        })
        # period별 디테일 행
        for key in keys:
            p = period_map.get(key[1])
            p_label = (p.period_label or f"Y{str(p.period_year)[-2:]}") if p else ""
            p_completed = p.is_completed if p else False
            detail_rows = by_group[key]
            p_total = sum(r["amount"] for r in detail_rows)

            # period 소계 행
            receipts.append({
                "_is_group": True,
                "_group_key": cid,
                "_period_group": True,
                "contract_id": cid,
                "contract_name": "",
                "period_label": p_label,
                "receipt_date": "",
                "amount": p_total,
                "description": f"{len(detail_rows)}건",
                "revenue_month": "",
                "is_completed": p_completed,
            })
            # 개별 입금 행
            for dr in detail_rows:
                receipts.append({
                    "_is_group": False,
                    "_group_key": cid,
                    "contract_id": cid,
                    "contract_name": "",
                    "period_label": "",
                    "receipt_date": dr["receipt_date"],
                    "amount": dr["amount"],
                    "description": dr["description"],
                    "revenue_month": dr["revenue_month"],
                    "is_completed": p_completed,
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
