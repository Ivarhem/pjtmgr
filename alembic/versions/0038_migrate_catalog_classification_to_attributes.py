# -*- coding: utf-8 -*-
"""Migrate catalog classification data into attribute values.

Revision ID: 0038
Revises: 0037
Create Date: 2026-03-27
"""

from __future__ import annotations

from datetime import datetime, timezone
import re

from alembic import op
import sqlalchemy as sa


revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_text(*values) -> str:
    text = " ".join(str(value or "") for value in values).lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9가-힣\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text) is not None


def _infer_imp_type(product_type: str | None, asset_kind: str | None, node_code: str | None) -> str:
    candidates = [asset_kind or "", product_type or "", node_code or ""]
    text = _normalize_text(*candidates)
    if "hardware" in text or text.startswith("hw"):
        return "hw"
    if "software" in text or text.startswith("sw"):
        return "sw"
    if "service" in text or "svc" in text:
        return "svc"
    if "model" in text:
        return "svc"
    return "hw"


def _infer_domain(text: str, node_code: str | None, asset_type_key: str | None) -> str:
    normalized = _normalize_text(text, node_code, asset_type_key)
    code = (node_code or "").upper()
    if asset_type_key == "dbms" or " db " in f" {normalized} " or "oracle" in normalized or "mssql" in normalized or "postgres" in normalized:
        return "db"
    if asset_type_key == "storage" or any(token in normalized for token in ("storage", "스토리지", "nas", "san", "backup", "백업")):
        return "sto"
    if asset_type_key == "server" or any(token in normalized for token in ("server", "서버", "x86", "unix", "linux", "windows server")):
        return "svr"
    if asset_type_key == "network" or any(token in normalized for token in ("network", "네트워크", "switch", "router", "nms")) or any(
        _contains_token(normalized, token) for token in ("l2", "l3", "l4", "ap")
    ):
        return "net"
    if asset_type_key == "security" or any(token in normalized for token in ("security", "보안", "firewall", "fw", "utm", "ips", "waf", "ddos", "vpn", "siem", "pan os", "fortios", "junos")):
        return "sec"
    if code.startswith("SW-DB"):
        return "db"
    if code.startswith("HW-STR"):
        return "sto"
    if code.startswith("HW-SRV") or code.startswith("SW-OS"):
        return "svr"
    if code.startswith("HW-NET"):
        return "net"
    if code.startswith("HW-SEC") or code.startswith("SW-SEC"):
        return "sec"
    return "sec" if "ai" in normalized else "svr"


def _infer_product_family(text: str, node_code: str | None, domain: str) -> str:
    normalized = _normalize_text(text, node_code)
    code = (node_code or "").upper()
    if any(token in normalized for token in ("firewall", "방화벽", " fortigate ", " srx", "ngf", "axgate", "pan os", "junos", "fortios")) or code.endswith("-FW"):
        return "fw"
    if "utm" in normalized or code.endswith("-UTM"):
        return "fw"
    if "ips" in normalized or code.endswith("-IPS"):
        return "ips"
    if "waf" in normalized or code.endswith("-WAF"):
        return "waf"
    if "ddos" in normalized or code.endswith("-DDOS"):
        return "ddos"
    if "siem" in normalized:
        return "siem"
    if "nms" in normalized:
        return "nms"
    if _contains_token(normalized, "l2") or code.endswith("-L2"):
        return "l2"
    if _contains_token(normalized, "l3") or code.endswith("-L3"):
        return "l3"
    if _contains_token(normalized, "l4") or code.endswith("-L4"):
        return "l4"
    if any(token in normalized for token in ("x86", "proliant", "poweredge")) or code.endswith("-X86"):
        return "x86_server"
    if "unix" in normalized or code.endswith("-UNIX"):
        return "unix_server"
    if "nas" in normalized or code.endswith("-NAS"):
        return "nas"
    if "san" in normalized or code.endswith("-SAN"):
        return "san"
    if any(token in normalized for token in ("oracle", "mssql", "mysql", "postgres", "dbms")) or code.startswith("SW-DB"):
        return "dbms"
    if any(token in normalized for token in ("windows", "linux", "unix", "operating system", "운영체제")) or code.startswith("SW-OS"):
        return "os"
    if "backup" in normalized or "백업" in normalized:
        return "backup"
    if any(token in normalized for token in ("middleware", "was", "web server", "web", "mq", "tp monitor")) or code.startswith("SW-MW"):
        return "middleware"
    if domain == "db":
        return "dbms"
    return "generic"


def _infer_platform(text: str, product_family: str) -> str | None:
    normalized = _normalize_text(text)
    if "appliance" in normalized or product_family in {"fw", "ips", "waf", "ddos", "l2", "l3", "l4", "nas", "san"}:
        if any(token in normalized for token in ("fortigate", "srx", "ngf", "switch", "router", "storage", "nas", "san", "appliance")):
            return "appliance"
    if "windows" in normalized:
        return "windows"
    if "linux" in normalized:
        return "linux"
    if "unix" in normalized:
        return "unix"
    if "x86" in normalized or any(token in normalized for token in ("poweredge", "proliant")):
        return "x86"
    if "container" in normalized:
        return "container"
    if "vm" in normalized or "virtual" in normalized:
        return "vm"
    return None


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    attribute_rows = conn.execute(
        sa.text("SELECT id, attribute_key FROM catalog_attribute_defs WHERE attribute_key IN ('domain', 'imp_type', 'product_family', 'platform')")
    ).fetchall()
    attribute_ids = {row.attribute_key: int(row.id) for row in attribute_rows}
    option_rows = conn.execute(
        sa.text(
            """
            SELECT a.attribute_key, o.option_key, o.id
            FROM catalog_attribute_options o
            JOIN catalog_attribute_defs a ON a.id = o.attribute_id
            WHERE a.attribute_key IN ('domain', 'imp_type', 'product_family', 'platform')
            """
        )
    ).fetchall()
    option_ids = {(row.attribute_key, row.option_key): int(row.id) for row in option_rows}

    node_rows = conn.execute(
        sa.text(
            """
            SELECT
                n.id,
                n.node_code,
                n.node_name,
                n.parent_id,
                n.asset_type_key,
                n.asset_type_label,
                n.asset_kind,
                s.scope_type,
                n.scheme_id
            FROM classification_nodes n
            JOIN classification_schemes s ON s.id = n.scheme_id
            ORDER BY
                CASE WHEN s.scope_type = 'global' THEN 0 ELSE 1 END,
                n.scheme_id ASC,
                n.id ASC
            """
        )
    ).fetchall()
    node_by_id = {int(row.id): row for row in node_rows}
    node_by_code: dict[str, sa.Row] = {}
    for row in node_rows:
        node_by_code.setdefault(row.node_code, row)

    def build_path(row) -> str:
        parts: list[str] = []
        current = row
        visited: set[int] = set()
        while current is not None and int(current.id) not in visited:
            visited.add(int(current.id))
            parts.append(current.node_name or "")
            current = node_by_id.get(int(current.parent_id)) if current.parent_id is not None else None
        return " > ".join(reversed([part for part in parts if part]))

    existing_rows = conn.execute(
        sa.text(
            """
            SELECT product_id, attribute_id
            FROM product_catalog_attribute_values
            WHERE attribute_id IN :attribute_ids
            """
        ).bindparams(sa.bindparam("attribute_ids", expanding=True)),
        {"attribute_ids": list(attribute_ids.values())},
    ).fetchall()
    existing = {(int(row.product_id), int(row.attribute_id)) for row in existing_rows}

    product_rows = conn.execute(
        sa.text(
            """
            SELECT
                id,
                vendor,
                name,
                product_type,
                category,
                classification_node_code
            FROM product_catalog
            ORDER BY id ASC
            """
        )
    ).fetchall()

    inserts: list[dict] = []
    for product in product_rows:
        node = node_by_code.get(product.classification_node_code) if product.classification_node_code else None
        path_label = build_path(node) if node is not None else ""
        text_blob = _normalize_text(
            product.vendor,
            product.name,
            product.product_type,
            product.category,
            product.classification_node_code,
            path_label,
            node.node_name if node else "",
            node.asset_type_key if node else "",
            node.asset_type_label if node else "",
        )
        imp_type = _infer_imp_type(product.product_type, node.asset_kind if node else None, product.classification_node_code)
        domain = _infer_domain(text_blob, product.classification_node_code, node.asset_type_key if node else None)
        product_family = _infer_product_family(text_blob, product.classification_node_code, domain)
        platform = _infer_platform(text_blob, product_family)

        inferred = {
            "domain": domain,
            "imp_type": imp_type,
            "product_family": product_family,
            "platform": platform,
        }
        for attribute_key, option_key in inferred.items():
            if option_key is None:
                continue
            attribute_id = attribute_ids[attribute_key]
            if (int(product.id), attribute_id) in existing:
                continue
            option_id = option_ids.get((attribute_key, option_key))
            if option_id is None and attribute_key == "product_family":
                option_id = option_ids.get((attribute_key, "generic"))
            if option_id is None:
                continue
            inserts.append(
                {
                    "product_id": int(product.id),
                    "attribute_id": attribute_id,
                    "option_id": option_id,
                    "raw_value": None,
                    "sort_order": 100,
                    "is_primary": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    if inserts:
        op.bulk_insert(
            sa.table(
                "product_catalog_attribute_values",
                sa.column("product_id", sa.Integer()),
                sa.column("attribute_id", sa.Integer()),
                sa.column("option_id", sa.Integer()),
                sa.column("raw_value", sa.String()),
                sa.column("sort_order", sa.Integer()),
                sa.column("is_primary", sa.Boolean()),
                sa.column("created_at", sa.DateTime()),
                sa.column("updated_at", sa.DateTime()),
            ),
            inserts,
        )


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")
