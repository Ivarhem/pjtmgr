"""Excel Import 서비스 (3시트 템플릿 파싱 및 DB 저장)"""
from __future__ import annotations

import os
from collections import defaultdict
from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd
from sqlalchemy.orm import Session
from app.modules.common.models.user import User
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.monthly_forecast import MonthlyForecast
from app.modules.accounting.models.transaction_line import TransactionLine
from app.modules.common.services.user import get_default_role_id
from app.modules.common.services.customer import get_or_create_by_name as _get_or_create_customer_svc
from app.core.code_generator import next_contract_code, next_period_code, RESERVED_CUSTOMER_CODE
from app.core.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from app.modules.common.models.customer import Customer
from app.modules.accounting.schemas.contract import VALID_STAGES
from app.modules.accounting.services.contract_type_config import get_valid_codes as _get_valid_contract_types

# ── 파일 유효성 검증 ──

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_ALLOWED_CSV_EXTENSIONS = {".csv"}
_ALLOWED_CSV_MIMES = {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}


def validate_xlsx(filename: str | None, content_type: str | None) -> None:
    """Excel 파일 확장자 및 MIME 타입 검증."""
    if not filename or not filename.lower().endswith(".xlsx"):
        raise BusinessRuleError("xlsx 파일만 업로드할 수 있습니다.", status_code=422)
    if not content_type or content_type != _XLSX_MIME:
        raise BusinessRuleError("xlsx 파일만 업로드할 수 있습니다.", status_code=422)


def validate_csv(filename: str | None, content_type: str | None) -> None:
    """CSV 파일 확장자 및 MIME 타입 검증."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ALLOWED_CSV_EXTENSIONS:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)
    if content_type and content_type not in _ALLOWED_CSV_MIMES:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)

VALID_LINE_TYPES = {"매출", "매입"}
LINE_TYPE_MAP = {"매출": "revenue", "매입": "cost"}

# 진행단계 소수 → 퍼센트 정규화
_STAGE_NORM: dict[str, str] = {"0.1": "10%", "0.5": "50%", "0.7": "70%", "0.9": "90%"}
# 사업유형 정규화 (대소문자, 별칭)
_TYPE_NORM: dict[str, str] = {"etc": "ETC", "prod": "Prod", "ts": "TS"}


def _norm_stage(val: str) -> str:
    v = val.strip()
    return _STAGE_NORM.get(v, v)


def _norm_contract_type(val: str) -> str:
    v = val.strip()
    return _TYPE_NORM.get(v.lower(), v)


def _get_or_create_user(db: Session, name: str) -> User | None:
    if not name or str(name).strip() == "":
        return None
    name = str(name).strip()
    user = db.query(User).filter(User.name == name).first()
    if not user:
        user = User(name=name, login_id=name.lower().replace(" ", "_"), role_id=get_default_role_id(db))
        db.add(user)
        db.flush()
    return user


def _get_or_create_customer(
    db: Session,
    name: str,
    tax_contact_name: str | None = None,
    tax_contact_phone: str | None = None,
    tax_contact_email: str | None = None,
) -> "Customer":
    """pandas NaN 처리 후 customer 서비스 호출."""
    def _clean(val: object) -> str | None:
        return str(val).strip() if pd.notna(val) and val else None

    return _get_or_create_customer_svc(
        db,
        str(name).strip(),
        tax_contact_name=_clean(tax_contact_name),
        tax_contact_phone=_clean(tax_contact_phone),
        tax_contact_email=_clean(tax_contact_email),
    )


def _to_int(val) -> int:
    try:
        if pd.isna(val):
            return 0
    except (TypeError, ValueError):
        pass
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _import_key(row: pd.Series) -> tuple[str, str]:
    return (str(row["연도"]).strip(), str(row["번호"]).strip())


def _contract_identity(row: pd.Series) -> tuple[str, str]:
    return (str(row["연도"]).strip(), str(row["영업기회명"]).strip())


def _find_existing_periods(
    db: Session, identities: set[tuple[int, str]]
) -> dict[tuple[int, str], list[ContractPeriod]]:
    if not identities:
        return {}

    years = sorted({year for year, _name in identities})
    names = sorted({name for _year, name in identities})
    rows = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .filter(ContractPeriod.period_year.in_(years), Contract.contract_name.in_(names))
        .all()
    )

    grouped: dict[tuple[int, str], list[ContractPeriod]] = defaultdict(list)
    for period in rows:
        key = (period.period_year, period.contract.contract_name)
        if key in identities:
            grouped[key].append(period)
    return grouped


def _append_error(
    errors: list[str],
    error_details: list[dict],
    message: str,
    *,
    sheet: str | None = None,
    row: int | None = None,
    column: str | None = None,
    code: str | None = None,
) -> None:
    errors.append(message)
    detail = {"message": message}
    if sheet is not None:
        detail["sheet"] = sheet
    if row is not None:
        detail["row"] = row
    if column is not None:
        detail["column"] = column
    if code is not None:
        detail["code"] = code
    error_details.append(detail)


def _validate_contract_identity_map(
    df1: pd.DataFrame,
    *,
    existing_periods: dict[tuple[int, str], list[ContractPeriod]] | None = None,
) -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    error_details: list[dict] = []
    upload_identity_rows: dict[tuple[str, str], list[int]] = defaultdict(list)

    for i, row in df1.iterrows():
        upload_identity_rows[_contract_identity(row)].append(i + 2)

    for (year, contract_name), rows in upload_identity_rows.items():
        if len(rows) > 1:
            _append_error(
                errors,
                error_details,
                f"Sheet1 {rows[0]}행 외: 같은 연도/사업명 조합({year}, {contract_name})이 중복되어 전체 Import 대상을 구분할 수 없습니다.",
                sheet="Sheet1",
                row=rows[0],
                column="연도/영업기회명",
                code="duplicate_contract_identity_in_upload",
            )

    for (year, contract_name), periods in (existing_periods or {}).items():
        if len(periods) > 1:
            _append_error(
                errors,
                error_details,
                f"기존 데이터에 같은 연도/사업명 조합({year}, {contract_name})이 {len(periods)}건 있어 전체 Import 대상을 구분할 수 없습니다.",
                sheet="Sheet1",
                column="연도/영업기회명",
                code="ambiguous_existing_contract_identity",
            )

    return errors, error_details


def parse_and_validate(file_bytes: bytes, db: Session | None = None) -> dict:
    """파싱 + 유효성 검사. errors 리스트 반환."""
    xl = pd.ExcelFile(BytesIO(file_bytes))
    errors: list[str] = []
    error_details: list[dict] = []

    # Sheet1: 영업기회
    if "영업기회" not in xl.sheet_names:
        return {
            "errors": ["Sheet1 이름이 '영업기회'여야 합니다."],
            "error_details": [{"sheet": "Sheet1", "message": "Sheet1 이름이 '영업기회'여야 합니다.", "code": "invalid_sheet_name"}],
            "data": None,
        }
    df1 = xl.parse("영업기회", dtype=str).fillna("")
    # 안내 행(연도가 4자리 숫자가 아닌 행) 제거
    df1 = df1[df1["연도"].str.strip().str.match(r"^\d{4}$")].reset_index(drop=True)

    # "구분" → "사업유형" 하위 호환
    if "구분" in df1.columns and "사업유형" not in df1.columns:
        df1.rename(columns={"구분": "사업유형"}, inplace=True)

    required1 = ["연도", "번호", "사업유형", "거래처(END)", "영업기회명", "진행단계"]
    missing = [c for c in required1 if c not in df1.columns]
    if missing:
        return {
            "errors": [f"Sheet1 필수 컬럼 누락: {missing}"],
            "error_details": [{
                "sheet": "Sheet1",
                "column": ",".join(missing),
                "message": f"Sheet1 필수 컬럼 누락: {missing}",
                "code": "missing_required_columns",
            }],
            "data": None,
        }

    # 사업유형·진행단계 정규화 적용
    df1["사업유형"] = df1["사업유형"].apply(lambda v: _norm_contract_type(str(v)))
    df1["진행단계"] = df1["진행단계"].apply(lambda v: _norm_stage(str(v)))

    valid_contract_types = _get_valid_contract_types(db) if db else set()

    for i, row in df1.iterrows():
        r = i + 2
        if not row["연도"].strip():
            _append_error(errors, error_details, f"Sheet1 {r}행: 연도 필수", sheet="Sheet1", row=r, column="연도", code="required_year")
        if not row["번호"].strip():
            _append_error(errors, error_details, f"Sheet1 {r}행: 번호 필수", sheet="Sheet1", row=r, column="번호", code="required_number")
        if valid_contract_types and row["사업유형"].strip() not in valid_contract_types:
            _append_error(
                errors,
                error_details,
                f"Sheet1 {r}행: 사업유형 허용값({valid_contract_types}) 오류 - '{row['사업유형']}'",
                sheet="Sheet1",
                row=r,
                column="사업유형",
                code="invalid_contract_type",
            )
        if row["진행단계"].strip() not in VALID_STAGES:
            _append_error(
                errors,
                error_details,
                f"Sheet1 {r}행: 진행단계 허용값({VALID_STAGES}) 오류 - '{row['진행단계']}'",
                sheet="Sheet1",
                row=r,
                column="진행단계",
                code="invalid_stage",
            )

    if db is not None:
        identities = {(int(year), name) for year, name in {_contract_identity(row) for _, row in df1.iterrows()}}
        identity_errors, identity_details = _validate_contract_identity_map(
            df1,
            existing_periods=_find_existing_periods(db, identities),
        )
        errors.extend(identity_errors)
        error_details.extend(identity_details)

    # Sheet2: 월별계획 (선택)
    if "월별계획" in xl.sheet_names:
        df2 = xl.parse("월별계획", dtype=str).fillna("")
        if "연도" not in df2.columns:
            _append_error(
                errors,
                error_details,
                "Sheet2 필수 컬럼 누락: ['연도']",
                sheet="Sheet2",
                column="연도",
                code="missing_required_columns",
            )
            df2 = None
        else:
            df2 = df2[df2["연도"].apply(lambda v: str(v).strip().isdigit() and len(str(v).strip()) == 4)].reset_index(drop=True)
    else:
        df2 = None

    # Sheet3: 실적 (선택)
    df3 = None
    if "실적" in xl.sheet_names:
        df3 = xl.parse("실적", dtype=str).fillna("")
        required3 = ["연도", "번호", "매출/매입", "거래처명"]
        missing3 = [c for c in required3 if c not in df3.columns]
        if missing3:
            _append_error(
                errors,
                error_details,
                f"Sheet3 필수 컬럼 누락: {missing3}",
                sheet="Sheet3",
                column=",".join(missing3),
                code="missing_required_columns",
            )
            df3 = None
        else:
            df3 = df3[df3["연도"].apply(lambda v: str(v).strip().isdigit() and len(str(v).strip()) == 4)].reset_index(drop=True)
            opp_keys = set(zip(df1["연도"].str.strip(), df1["번호"].str.strip()))
            for i, row in df3.iterrows():
                r = i + 2
                key = (row["연도"].strip(), row["번호"].strip())
                if key not in opp_keys:
                    _append_error(
                        errors,
                        error_details,
                        f"Sheet3 {r}행: 연도+번호({key})가 Sheet1에 없음",
                        sheet="Sheet3",
                        row=r,
                        column="연도/번호",
                        code="missing_sheet1_reference",
                    )
                if row["매출/매입"].strip() not in VALID_LINE_TYPES:
                    _append_error(
                        errors,
                        error_details,
                        f"Sheet3 {r}행: 매출/매입 허용값 오류 - '{row['매출/매입']}'",
                        sheet="Sheet3",
                        row=r,
                        column="매출/매입",
                        code="invalid_line_type",
                    )

    return {
        "errors": errors,
        "error_details": error_details,
        "data": {"df1": df1, "df2": df2, "df3": df3} if not errors else None,
        "counts": {
            "contracts": len(df1),
            "forecasts": len(df2) if df2 is not None else 0,
            "actuals": len(df3) if df3 is not None else 0,
        },
    }


def import_data(db: Session, file_bytes: bytes, on_duplicate: str = "overwrite") -> dict:
    """실제 DB 저장. on_duplicate: 'overwrite' | 'skip'"""
    result = parse_and_validate(file_bytes, db=db)
    if result["errors"]:
        return result

    try:
        return _import_data_inner(db, result["data"], on_duplicate)
    except Exception:
        db.rollback()
        raise


def _import_data_inner(
    db: Session, data: dict, on_duplicate: str,
) -> dict:
    df1, df2, df3 = data["df1"], data["df2"], data["df3"]
    created = skipped = 0
    new_users: list[str] = []

    # (연도, 번호) → ContractPeriod 매핑 (Sheet2/Sheet3 연결용)
    period_map: dict[tuple, ContractPeriod] = {}
    existing_periods = _find_existing_periods(
        db,
        {(int(year), name) for year, name in {_contract_identity(row) for _, row in df1.iterrows()}},
    )

    for _, row in df1.iterrows():
        year = int(row["연도"].strip())
        contract_name = row["영업기회명"].strip()
        contract_type = row["사업유형"].strip()
        identity = (year, contract_name)

        matches = existing_periods.get(identity, [])
        existing_period = matches[0] if matches else None

        if existing_period and on_duplicate == "skip":
            skipped += 1
            period_map[_import_key(row)] = existing_period
            continue

        owner_name = row.get("담당", "").strip()
        owner = None
        if owner_name:
            is_new = db.query(User).filter(User.name == owner_name).first() is None
            owner = _get_or_create_user(db, owner_name)
            if is_new:
                new_users.append(owner_name)

        end_customer = _get_or_create_customer(db, row["거래처(END)"].strip())

        if existing_period:
            # 덮어쓰기: period + contract 업데이트
            contract = existing_period.contract
            contract.contract_name = contract_name
            contract.contract_type = contract_type
            contract.end_customer_id = end_customer.id
            if owner:
                contract.owner_user_id = owner.id
            existing_period.stage = row["진행단계"].strip()
            existing_period.expected_revenue_total = _to_int(row.get("예상매출(원)", ""))
            existing_period.expected_gp_total = _to_int(row.get("예상GP(원)", ""))
            period_map[_import_key(row)] = existing_period
        else:
            cust_code = end_customer.customer_code if end_customer else RESERVED_CUSTOMER_CODE
            contract = Contract(
                contract_code=next_contract_code(db, cust_code),
                contract_name=contract_name,
                contract_type=contract_type,
                end_customer_id=end_customer.id,
                owner_user_id=owner.id if owner else None,
                status="active",
            )
            db.add(contract)
            db.flush()

            year_suffix = str(year)[-2:]
            period = ContractPeriod(
                contract_id=contract.id,
                period_year=year,
                period_label=f"Y{year_suffix}",
                period_code=next_period_code(db, contract.contract_code, year),
                stage=row["진행단계"].strip(),
                expected_revenue_total=_to_int(row.get("예상매출(원)", "")),
                expected_gp_total=_to_int(row.get("예상GP(원)", "")),
            )
            db.add(period)
            db.flush()
            period_map[_import_key(row)] = period
            existing_periods.setdefault(identity, []).append(period)
            created += 1

    # Sheet2: 월별계획 → MonthlyForecast
    if df2 is not None:
        for _, row in df2.iterrows():
            key = _import_key(row)
            period = period_map.get(key)
            if not period:
                continue
            year_val = int(row["연도"].strip())
            for m in range(1, 13):
                sales = _to_int(row.get(f"{m}월매출", 0))
                gp = _to_int(row.get(f"{m}월GP", 0))
                if sales == 0 and gp == 0:
                    continue
                ym = f"{year_val}-{m:02d}-01"
                fc = db.query(MonthlyForecast).filter_by(
                    contract_period_id=period.id, forecast_month=ym, is_current=True
                ).first()
                if fc:
                    fc.revenue_amount = sales
                    fc.gp_amount = gp
                else:
                    db.add(MonthlyForecast(
                        contract_period_id=period.id,
                        forecast_month=ym,
                        revenue_amount=sales,
                        gp_amount=gp,
                    ))

    # Sheet3: 실적 → TransactionLine (월 컬럼을 개별 행으로 변환)
    if df3 is not None:
        for _, row in df3.iterrows():
            key = _import_key(row)
            period = period_map.get(key)
            if not period:
                continue
            contract_id = period.contract_id
            year_val = int(row["연도"].strip())
            line_type = LINE_TYPE_MAP.get(row["매출/매입"].strip(), "revenue")

            customer = _get_or_create_customer(
                db,
                name=row["거래처명"],
                tax_contact_name=row.get("세금계산서담당자"),
                tax_contact_phone=row.get("연락처"),
                tax_contact_email=row.get("이메일"),
            )

            for m in range(1, 13):
                col = f"{m}월"
                amount = _to_int(row.get(col, 0))
                if amount == 0:
                    continue
                revenue_month = f"{year_val}-{m:02d}-01"
                db.add(TransactionLine(
                    contract_id=contract_id,
                    revenue_month=revenue_month,
                    line_type=line_type,
                    customer_id=customer.id,
                    supply_amount=amount,
                ))

    db.commit()
    return {
        "errors": [],
        "error_details": [],
        "created": created,
        "skipped": skipped,
        "new_users": new_users,
    }


# ── 시트별 독립 Import ──────────────────────────────────────────────

def _is_year(val: str) -> bool:
    v = val.strip()
    return v.isdigit() and len(v) == 4


def import_forecast_sheet(db: Session, file_bytes: bytes) -> dict:
    """Sheet2(월별계획) 단독 Import.
    컬럼: 기간ID | 연도 | 사업명(참고) | 1월매출 | 1월GP | ... | 12월GP
    '기간ID'는 ContractPeriod.id 기준으로 대상 period를 찾는다.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    if "월별계획" not in xl.sheet_names:
        return {
            "errors": ["시트 이름이 '월별계획'이어야 합니다."],
            "error_details": [{"sheet": "Sheet2", "message": "시트 이름이 '월별계획'이어야 합니다.", "code": "invalid_sheet_name"}],
            "saved": 0,
        }

    df = xl.parse("월별계획", dtype=str).fillna("")
    required = ["기간ID"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {
            "errors": [f"필수 컬럼 누락: {missing}"],
            "error_details": [{"sheet": "Sheet2", "column": ",".join(missing), "message": f"필수 컬럼 누락: {missing}", "code": "missing_required_columns"}],
            "saved": 0,
        }
    df = df[df["기간ID"].apply(lambda v: str(v).strip().isdigit())].reset_index(drop=True)

    # batch lookup: 모든 기간ID를 한번에 조회
    period_ids = {int(str(row.get("기간ID", "")).strip()) for _, row in df.iterrows()
                  if str(row.get("기간ID", "")).strip().isdigit()}
    period_map = {p.id: p for p in db.query(ContractPeriod).filter(ContractPeriod.id.in_(period_ids)).all()} if period_ids else {}

    errors: list[str] = []
    error_details: list[dict] = []
    saved = 0

    for i, row in df.iterrows():
        period_id_str = str(row.get("기간ID", "")).strip()
        if not period_id_str.isdigit():
            continue
        period_id = int(period_id_str)
        period = period_map.get(period_id)
        if not period:
            _append_error(
                errors,
                error_details,
                f"{i + 2}행: 기간ID {period_id}에 해당하는 영업기회가 없습니다.",
                sheet="Sheet2",
                row=i + 2,
                column="기간ID",
                code="missing_contract_period",
            )
            continue

        year_val = period.period_year
        for m in range(1, 13):
            sales = _to_int(row.get(f"{m}월매출", 0))
            gp = _to_int(row.get(f"{m}월GP", 0))
            if sales == 0 and gp == 0:
                continue
            ym = f"{year_val}-{m:02d}-01"
            fc = db.query(MonthlyForecast).filter_by(
                contract_period_id=period.id, forecast_month=ym, is_current=True
            ).first()
            if fc:
                fc.revenue_amount = sales
                fc.gp_amount = gp
            else:
                db.add(MonthlyForecast(
                    contract_period_id=period.id,
                    forecast_month=ym,
                    revenue_amount=sales,
                    gp_amount=gp,
                ))
            saved += 1

    if errors:
        db.rollback()
        return {"errors": errors, "error_details": error_details, "saved": 0}
    db.commit()
    return {"errors": [], "error_details": [], "saved": saved}


def import_actuals_sheet(db: Session, file_bytes: bytes) -> dict:
    """Sheet3(실적) 단독 Import.
    컬럼: 기간ID | 연도 | 사업명(참고) | 매출/매입 | 거래처명 | ... | 1월 | ... | 12월
    '기간ID'는 ContractPeriod.id 기준으로 contract_id를 찾는다.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    if "실적" not in xl.sheet_names:
        return {
            "errors": ["시트 이름이 '실적'이어야 합니다."],
            "error_details": [{"sheet": "Sheet3", "message": "시트 이름이 '실적'이어야 합니다.", "code": "invalid_sheet_name"}],
            "saved": 0,
        }

    df = xl.parse("실적", dtype=str).fillna("")
    required = ["기간ID", "매출/매입", "거래처명"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {
            "errors": [f"필수 컬럼 누락: {missing}"],
            "error_details": [{"sheet": "Sheet3", "column": ",".join(missing), "message": f"필수 컬럼 누락: {missing}", "code": "missing_required_columns"}],
            "saved": 0,
        }
    df = df[df["기간ID"].apply(lambda v: str(v).strip().isdigit())].reset_index(drop=True)

    # batch lookup: 모든 기간ID를 한번에 조회
    period_ids = {int(str(row.get("기간ID", "")).strip()) for _, row in df.iterrows()
                  if str(row.get("기간ID", "")).strip().isdigit()}
    period_map = {p.id: p for p in db.query(ContractPeriod).filter(ContractPeriod.id.in_(period_ids)).all()} if period_ids else {}

    errors: list[str] = []
    error_details: list[dict] = []
    saved = 0

    for i, row in df.iterrows():
        period_id_str = str(row.get("기간ID", "")).strip()
        if not period_id_str.isdigit():
            continue
        period_id = int(period_id_str)
        period = period_map.get(period_id)
        if not period:
            _append_error(
                errors,
                error_details,
                f"{i + 2}행: 기간ID {period_id}에 해당하는 영업기회가 없습니다.",
                sheet="Sheet3",
                row=i + 2,
                column="기간ID",
                code="missing_contract_period",
            )
            continue

        line_type_raw = str(row.get("매출/매입", "")).strip()
        if line_type_raw not in VALID_LINE_TYPES:
            _append_error(
                errors,
                error_details,
                f"{i + 2}행: 매출/매입 값이 올바르지 않습니다 - '{line_type_raw}'",
                sheet="Sheet3",
                row=i + 2,
                column="매출/매입",
                code="invalid_line_type",
            )
            continue

        customer_name = str(row.get("거래처명", "")).strip()
        if not customer_name:
            _append_error(
                errors,
                error_details,
                f"{i + 2}행: 거래처명이 비어있습니다.",
                sheet="Sheet3",
                row=i + 2,
                column="거래처명",
                code="required_customer_name",
            )
            continue

        customer = _get_or_create_customer(
            db,
            name=customer_name,
            tax_contact_name=row.get("세금계산서담당자"),
            tax_contact_phone=row.get("연락처"),
            tax_contact_email=row.get("이메일"),
        )
        line_type = LINE_TYPE_MAP[line_type_raw]
        year_val = period.period_year

        for m in range(1, 13):
            amount = _to_int(row.get(f"{m}월", 0))
            if amount == 0:
                continue
            revenue_month = f"{year_val}-{m:02d}-01"
            db.add(TransactionLine(
                contract_id=period.contract_id,
                revenue_month=revenue_month,
                line_type=line_type,
                customer_id=customer.id,
                supply_amount=amount,
            ))
            saved += 1

    if errors:
        db.rollback()
        return {"errors": errors, "error_details": error_details, "saved": 0}
    db.commit()
    return {"errors": [], "error_details": [], "saved": saved}
