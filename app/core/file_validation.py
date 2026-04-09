"""파일 업로드 유효성 검증 (공통)."""
from __future__ import annotations

import os

from app.core.exceptions import BusinessRuleError

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_ALLOWED_CSV_EXTENSIONS = {".csv"}
_ALLOWED_CSV_MIMES = {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}


def validate_xlsx(filename: str | None, content_type: str | None) -> None:
    """Excel 파일 확장자 및 MIME 타입 검증."""
    if not filename or not filename.lower().endswith(".xlsx"):
        raise BusinessRuleError("xlsx 파일만 업로드할 수 있습니다.", status_code=422)
    if content_type and content_type != _XLSX_MIME:
        raise BusinessRuleError("xlsx 파일만 업로드할 수 있습니다.", status_code=422)


def validate_csv(filename: str | None, content_type: str | None) -> None:
    """CSV 파일 확장자 및 MIME 타입 검증."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ALLOWED_CSV_EXTENSIONS:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)
    if content_type and content_type not in _ALLOWED_CSV_MIMES:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)
