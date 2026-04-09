"""계층적 코드 채번 유틸리티.

코드 형식: P000-B000-Y26A
- 업체코드: P + base36(3) 전역 순번
- 사업코드: {업체코드}-B + base36(3) 업체 내 순번
- 기간코드: {사업코드}-Y + 연도(2) + A~Z 순번
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError

_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE36_MAP = {c: i for i, c in enumerate(_BASE36)}

RESERVED_PARTNER_CODE = "PXXX"


def int_to_base36(n: int, width: int = 3) -> str:
    """정수 -> 고정 폭 base36 문자열. 0->'000', 35->'00Z', 36->'010'."""
    result: list[str] = []
    for _ in range(width):
        result.append(_BASE36[n % 36])
        n //= 36
    return "".join(reversed(result))


def base36_to_int(s: str) -> int:
    """base36 문자열 -> 정수. '00Z'->35, '010'->36."""
    n = 0
    for c in s:
        n = n * 36 + _BASE36_MAP[c]
    return n


def next_partner_code(db: Session) -> str:
    """전역 MAX partner_code 다음 번호. P000~PZZZ. PXXX 건너뜀."""
    row = db.execute(
        text("SELECT MAX(partner_code) FROM partners WHERE partner_code LIKE 'P%' AND partner_code != :reserved"),
        {"reserved": RESERVED_PARTNER_CODE},
    ).scalar()
    if row:
        n = base36_to_int(row[1:]) + 1  # 'P' prefix 제거
    else:
        n = 0
    # PXXX (base36 XXX = 44252) 건너뛰기
    reserved_n = base36_to_int("XXX")
    if n == reserved_n:
        n += 1
    return f"P{int_to_base36(n)}"


def next_business_code(db: Session, partner_code: str) -> str:
    """해당 업체의 MAX contract_code에서 B-부분 다음 번호."""
    pattern = f"{partner_code}-B%"
    row = db.execute(
        text("SELECT MAX(contract_code) FROM contracts WHERE contract_code LIKE :pattern"),
        {"pattern": pattern},
    ).scalar()
    if row:
        b_part = row.split("-B")[-1]  # "000" ~ "ZZZ"
        n = base36_to_int(b_part) + 1
    else:
        n = 0
    return f"{partner_code}-B{int_to_base36(n)}"


def next_period_code(db: Session, contract_code: str, period_year: int) -> str:
    """해당 사업+연도의 MAX period_code에서 suffix letter 다음. A~Z (26슬롯)."""
    year_suffix = f"Y{period_year % 100:02d}"
    pattern = f"{contract_code}-{year_suffix}%"
    row = db.execute(
        text("SELECT MAX(period_code) FROM contract_periods WHERE period_code LIKE :pattern"),
        {"pattern": pattern},
    ).scalar()
    if row:
        last_letter = row[-1]  # A ~ Z
        if last_letter == "Z":
            raise BusinessRuleError("해당 연도의 기간 슬롯이 모두 사용되었습니다 (최대 26개)")
        next_letter = chr(ord(last_letter) + 1)
    else:
        next_letter = "A"
    return f"{contract_code}-{year_suffix}{next_letter}"
