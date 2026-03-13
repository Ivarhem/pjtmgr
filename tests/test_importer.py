from io import BytesIO

import pandas as pd

from app.models.contract_type_config import ContractTypeConfig
from app.services import importer


def _workbook_bytes(*, contracts: pd.DataFrame, forecasts: pd.DataFrame | None = None, actuals: pd.DataFrame | None = None) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        contracts.to_excel(writer, sheet_name="영업기회", index=False)
        if forecasts is not None:
            forecasts.to_excel(writer, sheet_name="월별계획", index=False)
        if actuals is not None:
            actuals.to_excel(writer, sheet_name="실적", index=False)
    return buffer.getvalue()


def test_parse_and_validate_accepts_normalized_stage_and_type(db_session) -> None:
    db_session.add(ContractTypeConfig(code="ETC", label="ETC", sort_order=1, is_active=True))
    db_session.commit()
    contracts = pd.DataFrame(
        [
            {
                "연도": "2025",
                "번호": "1",
                "사업유형": "etc",
                "거래처(END)": "테스트 고객",
                "영업기회명": "유효한 사업",
                "진행단계": "0.7",
            }
        ]
    )
    result = importer.parse_and_validate(_workbook_bytes(contracts=contracts), db=db_session)

    assert result["errors"] == []
    assert result["counts"]["contracts"] == 1


def test_parse_and_validate_rejects_invalid_actual_reference(db_session) -> None:
    db_session.add(ContractTypeConfig(code="MA", label="MA", sort_order=1, is_active=True))
    db_session.commit()
    contracts = pd.DataFrame(
        [
            {
                "연도": "2025",
                "번호": "1",
                "사업유형": "MA",
                "거래처(END)": "테스트 고객",
                "영업기회명": "기준 사업",
                "진행단계": "70%",
            }
        ]
    )
    actuals = pd.DataFrame(
        [
            {
                "연도": "2025",
                "번호": "99",
                "매출/매입": "매출",
                "거래처명": "없는 참조",
            }
        ]
    )
    result = importer.parse_and_validate(
        _workbook_bytes(contracts=contracts, actuals=actuals),
        db=db_session,
    )

    assert any("Sheet3" in error and "Sheet1에 없음" in error for error in result["errors"])
