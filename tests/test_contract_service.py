from app.models.contract import Contract
from app.models.contract_type_config import ContractTypeConfig
from app.models.customer import Customer
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractPeriodCreate
from app.services import contract as contract_service


def _seed_contract_type(db_session) -> None:
    db_session.add(
        ContractTypeConfig(
            code="MA",
            label="MA",
            sort_order=1,
            is_active=True,
            default_inspection_day=5,
            default_invoice_month_offset=1,
            default_invoice_day_type="말일",
        )
    )
    db_session.commit()


def test_create_contract_applies_defaults_and_created_by(db_session) -> None:
    _seed_contract_type(db_session)
    owner = User(name="홍길동", login_id="hong", role="user")
    customer = Customer(name="고객사")
    db_session.add_all([owner, customer])
    db_session.commit()

    result = contract_service.create_contract(
        db_session,
        ContractCreate(
            contract_name="테스트 사업",
            contract_type="MA",
            end_customer_id=customer.id,
        ),
        created_by=owner.id,
    )

    saved = db_session.get(Contract, result["id"])
    assert saved is not None
    assert saved.owner_user_id == owner.id
    assert saved.inspection_day == 5
    assert saved.invoice_month_offset == 1
    assert saved.invoice_day_type == "말일"
    assert saved.contract_code.startswith("MA-")


def test_create_period_inherits_contract_fields(db_session) -> None:
    _seed_contract_type(db_session)
    owner = User(name="영업", login_id="sales", role="user")
    end_customer = Customer(name="엔드고객")
    billing_customer = Customer(name="매출처")
    db_session.add_all([owner, end_customer, billing_customer])
    db_session.commit()

    contract = Contract(
        contract_name="상속 테스트",
        contract_type="MA",
        contract_code="MA-2026-0001",
        owner_user_id=owner.id,
        end_customer_id=end_customer.id,
        inspection_day=10,
        invoice_month_offset=1,
        invoice_day_type="특정일",
        invoice_day=25,
    )
    db_session.add(contract)
    db_session.commit()

    period = contract_service.create_period(
        db_session,
        contract.id,
        ContractPeriodCreate(
            period_year=2026,
            stage="70%",
            customer_id=billing_customer.id,
        ),
    )

    assert period["owner_user_id"] == owner.id
    assert period["customer_id"] == billing_customer.id
    assert period["inspection_day"] == 10
    assert period["invoice_month_offset"] == 1
    assert period["invoice_day_type"] == "특정일"
    assert period["invoice_day"] == 25
