"""Excel Import 서비스 (3시트 템플릿 파싱 및 DB 저장)"""
from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.monthly_forecast import MonthlyForecast
from app.models.transaction_line import TransactionLine
from app.auth.constants import ROLE_USER
from app.services.customer import get_or_create_by_name as _get_or_create_customer_svc

if TYPE_CHECKING:
    from app.models.customer import Customer
from app.schemas.contract import VALID_STAGES
from app.services.contract_type_config import get_valid_codes as _get_valid_contract_types
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
        user = User(name=name, login_id=name.lower().replace(" ", "_"), role=ROLE_USER)
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


def parse_and_validate(file_bytes: bytes, db: Session | None = None) -> dict:
    """파싱 + 유효성 검사. errors 리스트 반환."""
    xl = pd.ExcelFile(BytesIO(file_bytes))
    errors = []

    # Sheet1: 영업기회
    if "영업기회" not in xl.sheet_names:
        return {"errors": ["Sheet1 이름이 '영업기회'여야 합니다."], "data": None}
    df1 = xl.parse("영업기회", dtype=str).fillna("")
    # 안내 행(연도가 4자리 숫자가 아닌 행) 제거
    df1 = df1[df1["연도"].str.strip().str.match(r"^\d{4}$")].reset_index(drop=True)

    # "구분" → "사업유형" 하위 호환
    if "구분" in df1.columns and "사업유형" not in df1.columns:
        df1.rename(columns={"구분": "사업유형"}, inplace=True)

    required1 = ["연도", "번호", "사업유형", "거래처(END)", "영업기회명", "진행단계"]
    missing = [c for c in required1 if c not in df1.columns]
    if missing:
        return {"errors": [f"Sheet1 필수 컬럼 누락: {missing}"], "data": None}

    # 사업유형·진행단계 정규화 적용
    df1["사업유형"] = df1["사업유형"].apply(lambda v: _norm_contract_type(str(v)))
    df1["진행단계"] = df1["진행단계"].apply(lambda v: _norm_stage(str(v)))

    valid_contract_types = _get_valid_contract_types(db) if db else set()

    for i, row in df1.iterrows():
        r = i + 2
        if not row["연도"].strip():
            errors.append(f"Sheet1 {r}행: 연도 필수")
        if not row["번호"].strip():
            errors.append(f"Sheet1 {r}행: 번호 필수")
        if valid_contract_types and row["사업유형"].strip() not in valid_contract_types:
            errors.append(f"Sheet1 {r}행: 사업유형 허용값({valid_contract_types}) 오류 - '{row['사업유형']}'")
        if row["진행단계"].strip() not in VALID_STAGES:
            errors.append(f"Sheet1 {r}행: 진행단계 허용값({VALID_STAGES}) 오류 - '{row['진행단계']}'")

    # Sheet2: 월별계획 (선택)
    if "월별계획" in xl.sheet_names:
        df2 = xl.parse("월별계획", dtype=str).fillna("")
        if "연도" not in df2.columns:
            errors.append("Sheet2 필수 컬럼 누락: ['연도']")
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
            errors.append(f"Sheet3 필수 컬럼 누락: {missing3}")
            df3 = None
        else:
            df3 = df3[df3["연도"].apply(lambda v: str(v).strip().isdigit() and len(str(v).strip()) == 4)].reset_index(drop=True)
            opp_keys = set(zip(df1["연도"].str.strip(), df1["번호"].str.strip()))
            for i, row in df3.iterrows():
                r = i + 2
                key = (row["연도"].strip(), row["번호"].strip())
                if key not in opp_keys:
                    errors.append(f"Sheet3 {r}행: 연도+번호({key})가 Sheet1에 없음")
                if row["매출/매입"].strip() not in VALID_LINE_TYPES:
                    errors.append(f"Sheet3 {r}행: 매출/매입 허용값 오류 - '{row['매출/매입']}'")

    return {
        "errors": errors,
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

    df1, df2, df3 = result["data"]["df1"], result["data"]["df2"], result["data"]["df3"]
    created = skipped = 0
    new_users: list[str] = []

    # (연도, 번호) → ContractPeriod 매핑 (Sheet2/Sheet3 연결용)
    period_map: dict[tuple, ContractPeriod] = {}

    for _, row in df1.iterrows():
        year = int(row["연도"].strip())
        seq_no_str = row["번호"].strip()
        contract_name = row["영업기회명"].strip()
        contract_type = row["사업유형"].strip()

        # 중복 탐지: period_year + contract_name 기준
        existing_period = (
            db.query(ContractPeriod)
            .join(ContractPeriod.contract)
            .filter(ContractPeriod.period_year == year, Contract.contract_name == contract_name)
            .first()
        )

        if existing_period and on_duplicate == "skip":
            skipped += 1
            period_map[(row["연도"].strip(), seq_no_str)] = existing_period
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
            period_map[(row["연도"].strip(), seq_no_str)] = existing_period
        else:
            contract = Contract(
                contract_name=contract_name,
                contract_type=contract_type,
                end_customer_id=end_customer.id,
                owner_user_id=owner.id if owner else None,
                status="active",
            )
            db.add(contract)
            db.flush()

            year_suffix = str(year)[-2:]
            contract.contract_code = f"{contract_type}-{year}-{contract.id:04d}"

            period = ContractPeriod(
                contract_id=contract.id,
                period_year=year,
                period_label=f"Y{year_suffix}",
                stage=row["진행단계"].strip(),
                expected_revenue_total=_to_int(row.get("예상매출(원)", "")),
                expected_gp_total=_to_int(row.get("예상GP(원)", "")),
            )
            db.add(period)
            db.flush()
            period_map[(row["연도"].strip(), seq_no_str)] = period
            created += 1

    # Sheet2: 월별계획 → MonthlyForecast
    if df2 is not None:
        for _, row in df2.iterrows():
            key = (row["연도"].strip(), row["번호"].strip())
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
            key = (row["연도"].strip(), row["번호"].strip())
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
        return {"errors": ["시트 이름이 '월별계획'이어야 합니다."], "saved": 0}

    df = xl.parse("월별계획", dtype=str).fillna("")
    required = ["기간ID"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"errors": [f"필수 컬럼 누락: {missing}"], "saved": 0}
    df = df[df["기간ID"].apply(lambda v: str(v).strip().isdigit())].reset_index(drop=True)

    # batch lookup: 모든 기간ID를 한번에 조회
    period_ids = {int(str(row.get("기간ID", "")).strip()) for _, row in df.iterrows()
                  if str(row.get("기간ID", "")).strip().isdigit()}
    period_map = {p.id: p for p in db.query(ContractPeriod).filter(ContractPeriod.id.in_(period_ids)).all()} if period_ids else {}

    errors: list[str] = []
    saved = 0

    for i, row in df.iterrows():
        period_id_str = str(row.get("기간ID", "")).strip()
        if not period_id_str.isdigit():
            continue
        period_id = int(period_id_str)
        period = period_map.get(period_id)
        if not period:
            errors.append(f"{i + 2}행: 기간ID {period_id}에 해당하는 영업기회가 없습니다.")
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
        return {"errors": errors, "saved": 0}
    db.commit()
    return {"errors": [], "saved": saved}


def import_actuals_sheet(db: Session, file_bytes: bytes) -> dict:
    """Sheet3(실적) 단독 Import.
    컬럼: 기간ID | 연도 | 사업명(참고) | 매출/매입 | 거래처명 | ... | 1월 | ... | 12월
    '기간ID'는 ContractPeriod.id 기준으로 contract_id를 찾는다.
    """
    xl = pd.ExcelFile(BytesIO(file_bytes))
    if "실적" not in xl.sheet_names:
        return {"errors": ["시트 이름이 '실적'이어야 합니다."], "saved": 0}

    df = xl.parse("실적", dtype=str).fillna("")
    required = ["기간ID", "매출/매입", "거래처명"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"errors": [f"필수 컬럼 누락: {missing}"], "saved": 0}
    df = df[df["기간ID"].apply(lambda v: str(v).strip().isdigit())].reset_index(drop=True)

    # batch lookup: 모든 기간ID를 한번에 조회
    period_ids = {int(str(row.get("기간ID", "")).strip()) for _, row in df.iterrows()
                  if str(row.get("기간ID", "")).strip().isdigit()}
    period_map = {p.id: p for p in db.query(ContractPeriod).filter(ContractPeriod.id.in_(period_ids)).all()} if period_ids else {}

    errors: list[str] = []
    saved = 0

    for i, row in df.iterrows():
        period_id_str = str(row.get("기간ID", "")).strip()
        if not period_id_str.isdigit():
            continue
        period_id = int(period_id_str)
        period = period_map.get(period_id)
        if not period:
            errors.append(f"{i + 2}행: 기간ID {period_id}에 해당하는 영업기회가 없습니다.")
            continue

        line_type_raw = str(row.get("매출/매입", "")).strip()
        if line_type_raw not in VALID_LINE_TYPES:
            errors.append(f"{i + 2}행: 매출/매입 값이 올바르지 않습니다 - '{line_type_raw}'")
            continue

        customer_name = str(row.get("거래처명", "")).strip()
        if not customer_name:
            errors.append(f"{i + 2}행: 거래처명이 비어있습니다.")
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
        return {"errors": errors, "saved": 0}
    db.commit()
    return {"errors": [], "saved": saved}
