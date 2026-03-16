import pytest

from app.exceptions import BusinessRuleError
from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.contract_type_config import ContractTypeConfig
from app.models.customer import Customer
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.receipt import ReceiptCreate
from app.services import receipt as receipt_service


def _seed_contract_for_receipt(db_session) -> tuple[User, Customer, Contract]:
    owner = User(name="영업", login_id="sales-safe", role="user")
    customer = Customer(name="거래처")
    db_session.add_all(
        [
            owner,
            customer,
            ContractTypeConfig(code="MA", label="MA", sort_order=1, is_active=True),
        ]
    )
    db_session.flush()

    contract = Contract(
        contract_name="트랜잭션 테스트",
        contract_type="MA",
        contract_code="MA-2026-0001",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()
    db_session.add(
        ContractPeriod(
            contract_id=contract.id,
            period_year=2026,
            period_label="Y26",
            stage="70%",
            start_month="2026-01-01",
            end_month="2026-12-01",
            is_completed=False,
        )
    )
    db_session.commit()
    return owner, customer, contract


def test_create_receipt_rolls_back_when_auto_match_fails(db_session, monkeypatch) -> None:
    owner, customer, contract = _seed_contract_for_receipt(db_session)

    def _boom(*_args, **_kwargs):
        raise BusinessRuleError("자동 배분 실패")

    monkeypatch.setattr("app.services.receipt_match.auto_match_receipt", _boom)

    with pytest.raises(BusinessRuleError):
        receipt_service.create_receipt(
            db_session,
            contract.id,
            ReceiptCreate(
                customer_id=customer.id,
                receipt_date="2026-01-15",
                revenue_month="2026-01-01",
                amount=100,
            ),
            created_by=owner.id,
        )

    assert db_session.query(Receipt).filter(Receipt.contract_id == contract.id).count() == 0
