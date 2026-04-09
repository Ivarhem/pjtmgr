from sqlalchemy.orm import Session, joinedload
from app.core.auth.authorization import check_period_access, has_full_contract_scope, list_accessible_contract_ids
from app.modules.accounting.models.contract_contact import ContractContact
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.contract import Contract
from app.modules.common.models.partner import Partner
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.common.models.user import User
from app.core.exceptions import NotFoundError
from app.modules.accounting.schemas.contract_contact import ContractContactCreate, ContractContactUpdate


def list_by_period(db: Session, period_id: int) -> list[dict]:
    """Period의 모든 담당자 목록."""
    rows = (
        db.query(ContractContact)
        .options(joinedload(ContractContact.partner_contact))
        .filter(ContractContact.contract_period_id == period_id)
        .order_by(ContractContact.partner_id, ContractContact.contact_type, ContractContact.rank)
        .all()
    )
    return [_to_dict(r) for r in rows]


def list_by_contract(db: Session, contract_id: int) -> list[dict]:
    """사업의 모든 Period에 걸친 담당자 목록."""
    period_ids = [
        p.id for p in db.query(ContractPeriod.id).filter(ContractPeriod.contract_id == contract_id).all()
    ]
    if not period_ids:
        return []
    rows = (
        db.query(ContractContact)
        .options(joinedload(ContractContact.partner_contact))
        .filter(ContractContact.contract_period_id.in_(period_ids))
        .order_by(ContractContact.partner_id, ContractContact.contact_type, ContractContact.rank)
        .all()
    )
    return [_to_dict(r) for r in rows]


def list_by_partner(db: Session, partner_id: int, current_user: User | None = None) -> list[dict]:
    """거래처와 관련된 모든 사업별 담당자 목록 (사업명 포함)."""
    q = (
        db.query(ContractContact)
        .options(
            joinedload(ContractContact.contract_period).joinedload(ContractPeriod.contract),
            joinedload(ContractContact.partner_contact),
        )
        .filter(ContractContact.partner_id == partner_id)
    )
    if current_user and not has_full_contract_scope(current_user):
        contract_ids = list_accessible_contract_ids(db, current_user)
        if not contract_ids:
            return []
        q = q.join(ContractContact.contract_period).filter(ContractPeriod.contract_id.in_(contract_ids))
    rows = q.order_by(ContractContact.contract_period_id.desc(), ContractContact.contact_type).all()
    result = []
    for r in rows:
        d = _to_dict(r)
        contract = r.contract_period.contract if r.contract_period else None
        d["contract_name"] = contract.contract_name if contract else None
        d["contract_code"] = contract.contract_code if contract else None
        d["period_label"] = r.contract_period.period_label if r.contract_period else None
        d["partner_name"] = r.partner.name if r.partner else None
        result.append(d)
    return result


def list_by_partner_pivoted(db: Session, partner_id: int, current_user: User | None = None) -> list[dict]:
    """거래처의 사업별 담당자를 period 단위로 피벗하여 반환.

    관련 사업의 **모든 period**를 행으로 포함 (담당자 미배정 period 포함).
    한 행에 영업(정) + 세금계산서(정) + 업무(정) 담당자 정보를 함께 포함.
    """
    from app.modules.common.services.partner import _related_contract_ids

    contract_ids = _related_contract_ids(db, partner_id)
    if current_user and not has_full_contract_scope(current_user):
        visible = set(list_accessible_contract_ids(db, current_user))
        contract_ids &= visible
    if not contract_ids:
        return []

    # 모든 period 조회 (cancelled 제외)
    all_periods = (
        db.query(ContractPeriod)
        .join(Contract, Contract.id == ContractPeriod.contract_id)
        .options(joinedload(ContractPeriod.contract))
        .filter(
            ContractPeriod.contract_id.in_(contract_ids),
            Contract.status != "cancelled",
        )
        .order_by(ContractPeriod.contract_id.desc(), ContractPeriod.period_year.desc())
        .all()
    )

    # period 기본 행 생성
    periods: dict[int, dict] = {}
    for p in all_periods:
        c = p.contract
        periods[p.id] = {
            "contract_period_id": p.id,
            "contract_id": c.id if c else None,
            "contract_name": c.contract_name if c else None,
            "contract_code": c.contract_code if c else None,
            "period_label": p.period_label or f"Y{str(p.period_year)[-2:]}",
            "is_completed": p.is_completed,
            "sales_id": None, "sales_cc_id": None, "sales_name": None, "sales_phone": None, "sales_email": None,
            "tax_id": None, "tax_cc_id": None, "tax_name": None, "tax_phone": None, "tax_email": None,
            "ops_id": None, "ops_cc_id": None, "ops_name": None, "ops_phone": None, "ops_email": None,
        }

    # 담당자 데이터 채우기
    period_ids = list(periods.keys())
    if period_ids:
        rows = (
            db.query(ContractContact)
            .options(joinedload(ContractContact.partner_contact))
            .filter(
                ContractContact.contract_period_id.in_(period_ids),
                ContractContact.partner_id == partner_id,
            )
            .all()
        )
        prefix_map = {"영업": "sales", "세금계산서": "tax", "업무": "ops"}
        for r in rows:
            d = periods.get(r.contract_period_id)
            if not d:
                continue
            prefix = prefix_map.get(r.contact_type)
            if not prefix:
                continue
            if r.rank == "정" and d[prefix + "_id"] is None:
                cc = r.partner_contact
                d[prefix + "_id"] = r.id
                d[prefix + "_cc_id"] = r.partner_contact_id
                d[prefix + "_name"] = cc.name if cc else None
                d[prefix + "_phone"] = cc.phone if cc else None
                d[prefix + "_email"] = cc.email if cc else None

    return list(periods.values())


def create_contract_contact_for_contract(db: Session, contract_id: int, data: ContractContactCreate) -> dict:
    """Contract의 최신 Period에 담당자 등록 (하위 호환)."""
    period = (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id == contract_id)
        .order_by(ContractPeriod.period_year.desc())
        .first()
    )
    if not period:
        raise NotFoundError("사업에 연결된 기간이 없습니다.")
    return create_contract_contact(db, period.id, data)


def create_contract_contact(db: Session, period_id: int, data: ContractContactCreate) -> dict:
    """Period별 담당자 등록."""
    period = db.query(ContractPeriod).options(
        joinedload(ContractPeriod.contract)
    ).filter(ContractPeriod.id == period_id).first()
    if not period:
        raise NotFoundError("사업 기간을 찾을 수 없습니다.")
    partner = db.get(Partner, data.partner_id)
    if not partner:
        raise NotFoundError("거래처를 찾을 수 없습니다.")
    # 참조할 기본 담당자 확인
    cc = db.get(PartnerContact, data.partner_contact_id)
    if not cc:
        raise NotFoundError("기본 담당자를 찾을 수 없습니다.")
    if cc.partner_id != data.partner_id:
        raise NotFoundError("해당 거래처의 담당자가 아닙니다.")

    obj = ContractContact(
        contract_period_id=period_id,
        partner_id=data.partner_id,
        partner_contact_id=data.partner_contact_id,
        contact_type=data.contact_type,
        rank=data.rank,
        notes=data.notes,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    d = _to_dict(obj)
    d["contract_name"] = period.contract.contract_name
    d["contract_code"] = period.contract.contract_code
    d["period_label"] = period.period_label
    d["partner_name"] = partner.name
    return d


def update_contract_contact(
    db: Session, contact_id: int, data: ContractContactUpdate, *, current_user: User | None = None,
) -> dict:
    """사업별 담당자 수정."""
    obj = db.query(ContractContact).options(
        joinedload(ContractContact.partner_contact)
    ).filter(ContractContact.id == contact_id).first()
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    if current_user:
        check_period_access(db, obj.contract_period_id, current_user)

    updates = data.model_dump(exclude_unset=True)
    # partner_contact_id 변경 시 같은 거래처인지 검증
    if "partner_contact_id" in updates and updates["partner_contact_id"] is not None:
        cc = db.get(PartnerContact, updates["partner_contact_id"])
        if not cc:
            raise NotFoundError("기본 담당자를 찾을 수 없습니다.")
        if cc.partner_id != obj.partner_id:
            raise NotFoundError("해당 거래처의 담당자가 아닙니다.")

    for field, value in updates.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    d = _to_dict(obj)
    contract = obj.contract_period.contract if obj.contract_period else None
    d["contract_name"] = contract.contract_name if contract else None
    d["contract_code"] = contract.contract_code if contract else None
    d["period_label"] = obj.contract_period.period_label if obj.contract_period else None
    d["partner_name"] = obj.partner.name if obj.partner else None
    return d


def delete_contract_contact(
    db: Session, contact_id: int, *, current_user: User | None = None,
) -> None:
    """사업별 담당자 삭제."""
    obj = db.get(ContractContact, contact_id)
    if not obj:
        raise NotFoundError("담당자를 찾을 수 없습니다.")
    if current_user:
        check_period_access(db, obj.contract_period_id, current_user)
    db.delete(obj)
    db.commit()


def _to_dict(obj: ContractContact) -> dict:
    cc = obj.partner_contact
    return {
        "id": obj.id,
        "contract_period_id": obj.contract_period_id,
        "partner_id": obj.partner_id,
        "partner_contact_id": obj.partner_contact_id,
        "contact_type": obj.contact_type,
        "rank": obj.rank,
        "contact_name": cc.name if cc else None,
        "contact_phone": cc.phone if cc else None,
        "contact_email": cc.email if cc else None,
        "notes": obj.notes,
    }
