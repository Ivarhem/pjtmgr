"""Infra module: asset Excel import service tests."""
from __future__ import annotations

import openpyxl
from io import BytesIO

import pytest

from app.modules.common.models.customer import Customer
from app.modules.infra.models.asset import Asset
from app.modules.infra.services.infra_importer import (
    parse_inventory_sheet,
    import_inventory,
    INVENTORY_SHEET_NAME,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="import_admin", name="ImportAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session, name: str = "Import고객사") -> Customer:
    customer = Customer(name=name)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def _build_inventory_xlsx(rows: list[list], sheet_name: str = INVENTORY_SHEET_NAME) -> bytes:
    """
    테스트용 Inventory 시트가 포함된 xlsx 파일을 빌드한다.

    rows: 데이터 행 목록. 각 행은 35개 컬럼에 대응 (col 1~35).
    Row 1-2: 그룹 헤더 (빈 행), Row 3: 컬럼 헤더, Row 4+: 데이터.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Row 1-2: 그룹 헤더 (빈 행)
    ws.append([""] * 35)
    ws.append([""] * 35)

    # Row 3: 컬럼 헤더
    headers = [
        "", "Seq", "센터", "운영구분", "장비관리번호 MID", "Rack No.", "랙내 위치",
        "단계", "입고일", "대분류", "소분류", "제조사", "모델명", "Serial No.",
        "Hostname", "클러스터", "업무명", "Zone", "Service IP", "MGMT IP",
        "Size(unit)", "LC수량", "HA수량", "UTP수량", "전원수량", "전원Type",
        "Firmware Version", "자산 구분", "자산 번호", "도입년도", "관리부서",
        "담당자(정)", "담당자(부)", "유지보수업체", "비고",
    ]
    ws.append(headers)

    # Data rows (Row 4+)
    for row in rows:
        ws.append(row)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_data_row(
    seq: str = "1",
    center: str = "IDC-A",
    operation_type: str = "운영",
    equipment_id: str = "MID-001",
    hostname: str = "APP-SVR-01",
    category: str = "서버",
    subcategory: str = "x86",
    vendor: str = "Dell",
    model_name: str = "R740",
    serial_no: str = "SN001",
    service_ip: str = "10.0.1.1",
    mgmt_ip: str = "10.0.2.1",
) -> list:
    """35개 컬럼의 데이터 행 생성 헬퍼."""
    row = [""] * 35
    row[1] = seq            # Seq
    row[2] = center         # 센터
    row[3] = operation_type # 운영구분
    row[4] = equipment_id   # 장비관리번호
    row[5] = ""             # Rack No.
    row[6] = ""             # 랙내 위치
    row[7] = ""             # 단계
    row[8] = ""             # 입고일
    row[9] = category       # 대분류
    row[10] = subcategory   # 소분류
    row[11] = vendor        # 제조사
    row[12] = model_name    # 모델명
    row[13] = serial_no     # Serial No.
    row[14] = hostname      # Hostname
    row[15] = ""            # 클러스터
    row[16] = ""            # 업무명
    row[17] = ""            # Zone
    row[18] = service_ip    # Service IP
    row[19] = mgmt_ip       # MGMT IP
    row[20] = "2"           # Size(unit)
    row[21] = ""            # LC수량
    row[22] = ""            # HA수량
    row[23] = ""            # UTP수량
    row[24] = "2"           # 전원수량
    row[25] = "AC"          # 전원Type
    row[26] = ""            # Firmware Version
    row[27] = ""            # 자산 구분
    row[28] = ""            # 자산 번호
    row[29] = "2024"        # 도입년도
    row[30] = ""            # 관리부서
    row[31] = ""            # 담당자(정)
    row[32] = ""            # 담당자(부)
    row[33] = ""            # 유지보수업체
    row[34] = ""            # 비고
    return row


# ── 파싱 테스트 ──


def test_parse_normal_rows() -> None:
    """정상 데이터 파싱."""
    rows = [
        _make_data_row(seq="1", hostname="SVR-01", category="서버"),
        _make_data_row(seq="2", hostname="FW-01", category="방화벽", vendor="Palo Alto"),
    ]
    xlsx = _build_inventory_xlsx(rows)
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 2
    assert result["valid_count"] == 2
    assert len(result["errors"]) == 0
    assert result["rows"][0]["asset_name"] == "SVR-01"
    assert result["rows"][0]["asset_type"] == "server"
    assert result["rows"][1]["asset_name"] == "FW-01"
    assert result["rows"][1]["asset_type"] == "security"


def test_parse_empty_sheet() -> None:
    """빈 시트 처리."""
    xlsx = _build_inventory_xlsx([])
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 0
    assert len(result["errors"]) == 1
    assert "데이터 행이 없습니다" in result["errors"][0]


def test_parse_duplicate_asset_name() -> None:
    """파일 내 중복 자산명 검증."""
    rows = [
        _make_data_row(seq="1", hostname="SVR-01"),
        _make_data_row(seq="2", hostname="SVR-01"),
    ]
    xlsx = _build_inventory_xlsx(rows)
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 2
    assert len(result["errors"]) == 1
    assert "중복" in result["errors"][0]
    assert result["error_details"][0]["code"] == "duplicate_asset_in_upload"


def test_parse_missing_hostname_uses_equipment_id() -> None:
    """hostname 없으면 equipment_id를 asset_name으로 사용."""
    rows = [
        _make_data_row(seq="1", hostname="", equipment_id="MID-999", category="서버"),
    ]
    xlsx = _build_inventory_xlsx(rows)
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 1
    assert result["rows"][0]["asset_name"] == "MID-999"


def test_parse_missing_category_warning() -> None:
    """대분류 미입력 시 경고."""
    rows = [
        _make_data_row(seq="1", hostname="SVR-01", category=""),
    ]
    xlsx = _build_inventory_xlsx(rows)
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 1
    assert any("대분류" in w for w in result["warnings"])
    assert result["rows"][0]["asset_type"] == "etc"


def test_parse_integer_fields() -> None:
    """정수 필드 정상 변환."""
    rows = [_make_data_row(seq="1", hostname="SVR-01")]
    xlsx = _build_inventory_xlsx(rows)
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["rows"][0]["size_unit"] == 2
    assert result["rows"][0]["power_count"] == 2
    assert result["rows"][0]["year_acquired"] == 2024


def test_parse_wrong_sheet_name_falls_back() -> None:
    """시트명이 다르면 첫 번째 시트로 폴백 + 경고."""
    rows = [_make_data_row(seq="1", hostname="SVR-01", category="서버")]
    xlsx = _build_inventory_xlsx(rows, sheet_name="Sheet1")
    result = parse_inventory_sheet(xlsx, customer_id=1)

    assert result["total"] == 1
    assert any("첫 번째 시트" in w for w in result["warnings"])


# ── Import 테스트 ──


def test_import_creates_assets(db_session, admin_role_id) -> None:
    """정상 Import: 자산 생성 확인."""
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    rows = [
        _make_data_row(seq="1", hostname="IMP-SVR-01", category="서버"),
        _make_data_row(seq="2", hostname="IMP-FW-01", category="방화벽"),
    ]
    xlsx = _build_inventory_xlsx(rows)
    parsed = parse_inventory_sheet(xlsx, customer.id)
    assert len(parsed["errors"]) == 0

    result = import_inventory(db_session, customer.id, parsed["rows"], admin)
    assert result["created"] == 2
    assert result["skipped"] == 0

    # DB 검증
    assets = db_session.query(Asset).filter(Asset.customer_id == customer.id).all()
    assert len(assets) == 2
    names = {a.asset_name for a in assets}
    assert "IMP-SVR-01" in names
    assert "IMP-FW-01" in names


def test_import_skip_existing(db_session, admin_role_id) -> None:
    """on_duplicate=skip: 기존 자산 건너뛰기."""
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    # 기존 자산 생성
    existing = Asset(customer_id=customer.id, asset_name="SVR-EXIST", asset_type="server")
    db_session.add(existing)
    db_session.commit()

    rows = [
        _make_data_row(seq="1", hostname="SVR-EXIST", category="서버"),
        _make_data_row(seq="2", hostname="SVR-NEW", category="서버"),
    ]
    xlsx = _build_inventory_xlsx(rows)
    parsed = parse_inventory_sheet(xlsx, customer.id)

    result = import_inventory(db_session, customer.id, parsed["rows"], admin, on_duplicate="skip")
    assert result["created"] == 1
    assert result["skipped"] == 1


def test_import_nonexistent_customer(db_session, admin_role_id) -> None:
    """존재하지 않는 고객사 Import 시 에러."""
    admin = _make_admin_user(db_session, admin_role_id)
    result = import_inventory(db_session, 99999, [{"asset_name": "X", "customer_id": 99999}], admin)
    assert len(result["errors"]) == 1
    assert result["error_details"][0]["code"] == "customer_not_found"
