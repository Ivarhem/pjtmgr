from app.modules.common.models.partner import Partner
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
