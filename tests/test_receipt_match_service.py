import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.common.models.customer import Customer
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.models.transaction_line import STATUS_CONFIRMED, TransactionLine
from app.modules.common.models.user import User
from app.modules.accounting.schemas.receipt_match import ReceiptMatchCreate, ReceiptMatchUpdate
from app.modules.accounting.services import receipt_match as receipt_match_service


def _seed_contract_graph(db_session, user_role_id):
    owner_a = User(name="소유자A", login_id="owner_a", role_id=user_role_id)
    owner_b = User(name="소유자B", login_id="owner_b", role_id=user_role_id)
    customer = Customer(name="거래처")
    db_session.add_all([owner_a, owner_b, customer])
    db_session.flush()

    contract_a = Contract(
        contract_name="사업A",
        contract_type="MA",
        contract_code="MA-2026-0001",
        owner_user_id=owner_a.id,
        end_customer_id=customer.id,
        status="active",
    )
    contract_b = Contract(
        contract_name="사업B",
        contract_type="MA",
        contract_code="MA-2026-0002",
        owner_user_id=owner_b.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add_all([contract_a, contract_b])
    db_session.flush()

    db_session.add_all(
        [
            ContractPeriod(
                contract_id=contract_a.id,
                period_year=2026,
                period_label="Y26A",
                stage="70%",
                start_month="2026-01-01",
                end_month="2026-12-01",
            ),
            ContractPeriod(
                contract_id=contract_b.id,
                period_year=2026,
                period_label="Y26B",
                stage="70%",
                start_month="2026-01-01",
                end_month="2026-12-01",
            ),
        ]
    )
    db_session.flush()

    receipt = Receipt(
        contract_id=contract_a.id,
        customer_id=customer.id,
        receipt_date="2026-01-15",
        revenue_month="2026-01-01",
        amount=100,
        created_by=owner_a.id,
    )
    line = TransactionLine(
        contract_id=contract_a.id,
        revenue_month="2026-01-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=100,
        status=STATUS_CONFIRMED,
        created_by=owner_a.id,
    )
    foreign_line = TransactionLine(
        contract_id=contract_b.id,
        revenue_month="2026-01-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=100,
        status=STATUS_CONFIRMED,
        created_by=owner_b.id,
    )
    db_session.add_all([receipt, line, foreign_line])
    db_session.commit()

    return owner_a, owner_b, receipt, line, foreign_line


def test_create_match_rejects_contract_path_mismatch(db_session, user_role_id) -> None:
    owner_a, _owner_b, receipt, line, _foreign_line = _seed_contract_graph(db_session, user_role_id)

    with pytest.raises(BusinessRuleError):
        receipt_match_service.create_match(
            db_session,
            ReceiptMatchCreate(
                receipt_id=receipt.id,
                transaction_line_id=line.id,
                matched_amount=50,
            ),
            created_by=owner_a.id,
            current_user=owner_a,
            expected_contract_id=9999,
        )


def test_update_and_delete_match_check_contract_access(db_session, user_role_id) -> None:
    owner_a, owner_b, receipt, line, _foreign_line = _seed_contract_graph(db_session, user_role_id)
    created = receipt_match_service.create_match(
        db_session,
        ReceiptMatchCreate(
            receipt_id=receipt.id,
            transaction_line_id=line.id,
            matched_amount=50,
        ),
        created_by=owner_a.id,
        current_user=owner_a,
        expected_contract_id=receipt.contract_id,
    )
    match_id = created["id"]

    with pytest.raises(NotFoundError):
        receipt_match_service.update_match(
            db_session,
            match_id,
            ReceiptMatchUpdate(matched_amount=40),
            current_user=owner_b,
        )

    with pytest.raises(NotFoundError):
        receipt_match_service.delete_match(
            db_session,
            match_id,
            current_user=owner_b,
        )
