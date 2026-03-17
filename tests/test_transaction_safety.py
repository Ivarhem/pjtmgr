import pytest

from app.exceptions import BusinessRuleError
from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.contract_type_config import ContractTypeConfig
from app.models.customer import Customer
from app.models.receipt import Receipt
from app.models.receipt_match import ReceiptMatch
from app.models.setting import Setting
from app.models.transaction_line import TransactionLine
from app.models.user import User
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.schemas.setting import SettingUpdate
from app.services import receipt as receipt_service
from app.services import receipt_match as match_service
from app.services import setting as setting_service
from app.services import transaction_line as tl_service


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


def _seed_receipt_and_line(
    db_session, contract: Contract, customer: Customer, owner: User,
) -> tuple[Receipt, TransactionLine]:
    """확정 매출 라인과 입금을 생성하고 반환."""
    line = TransactionLine(
        contract_id=contract.id,
        revenue_month="2026-01-01",
        line_type="revenue",
        customer_id=customer.id,
        supply_amount=1000,
        status="확정",
        created_by=owner.id,
    )
    receipt = Receipt(
        contract_id=contract.id,
        customer_id=customer.id,
        receipt_date="2026-01-15",
        revenue_month="2026-01-01",
        amount=500,
        created_by=owner.id,
    )
    db_session.add_all([line, receipt])
    db_session.flush()
    # 수동 매칭 생성
    match = ReceiptMatch(
        receipt_id=receipt.id,
        transaction_line_id=line.id,
        matched_amount=500,
        match_type="manual",
        created_by=owner.id,
    )
    db_session.add(match)
    db_session.commit()
    return receipt, line


# ── 테스트 1: create_receipt 롤백 ────────────────────────────────


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


# ── 테스트 2: update_receipt 롤백 ────────────────────────────────


def test_update_receipt_rolls_back_when_auto_match_fails(db_session, monkeypatch) -> None:
    """update_receipt에서 auto_match 실패 시 금액 변경이 롤백되는지 확인."""
    owner, customer, contract = _seed_contract_for_receipt(db_session)

    # 직접 입금 생성 (auto_match 없이)
    receipt = Receipt(
        contract_id=contract.id,
        customer_id=customer.id,
        receipt_date="2026-01-15",
        revenue_month="2026-01-01",
        amount=100,
        created_by=owner.id,
    )
    db_session.add(receipt)
    db_session.commit()
    original_amount = receipt.amount

    def _boom(*_args, **_kwargs):
        raise BusinessRuleError("자동 배분 실패")

    monkeypatch.setattr("app.services.receipt_match.auto_match_receipt", _boom)

    with pytest.raises(BusinessRuleError):
        receipt_service.update_receipt(
            db_session,
            receipt.id,
            ReceiptUpdate(amount=999),
        )

    db_session.refresh(receipt)
    assert receipt.amount == original_amount


# ── 테스트 3: delete_receipt 시 매칭 cascade ─────────────────────


def test_delete_receipt_cascades_matches(db_session) -> None:
    """입금 삭제 시 연결된 ReceiptMatch도 CASCADE로 삭제되는지 확인."""
    owner, customer, contract = _seed_contract_for_receipt(db_session)
    receipt, line = _seed_receipt_and_line(db_session, contract, customer, owner)
    receipt_id = receipt.id

    assert db_session.query(ReceiptMatch).filter(ReceiptMatch.receipt_id == receipt_id).count() == 1

    receipt_service.delete_receipt(db_session, receipt_id)

    assert db_session.query(Receipt).filter(Receipt.id == receipt_id).count() == 0
    assert db_session.query(ReceiptMatch).filter(ReceiptMatch.receipt_id == receipt_id).count() == 0


# ── 테스트 4: auto_match_contract 롤백 ──────────────────────────


def test_auto_match_contract_rolls_back_on_failure(db_session, monkeypatch) -> None:
    """auto_match_contract 중 예외 시 전체 롤백 확인."""
    owner, customer, contract = _seed_contract_for_receipt(db_session)

    # 입금 2건 생성
    for i in range(2):
        db_session.add(Receipt(
            contract_id=contract.id,
            customer_id=customer.id,
            receipt_date=f"2026-01-{15 + i:02d}",
            revenue_month="2026-01-01",
            amount=100,
            created_by=owner.id,
        ))
    db_session.commit()

    call_count = 0
    original_fn = match_service._get_unmatched_sales

    def _fail_on_second_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise BusinessRuleError("대사 중 오류")
        return original_fn(*args, **kwargs)

    monkeypatch.setattr("app.services.receipt_match._get_unmatched_sales", _fail_on_second_call)

    with pytest.raises(BusinessRuleError):
        match_service.auto_match_contract(db_session, contract.id)

    # 롤백되어 auto 매칭이 없어야 함
    auto_count = (
        db_session.query(ReceiptMatch)
        .filter(ReceiptMatch.match_type == "auto")
        .count()
    )
    assert auto_count == 0


# ── 테스트 5: 매칭 존재하는 실적 삭제 차단 ──────────────────────


def test_delete_transaction_line_blocked_by_existing_match(db_session) -> None:
    """입금 매칭이 존재하는 TransactionLine 삭제 시 BusinessRuleError."""
    owner, customer, contract = _seed_contract_for_receipt(db_session)
    _receipt, line = _seed_receipt_and_line(db_session, contract, customer, owner)

    with pytest.raises(BusinessRuleError, match="매칭"):
        tl_service.delete_transaction_line(db_session, line.id)

    # 삭제되지 않았는지 확인
    assert db_session.query(TransactionLine).filter(TransactionLine.id == line.id).count() == 1


def test_update_settings_rolls_back_batch_on_failure(db_session, monkeypatch) -> None:
    db_session.add_all(
        [
            Setting(key="org_name", value="기존 조직"),
            Setting(key="auth.password_min_length", value="10"),
        ]
    )
    db_session.commit()

    original_set_setting_value = setting_service._set_setting_value
    call_count = 0

    def _fail_on_second_set(db, key, value):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise RuntimeError("두 번째 설정 저장 실패")
        return original_set_setting_value(db, key, value)

    monkeypatch.setattr(setting_service, "_set_setting_value", _fail_on_second_set)

    with pytest.raises(RuntimeError):
        setting_service.update_settings(
            db_session,
            SettingUpdate(org_name="새 조직", password_min_length=12),
        )

    db_session.rollback()
    db_session.expire_all()
    assert db_session.get(Setting, "org_name").value == "기존 조직"
    assert db_session.get(Setting, "auth.password_min_length").value == "10"
