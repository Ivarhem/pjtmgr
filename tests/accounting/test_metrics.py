from app.modules.accounting.services.metrics import build_filter, month_range, safe_pct, years_in_range


def test_build_filter_normalizes_month_bounds() -> None:
    filt = build_filter("2025-01", "2025-03", owner_id=[1], contract_type=["MA"])

    assert filt.date_from == "2025-01-01"
    assert filt.date_to == "2025-03-01"
    assert filt.owner_id == [1]
    assert filt.contract_type == ["MA"]


def test_month_range_spans_year_boundary() -> None:
    assert month_range("2025-11-01", "2026-02-01") == [
        "2025-11-01",
        "2025-12-01",
        "2026-01-01",
        "2026-02-01",
    ]


def test_years_in_range_includes_all_years() -> None:
    assert years_in_range("2024-12-01", "2026-01-01") == [2024, 2025, 2026]


def test_safe_pct_handles_zero_denominator() -> None:
    assert safe_pct(25, 200) == 12.5
    assert safe_pct(10, 0) is None
