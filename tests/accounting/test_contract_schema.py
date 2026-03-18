from app.modules.accounting.schemas.contract import ContractPeriodCreate, ContractPeriodUpdate, ContractUpdate


def test_contract_update_normalizes_inspection_date() -> None:
    payload = ContractUpdate(inspection_date="2026-1-5")

    assert payload.inspection_date == "2026-01-05"


def test_contract_period_create_normalizes_month_and_date_fields() -> None:
    payload = ContractPeriodCreate(
        period_year=2026,
        start_month="2601",
        end_month="2026-12",
        inspection_date="260115",
    )

    assert payload.start_month == "2026-01-01"
    assert payload.end_month == "2026-12-01"
    assert payload.inspection_date == "2026-01-15"


def test_contract_period_update_normalizes_partial_month_fields() -> None:
    payload = ContractPeriodUpdate(start_month="202601", end_month="2602")

    assert payload.start_month == "2026-01-01"
    assert payload.end_month == "2026-02-01"
