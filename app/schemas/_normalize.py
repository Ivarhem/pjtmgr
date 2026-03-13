"""날짜/월 문자열 정규화 유틸.

다양한 입력 형식을 표준 형식으로 변환 후 유효성을 검증한다.
스키마의 @field_validator에서 호출하여 사용.

지원하는 입력 형식:
  월(YYYY-MM-01):
    "2025-01-01"  → 그대로
    "2025-01"     → "2025-01-01"
    "202501"      → "2025-01-01"
    "2501"        → "2025-01-01"
  날짜(YYYY-MM-DD):
    "2025-01-15"  → 그대로
    "20250115"    → "2025-01-15"
    "250115"      → "2025-01-15"
    "2025-1-5"    → "2025-01-05"
"""
from __future__ import annotations

import re
from datetime import date

# 정규화 후 최종 검증용 정규식
_YEAR_MONTH_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-01$")
_DATE_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")


def _expand_year(yy: str) -> str:
    """2자리 연도를 4자리로 확장. 00-79 → 2000s, 80-99 → 1900s."""
    y = int(yy)
    return str(2000 + y) if y < 80 else str(1900 + y)


def normalize_month(v: str) -> str:
    """다양한 형식의 월 문자열을 YYYY-MM-01로 정규화.

    Raises:
        ValueError: 인식할 수 없는 형식이거나 유효하지 않은 월인 경우.
    """
    s = v.strip().replace("/", "-")

    # 이미 올바른 형식
    if _YEAR_MONTH_RE.match(s):
        return s

    # "2025-01" → "2025-01-01"
    if re.match(r"^\d{4}-\d{1,2}$", s):
        parts = s.split("-")
        result = f"{parts[0]}-{int(parts[1]):02d}-01"
        if _YEAR_MONTH_RE.match(result):
            return result

    # "202501" (6자리 YYYYMM)
    if re.match(r"^\d{6}$", s):
        result = f"{s[:4]}-{s[4:6]}-01"
        if _YEAR_MONTH_RE.match(result):
            return result

    # "2501" (4자리 YYMM)
    if re.match(r"^\d{4}$", s):
        year = _expand_year(s[:2])
        result = f"{year}-{s[2:4]}-01"
        if _YEAR_MONTH_RE.match(result):
            return result

    raise ValueError(
        f"월 형식을 인식할 수 없습니다: '{v}' "
        "(허용: YYYY-MM-01, YYYY-MM, YYYYMM, YYMM)"
    )


def normalize_date(v: str) -> str:
    """다양한 형식의 날짜 문자열을 YYYY-MM-DD로 정규화.

    Raises:
        ValueError: 인식할 수 없는 형식이거나 유효하지 않은 날짜인 경우.
    """
    s = v.strip().replace("/", "-")

    # 이미 올바른 형식
    if _DATE_RE.match(s):
        return s

    # "2025-1-5" 같은 대시 구분이지만 leading zero 없는 경우
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", s):
        parts = s.split("-")
        result = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if _DATE_RE.match(result):
            _validate_real_date(result)
            return result

    # "25-1-5" 같은 2자리 연도 + 대시
    if re.match(r"^\d{2}-\d{1,2}-\d{1,2}$", s):
        parts = s.split("-")
        year = _expand_year(parts[0])
        result = f"{year}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if _DATE_RE.match(result):
            _validate_real_date(result)
            return result

    # "20250115" (8자리 YYYYMMDD)
    if re.match(r"^\d{8}$", s):
        result = f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        if _DATE_RE.match(result):
            _validate_real_date(result)
            return result

    # "250115" (6자리 YYMMDD)
    if re.match(r"^\d{6}$", s):
        year = _expand_year(s[:2])
        result = f"{year}-{s[2:4]}-{s[4:6]}"
        if _DATE_RE.match(result):
            _validate_real_date(result)
            return result

    raise ValueError(
        f"날짜 형식을 인식할 수 없습니다: '{v}' "
        "(허용: YYYY-MM-DD, YYYYMMDD, YYMMDD)"
    )


def _validate_real_date(s: str) -> None:
    """정규식 통과 후 실제 달력상 유효한 날짜인지 검증 (예: 2월 30일 방지)."""
    try:
        parts = s.split("-")
        date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise ValueError(f"유효하지 않은 날짜입니다: '{s}'")
