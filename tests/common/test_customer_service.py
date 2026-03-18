from app.modules.common.models.customer import Customer
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.common.services import customer as customer_service


def test_delete_contact_removes_customer_contact(db_session) -> None:
    customer = Customer(name="거래처")
    db_session.add(customer)
    db_session.flush()

    contact = CustomerContact(customer_id=customer.id, name="담당자")
    db_session.add(contact)
    db_session.commit()

    customer_service.delete_contact(db_session, contact.id)

    assert db_session.get(CustomerContact, contact.id) is None
