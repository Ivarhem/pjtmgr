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
from app.services._customer_helpers import (
    _related_contract_ids,
    list_related_contracts,
    list_customer_financials,
    list_customer_receipts,
)

# re-export for external consumers
__all__ = [
    "list_customers", "get_customer", "create_customer", "update_customer", "delete_customer",
    "get_or_create_by_name", "get_contacts", "create_contact", "update_contact", "delete_contact",
    "_related_contract_ids", "list_related_contracts", "list_customer_financials", "list_customer_receipts",
]


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
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != obj.name:
        dup = db.query(Customer).filter(
            func.lower(Customer.name) == updates["name"].strip().lower(),
            Customer.id != customer_id,
        ).first()
        if dup:
            raise DuplicateError(f"'{updates['name']}' 거래처가 이미 존재합니다.")
    for field, value in updates.items():
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
