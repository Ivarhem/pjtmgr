from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import has_full_contract_scope, list_accessible_contract_ids
from app.core.code_generator import next_partner_code

if TYPE_CHECKING:
    from app.modules.common.models.user import User
from app.modules.common.models.partner import Partner
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.common.models.partner_contact_role import PartnerContactRole
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_contact import ContractContact
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.transaction_line import TransactionLine
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.models.receipt_match import ReceiptMatch
from app.modules.common.schemas.partner import PartnerCreate, PartnerUpdate
from app.modules.common.schemas.partner_contact import PartnerContactCreate, PartnerContactUpdate
from app.core.exceptions import NotFoundError, BusinessRuleError, DuplicateError
from app.modules.common.services._partner_helpers import (
    _related_contract_ids,
    list_related_contracts,
    list_partner_financials,
    list_partner_receipts,
)

# re-export for external consumers
__all__ = [
    "list_partners", "get_partner", "create_partner", "update_partner", "delete_partner",
    "get_or_create_by_name", "get_contacts", "create_contact", "update_contact", "delete_contact",
    "_related_contract_ids", "list_related_contracts", "list_partner_financials", "list_partner_receipts",
]


def list_partners(
    db: Session,
    current_user: User | None = None,
    *,
    my_only: bool = False,
    partner_type: str | None = None,
) -> list[dict]:
    """거래처 목록 (요약 데이터 포함: active_count, total_revenue)."""
    if my_only and current_user:
        contract_ids = _get_owner_contract_ids(db, current_user.id)
        if not contract_ids:
            return []
        partner_ids = _collect_partner_ids(db, contract_ids)
        if not partner_ids:
            return []
        query = db.query(Partner).filter(Partner.id.in_(partner_ids))
    elif not current_user or has_full_contract_scope(current_user):
        query = db.query(Partner)
    else:
        contract_ids = list_accessible_contract_ids(db, current_user)
        if not contract_ids:
            return []
        partner_ids = _collect_partner_ids(db, contract_ids)
        if not partner_ids:
            return []
        query = db.query(Partner).filter(Partner.id.in_(partner_ids))

    if partner_type:
        query = query.filter(Partner.partner_type == partner_type)

    partners = query.order_by(Partner.name).all()

    if not partners:
        return []

    return _enrich_partners_with_summary(db, partners)


def _enrich_partners_with_summary(db: Session, partners: list[Partner]) -> list[dict]:
    """거래처 ORM 목록에 active_count, total_revenue 요약을 추가하여 dict 리스트로 반환."""
    partner_ids = [c.id for c in partners]

    # 1) partner_id별 진행중 사업 건수 (stage != '계약완료')
    # end_partner 또는 period partner로 연결된 사업 기준
    active_q = (
        db.query(
            Partner.id,
            func.count(func.distinct(Contract.id)),
        )
        .outerjoin(Contract, Contract.end_partner_id == Partner.id)
        .outerjoin(ContractPeriod, ContractPeriod.contract_id == Contract.id)
        .filter(
            Partner.id.in_(partner_ids),
            Contract.status != "cancelled",
            ContractPeriod.stage != "계약완료",
        )
        .group_by(Partner.id)
        .all()
    )
    active_map = {cid: cnt for cid, cnt in active_q}

    # 2) partner_id별 매출 합계 (TransactionLine에서 해당 partner가 매출처인 것)
    rev_q = (
        db.query(
            TransactionLine.partner_id,
            func.sum(TransactionLine.supply_amount),
        )
        .filter(
            TransactionLine.partner_id.in_(partner_ids),
            TransactionLine.line_type == "revenue",
        )
        .group_by(TransactionLine.partner_id)
        .all()
    )
    rev_map = {cid: total or 0 for cid, total in rev_q}

    result = []
    for c in partners:
        result.append({
            "id": c.id,
            "partner_code": c.partner_code,
            "name": c.name,
            "business_no": c.business_no,
            "notes": c.notes,
            "partner_type": c.partner_type,
            "phone": c.phone,
            "address": c.address,
            "note": c.note,
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


def _collect_partner_ids(db: Session, contract_ids: list[int]) -> set[int]:
    """계약 ID 목록으로부터 관련 거래처 ID를 수집."""
    partner_ids: set[int] = set()
    partner_ids.update(
        cid
        for cid, in db.query(Contract.end_partner_id)
        .filter(Contract.id.in_(contract_ids), Contract.end_partner_id.isnot(None))
        .all()
    )
    # Period 매출처
    partner_ids.update(
        cid
        for cid, in db.query(ContractPeriod.partner_id)
        .filter(ContractPeriod.contract_id.in_(contract_ids), ContractPeriod.partner_id.isnot(None))
        .distinct()
        .all()
    )
    partner_ids.update(
        cid
        for cid, in db.query(TransactionLine.partner_id)
        .filter(TransactionLine.contract_id.in_(contract_ids), TransactionLine.partner_id.isnot(None))
        .distinct()
        .all()
    )
    partner_ids.update(
        cid
        for cid, in db.query(Receipt.partner_id)
        .filter(Receipt.contract_id.in_(contract_ids), Receipt.partner_id.isnot(None))
        .distinct()
        .all()
    )
    partner_ids.update(
        cid
        for cid, in db.query(ContractContact.partner_id)
        .join(ContractContact.contract_period)
        .filter(ContractPeriod.contract_id.in_(contract_ids), ContractContact.partner_id.isnot(None))
        .distinct()
        .all()
    )
    return partner_ids


def get_partner(db: Session, partner_id: int) -> Partner | None:
    return db.get(Partner, partner_id)


def get_or_create_by_name(
    db: Session,
    name: str,
    *,
    tax_contact_name: str | None = None,
    tax_contact_phone: str | None = None,
    tax_contact_email: str | None = None,
) -> Partner:
    name = name.strip()
    obj = db.query(Partner).filter(Partner.name == name).first()
    if not obj:
        obj = Partner(name=name, partner_code=next_partner_code(db))
        db.add(obj)
        db.flush()

    # 세금계산서 담당자 정보가 있으면 partner_contacts에 추가 (중복 방지)
    if tax_contact_name and tax_contact_name.strip():
        tc_name = tax_contact_name.strip()
        existing = (
            db.query(PartnerContact)
            .filter(
                PartnerContact.partner_id == obj.id,
                PartnerContact.name == tc_name,
            )
            .first()
        )
        if existing:
            # 기존 담당자에 세금계산서 역할 추가 (없으면)
            has_tax_role = any(r.role_type == "세금계산서" for r in existing.roles)
            if not has_tax_role:
                role = PartnerContactRole(
                    partner_contact_id=existing.id,
                    role_type="세금계산서",
                    is_default=True,
                )
                db.add(role)
                db.flush()
        else:
            contact = PartnerContact(
                partner_id=obj.id,
                name=tc_name,
                phone=tax_contact_phone.strip() if tax_contact_phone else None,
                email=tax_contact_email.strip() if tax_contact_email else None,
            )
            db.add(contact)
            db.flush()
            role = PartnerContactRole(
                partner_contact_id=contact.id,
                role_type="세금계산서",
                is_default=True,
            )
            db.add(role)
            db.flush()

    return obj


def create_partner(db: Session, data: PartnerCreate) -> Partner:
    existing = db.query(Partner).filter(Partner.name == data.name.strip()).first()
    if existing:
        raise DuplicateError(f"동일한 거래처명이 이미 존재합니다: {data.name}")
    obj = Partner(**data.model_dump())
    obj.partner_code = next_partner_code(db)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_partner(db: Session, partner_id: int) -> None:
    obj = db.get(Partner, partner_id)
    if not obj:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    # 참조 데이터가 있으면 삭제 불가
    if obj.contracts:
        raise BusinessRuleError("END 고객으로 등록된 사업이 있어 삭제할 수 없습니다.")
    transaction_line_count = db.query(TransactionLine).filter(TransactionLine.partner_id == partner_id).count()
    if transaction_line_count > 0:
        raise BusinessRuleError("매출/매입 실적이 있어 삭제할 수 없습니다.")
    receipt_count = db.query(Receipt).filter(Receipt.partner_id == partner_id).count()
    if receipt_count > 0:
        raise BusinessRuleError("입금 내역이 있어 삭제할 수 없습니다.")
    db.delete(obj)
    db.commit()


def update_partner(db: Session, partner_id: int, data: PartnerUpdate) -> Partner:
    obj = db.get(Partner, partner_id)
    if not obj:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    updates = data.model_dump(exclude_unset=True)
    if "partner_code" in updates:
        raise BusinessRuleError("업체코드는 변경할 수 없습니다.")
    if "name" in updates and updates["name"] != obj.name:
        dup = db.query(Partner).filter(
            func.lower(Partner.name) == updates["name"].strip().lower(),
            Partner.id != partner_id,
        ).first()
        if dup:
            raise DuplicateError(f"'{updates['name']}' 거래처가 이미 존재합니다.")
    for field, value in updates.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── PartnerContact CRUD ──────────────────────────────────────


def get_contacts(db: Session, partner_id: int) -> list[dict]:
    contacts = (
        db.query(PartnerContact)
        .options(joinedload(PartnerContact.roles))
        .filter(PartnerContact.partner_id == partner_id)
        .order_by(PartnerContact.name, PartnerContact.id)
        .all()
    )
    return [_contact_to_dict(c) for c in contacts]


def create_contact(db: Session, partner_id: int, data: PartnerContactCreate) -> dict:
    partner = db.get(Partner, partner_id)
    if not partner:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    obj = PartnerContact(
        partner_id=partner_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        department=data.department,
        title=data.title,
        emergency_phone=data.emergency_phone,
        note=data.note,
    )
    db.add(obj)
    db.flush()
    for role_data in data.roles:
        if role_data.is_default:
            _clear_default(db, partner_id, role_data.role_type)
        role = PartnerContactRole(
            partner_contact_id=obj.id,
            role_type=role_data.role_type,
            is_default=role_data.is_default,
        )
        db.add(role)
    db.commit()
    db.refresh(obj)
    return _contact_to_dict(obj)


def update_contact(db: Session, contact_id: int, data: PartnerContactUpdate) -> dict:
    obj = db.get(PartnerContact, contact_id)
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    updates = data.model_dump(exclude_unset=True)
    # 기본 필드 업데이트
    for field in ("name", "phone", "email", "department", "title", "emergency_phone", "note"):
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
                _clear_default(db, obj.partner_id, role_data.role_type, exclude_contact_id=obj.id)
            role = PartnerContactRole(
                partner_contact_id=obj.id,
                role_type=role_data.role_type,
                is_default=role_data.is_default,
            )
            db.add(role)
    db.commit()
    db.refresh(obj)
    return _contact_to_dict(obj)


def delete_contact(db: Session, contact_id: int) -> None:
    obj = db.get(PartnerContact, contact_id)
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    db.delete(obj)
    db.commit()




def _clear_default(
    db: Session, partner_id: int, role_type: str, *, exclude_contact_id: int | None = None,
) -> None:
    """같은 거래처·같은 역할에서 기존 기본 담당자를 해제."""
    query = (
        db.query(PartnerContactRole)
        .join(PartnerContact)
        .filter(
            PartnerContact.partner_id == partner_id,
            PartnerContactRole.role_type == role_type,
            PartnerContactRole.is_default.is_(True),
        )
    )
    if exclude_contact_id:
        query = query.filter(PartnerContactRole.partner_contact_id != exclude_contact_id)
    for r in query.all():
        r.is_default = False


def _contact_to_dict(obj: PartnerContact) -> dict:
    """PartnerContact ORM 객체를 dict로 변환."""
    return {
        "id": obj.id,
        "partner_id": obj.partner_id,
        "name": obj.name,
        "phone": obj.phone,
        "email": obj.email,
        "department": obj.department,
        "title": obj.title,
        "emergency_phone": obj.emergency_phone,
        "note": obj.note,
        "roles": [
            {"id": r.id, "role_type": r.role_type, "is_default": r.is_default}
            for r in obj.roles
        ],
    }
