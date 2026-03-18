from io import BytesIO

import pandas as pd

from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.contract_type_config import ContractTypeConfig
from app.modules.accounting.services import importer


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
    assert any(detail.get("code") == "missing_sheet1_reference" for detail in result["error_details"])


def test_parse_and_validate_rejects_duplicate_year_and_contract_name_in_upload(db_session) -> None:
    db_session.add(ContractTypeConfig(code="MA", label="MA", sort_order=1, is_active=True))
    db_session.commit()
    contracts = pd.DataFrame(
        [
            {
                "연도": "2025",
                "번호": "1",
                "사업유형": "MA",
                "거래처(END)": "고객사 A",
                "영업기회명": "중복 사업",
                "진행단계": "70%",
            },
            {
                "연도": "2025",
                "번호": "2",
                "사업유형": "MA",
                "거래처(END)": "고객사 B",
                "영업기회명": "중복 사업",
                "진행단계": "50%",
            },
        ]
    )

    result = importer.parse_and_validate(_workbook_bytes(contracts=contracts), db=db_session)

    assert any("같은 연도/사업명 조합" in error for error in result["errors"])
    assert any(detail.get("code") == "duplicate_contract_identity_in_upload" for detail in result["error_details"])


def test_parse_and_validate_rejects_ambiguous_existing_same_year_and_name(db_session) -> None:
    db_session.add(ContractTypeConfig(code="MA", label="MA", sort_order=1, is_active=True))
    contract1 = Contract(contract_name="기존 중복 사업", contract_type="MA", contract_code="MA-2025-0001", status="active")
    contract2 = Contract(contract_name="기존 중복 사업", contract_type="MA", contract_code="MA-2025-0002", status="active")
    db_session.add_all([contract1, contract2])
    db_session.flush()
    db_session.add_all(
        [
            ContractPeriod(
                contract_id=contract1.id,
                period_year=2025,
                period_label="Y25",
                stage="70%",
            ),
            ContractPeriod(
                contract_id=contract2.id,
                period_year=2025,
                period_label="Y25B",
                stage="50%",
            ),
        ]
    )
    db_session.commit()

    contracts = pd.DataFrame(
        [
            {
                "연도": "2025",
                "번호": "1",
                "사업유형": "MA",
                "거래처(END)": "고객사",
                "영업기회명": "기존 중복 사업",
                "진행단계": "70%",
            }
        ]
    )

    result = importer.parse_and_validate(_workbook_bytes(contracts=contracts), db=db_session)

    assert any("기존 데이터에 같은 연도/사업명 조합" in error for error in result["errors"])
    assert any(detail.get("code") == "ambiguous_existing_contract_identity" for detail in result["error_details"])
