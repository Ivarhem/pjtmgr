from __future__ import annotations

from pydantic import BaseModel


class ImportErrorDetail(BaseModel):
    message: str
    sheet: str | None = None
    row: int | None = None
    column: str | None = None
    code: str | None = None


class ImportPreviewRow(BaseModel):
    row_num: int
    asset_name: str | None = None
    asset_type: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    model: str | None = None
    serial_no: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    status: str | None = None
    errors: list[str] | None = None


class ImportPreviewResponse(BaseModel):
    valid: bool
    total: int
    valid_count: int
    errors: list[str]
    error_details: list[ImportErrorDetail]
    warnings: list[str]
    rows: list[ImportPreviewRow]


class ImportConfirmResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]
    error_details: list[ImportErrorDetail]
