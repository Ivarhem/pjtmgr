"""인프라모듈 Excel Export 서비스 — 프로젝트 단위 데이터 내보내기."""
from __future__ import annotations

from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.ip_subnet import IpSubnet
from app.modules.infra.models.port_map import PortMap
from app.modules.infra.models.project import Project

# ── 헤더 / 필드 매핑 ──

_INVENTORY_HEADERS = [
    ("Seq", None),
    ("센터", "center"),
    ("운영유형", "operation_type"),
    ("장비ID", "equipment_id"),
    ("랙 No", "rack_no"),
    ("랙 Unit", "rack_unit"),
    ("Phase", "phase"),
    ("입고일", "received_date"),
    ("분류", "category"),
    ("세분류", "subcategory"),
    ("제조사", "vendor"),
    ("모델", "model"),
    ("S/N", "serial_no"),
    ("호스트명", "hostname"),
    ("클러스터", "cluster"),
    ("서비스명", "service_name"),
    ("Zone", "zone"),
    ("서비스IP", "service_ip"),
    ("관리IP", "mgmt_ip"),
    ("Size(U)", "size_unit"),
    ("LC", "lc_count"),
    ("HA", "ha_count"),
    ("UTP", "utp_count"),
    ("전원 수", "power_count"),
    ("전원유형", "power_type"),
    ("FW버전", "firmware_version"),
    ("자산분류", "asset_class"),
    ("자산번호", "asset_number"),
    ("취득년도", "year_acquired"),
    ("부서", "dept"),
    ("주담당", "primary_contact_name"),
    ("부담당", "secondary_contact_name"),
    ("유지보수사", "maintenance_vendor"),
    ("비고", "note"),
]

_SUBNET_HEADERS = [
    ("대역명", "name"),
    ("Subnet (CIDR)", "subnet"),
    ("Netmask", "netmask"),
    ("Gateway", "gateway"),
    ("VLAN", "vlan_id"),
    ("Zone", "zone"),
    ("역할", "role"),
    ("지역/층", "region"),
    ("분류", "category"),
    ("설명", "description"),
]

_PORTMAP_HEADERS = [
    ("Seq", "seq"),
    ("요약", "summary"),
    ("연결유형", "connection_type"),
    ("출발 호스트명", "src_hostname"),
    ("출발 IP", "src_ip"),
    ("출발 Slot", "src_slot"),
    ("출발 Port", "src_port_name"),
    ("출발 Zone", "src_zone"),
    ("출발 VLAN", "src_vlan"),
    ("도착 호스트명", "dst_hostname"),
    ("도착 IP", "dst_ip"),
    ("도착 Slot", "dst_slot"),
    ("도착 Port", "dst_port_name"),
    ("도착 Zone", "dst_zone"),
    ("도착 VLAN", "dst_vlan"),
    ("프로토콜", "protocol"),
    ("포트", "port"),
    ("용도", "purpose"),
    ("상태", "status"),
    ("케이블유형", "cable_type"),
    ("케이블속도", "cable_speed"),
    ("케이블번호", "cable_no"),
    ("비고", "note"),
]

# ── 스타일 ──

_HEADER_FONT = Font(bold=True, size=10)
_HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_header(ws, headers: list[tuple[str, str | None]]) -> None:
    for col_idx, (label, _) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN


def _auto_width(ws, headers: list[tuple[str, str | None]]) -> None:
    for col_idx, (label, _) in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(label) + 2
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)) + 1)
        ws.column_dimensions[col_letter].width = min(max_len + 1, 40)


# ── 메인 ──


def export_project(db: Session, project_id: int) -> bytes:
    """프로젝트 데이터를 3개 시트(Inventory, IP대역, Portmap)로 Export."""
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")

    wb = openpyxl.Workbook()

    # Sheet 1: Inventory (Assets)
    ws_inv = wb.active
    ws_inv.title = "01. Inventory"
    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.project_id == project_id)
            .order_by(Asset.id.asc())
        )
    )
    _write_header(ws_inv, _INVENTORY_HEADERS)
    for row_idx, asset in enumerate(assets, 2):
        for col_idx, (_, field) in enumerate(_INVENTORY_HEADERS, 1):
            if field is None:
                ws_inv.cell(row=row_idx, column=col_idx, value=row_idx - 1)
            else:
                val = getattr(asset, field, None)
                if val is not None:
                    val = str(val)
                ws_inv.cell(row=row_idx, column=col_idx, value=val)
    _auto_width(ws_inv, _INVENTORY_HEADERS)

    # Sheet 2: IP 대역
    ws_sub = wb.create_sheet("05. 네트워크 대역")
    subnets = list(
        db.scalars(
            select(IpSubnet)
            .where(IpSubnet.project_id == project_id)
            .order_by(IpSubnet.id.asc())
        )
    )
    _write_header(ws_sub, _SUBNET_HEADERS)
    for row_idx, sub in enumerate(subnets, 2):
        for col_idx, (_, field) in enumerate(_SUBNET_HEADERS, 1):
            val = getattr(sub, field, None)
            if val is not None:
                val = str(val)
            ws_sub.cell(row=row_idx, column=col_idx, value=val)
    _auto_width(ws_sub, _SUBNET_HEADERS)

    # Sheet 3: Portmap
    ws_pm = wb.create_sheet("03. Portmap")
    portmaps = list(
        db.scalars(
            select(PortMap)
            .where(PortMap.project_id == project_id)
            .order_by(PortMap.id.asc())
        )
    )
    _write_header(ws_pm, _PORTMAP_HEADERS)
    for row_idx, pm in enumerate(portmaps, 2):
        for col_idx, (_, field) in enumerate(_PORTMAP_HEADERS, 1):
            val = getattr(pm, field, None)
            if val is not None:
                val = str(val) if not isinstance(val, int) else val
            ws_pm.cell(row=row_idx, column=col_idx, value=val)
    _auto_width(ws_pm, _PORTMAP_HEADERS)

    # 바이트 출력
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
