from app.modules.accounting.schemas.contract import ContractPeriodCreate, ContractPeriodUpdate, ContractUpdate


def test_contract_update_is_common_schema_without_accounting_only_fields() -> None:
    payload = ContractUpdate(contract_name="테스트 사업")

    assert payload.contract_name == "테스트 사업"
    assert not hasattr(payload, "inspection_date")


def test_contract_period_create_normalizes_month_fields() -> None:
    payload = ContractPeriodCreate(
        period_year=2026,
        start_month="2601",
        end_month="2026-12",
    )

    assert payload.start_month == "2026-01-01"
    assert payload.end_month == "2026-12-01"
    assert not hasattr(payload, "inspection_date")


def test_contract_period_update_normalizes_partial_month_fields() -> None:
    payload = ContractPeriodUpdate(start_month="202601", end_month="2602")

    assert payload.start_month == "2026-01-01"
    assert payload.end_month == "2026-02-01"
