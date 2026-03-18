from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_type_config import ContractTypeConfig
from app.modules.common.models.customer import Customer
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.models.transaction_line import STATUS_CONFIRMED, TransactionLine
from app.modules.common.models.user import User
from app.core.exceptions import BusinessRuleError
from app.modules.accounting.schemas.contract import ContractCreate, ContractPeriodCreate
from app.modules.accounting.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.modules.accounting.schemas.transaction_line import TransactionLineCreate, TransactionLineUpdate
from app.modules.accounting.services import contract as contract_service
from app.modules.accounting.services import receipt as receipt_service
from app.modules.accounting.services import receipt_match as receipt_match_service
from app.modules.accounting.services import transaction_line as tl_service


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


def test_create_contract_applies_defaults_and_created_by(db_session, user_role_id) -> None:
    _seed_contract_type(db_session)
    owner = User(name="홍길동", login_id="hong", role_id=user_role_id)
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


def test_create_period_inherits_contract_fields(db_session, user_role_id) -> None:
    _seed_contract_type(db_session)
    owner = User(name="영업", login_id="sales", role_id=user_role_id)
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


def test_completed_period_blocks_transaction_line_create_and_move(db_session, user_role_id) -> None:
    _seed_contract_type(db_session)
    owner = User(name="영업", login_id="sales2", role_id=user_role_id)
    customer = Customer(name="고객사")
    db_session.add_all([owner, customer])
    db_session.commit()

    contract = Contract(
        contract_name="완료기간 테스트",
        contract_type="MA",
        contract_code="MA-2026-0002",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()

    db_session.add_all([
        ContractPeriod(
            contract_id=contract.id,
            period_year=2026,
            period_label="Y26",
            stage="계약완료",
            start_month="2026-01-01",
            end_month="2026-12-01",
            is_completed=True,
        ),
        ContractPeriod(
            contract_id=contract.id,
            period_year=2027,
            period_label="Y27",
            stage="70%",
            start_month="2027-01-01",
            end_month="2027-12-01",
            is_completed=False,
        ),
    ])
    db_session.commit()

    try:
        tl_service.create_transaction_line(
            db_session,
            contract.id,
            TransactionLineCreate(
                revenue_month="2026-06-01",
                line_type="revenue",
                customer_id=customer.id,
                supply_amount=1000,
                status="확정",
            ),
            created_by=owner.id,
        )
        assert False, "완료된 기간의 실적 생성은 차단되어야 합니다."
    except BusinessRuleError:
        pass

    row = TransactionLine(
        contract_id=contract.id,
        revenue_month="2027-01-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=2000,
        status=STATUS_CONFIRMED,
        created_by=owner.id,
    )
    db_session.add(row)
    db_session.commit()

    try:
        tl_service.update_transaction_line(
            db_session,
            row.id,
            TransactionLineUpdate(revenue_month="2026-07-01"),
        )
        assert False, "완료된 기간으로의 실적 이동은 차단되어야 합니다."
    except BusinessRuleError:
        pass


def test_completed_period_blocks_receipt_create_update_delete(db_session, user_role_id) -> None:
    _seed_contract_type(db_session)
    owner = User(name="수금담당", login_id="receipt_owner", role_id=user_role_id)
    customer = Customer(name="매출처")
    db_session.add_all([owner, customer])
    db_session.commit()

    contract = Contract(
        contract_name="입금 완료기간 테스트",
        contract_type="MA",
        contract_code="MA-2026-0003",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()

    db_session.add_all([
        ContractPeriod(
            contract_id=contract.id,
            period_year=2026,
            period_label="Y26",
            stage="계약완료",
            start_month="2026-01-01",
            end_month="2026-12-01",
            is_completed=True,
        ),
        ContractPeriod(
            contract_id=contract.id,
            period_year=2027,
            period_label="Y27",
            stage="70%",
            start_month="2027-01-01",
            end_month="2027-12-01",
            is_completed=False,
        ),
    ])
    db_session.commit()

    try:
        receipt_service.create_receipt(
            db_session,
            contract.id,
            ReceiptCreate(
                customer_id=customer.id,
                receipt_date="2026-03-15",
                revenue_month="2026-03-01",
                amount=3000,
            ),
            created_by=owner.id,
        )
        assert False, "완료된 기간의 입금 생성은 차단되어야 합니다."
    except BusinessRuleError:
        pass

    receipt = Receipt(
        contract_id=contract.id,
        customer_id=customer.id,
        receipt_date="2027-02-15",
        revenue_month="2027-02-01",
        amount=5000,
        created_by=owner.id,
    )
    db_session.add(receipt)
    db_session.commit()

    try:
        receipt_service.update_receipt(
            db_session,
            receipt.id,
            ReceiptUpdate(revenue_month="2026-02-01"),
        )
        assert False, "완료된 기간으로의 입금 이동은 차단되어야 합니다."
    except BusinessRuleError:
        pass

    receipt.revenue_month = "2026-04-01"
    db_session.commit()

    try:
        receipt_service.delete_receipt(db_session, receipt.id)
        assert False, "완료된 기간의 입금 삭제는 차단되어야 합니다."
    except BusinessRuleError:
        pass


def test_auto_match_receipt_is_isolated_to_same_period_range(db_session, user_role_id) -> None:
    _seed_contract_type(db_session)
    owner = User(name="배분담당", login_id="matcher", role_id=user_role_id)
    customer = Customer(name="매출처")
    db_session.add_all([owner, customer])
    db_session.commit()

    contract = Contract(
        contract_name="FIFO 기간격리 테스트",
        contract_type="MA",
        contract_code="MA-2026-0004",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()

    db_session.add_all([
        ContractPeriod(
            contract_id=contract.id,
            period_year=2026,
            period_label="Y26-H1",
            stage="70%",
            start_month="2026-01-01",
            end_month="2026-06-01",
            is_completed=False,
        ),
        ContractPeriod(
            contract_id=contract.id,
            period_year=2027,
            period_label="Y26-H2",
            stage="70%",
            start_month="2027-01-01",
            end_month="2027-12-01",
            is_completed=False,
        ),
    ])
    db_session.flush()

    first_half_line = TransactionLine(
        contract_id=contract.id,
        revenue_month="2026-05-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=100,
        status=STATUS_CONFIRMED,
        created_by=owner.id,
    )
    second_half_line = TransactionLine(
        contract_id=contract.id,
        revenue_month="2027-08-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=100,
        status=STATUS_CONFIRMED,
        created_by=owner.id,
    )
    receipt = Receipt(
        contract_id=contract.id,
        customer_id=customer.id,
        receipt_date="2026-05-20",
        revenue_month="2026-05-01",
        amount=150,
        created_by=owner.id,
    )
    db_session.add_all([first_half_line, second_half_line, receipt])
    db_session.commit()

    created = receipt_match_service.auto_match_receipt(
        db_session,
        receipt.id,
        created_by=owner.id,
    )
    db_session.flush()

    assert len(created) == 1
    assert created[0].transaction_line_id == first_half_line.id
    assert created[0].matched_amount == 100
