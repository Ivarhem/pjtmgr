from app.modules.common.models.partner import Partner
from app.modules.common.models.contract import Contract
from app.modules.common.models.user import User
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.common.services import partner as partner_service


def test_delete_contact_removes_partner_contact(db_session) -> None:
    partner = Partner(partner_code="P001", name="거래처")
    db_session.add(partner)
    db_session.flush()

    contact = PartnerContact(partner_id=partner.id, name="담당자")
    db_session.add(contact)
    db_session.commit()

    partner_service.delete_contact(db_session, contact.id)

    assert db_session.get(PartnerContact, contact.id) is None


def test_list_partners_includes_unlinked_partner_for_regular_user(db_session, user_role_id) -> None:
    user = User(login_id="sales-user", name="영업담당", role_id=user_role_id)
    partner = Partner(partner_code="P777", name="지옥불반도")
    db_session.add_all([user, partner])
    db_session.commit()

    rows = partner_service.list_partners(db_session, current_user=user)

    assert [row["name"] for row in rows] == ["지옥불반도"]


def test_list_partners_my_only_still_filters_to_owned_contracts(db_session, user_role_id) -> None:
    owner = User(login_id="owner-user", name="담당자", role_id=user_role_id)
    other = User(login_id="other-user", name="다른담당자", role_id=user_role_id)
    owned_partner = Partner(partner_code="P101", name="내거래처")
    unowned_partner = Partner(partner_code="P102", name="남의거래처")
    db_session.add_all([owner, other, owned_partner, unowned_partner])
    db_session.flush()

    owned_contract = Contract(
        contract_code="B001",
        contract_name="내 사업",
        contract_type="인프라",
        owner_user_id=owner.id,
        end_partner_id=owned_partner.id,
    )
    other_contract = Contract(
        contract_code="B002",
        contract_name="남의 사업",
        contract_type="인프라",
        owner_user_id=other.id,
        end_partner_id=unowned_partner.id,
    )
    db_session.add_all([owned_contract, other_contract])
    db_session.commit()

    rows = partner_service.list_partners(db_session, current_user=owner, my_only=True)

    assert [row["name"] for row in rows] == ["내거래처"]
