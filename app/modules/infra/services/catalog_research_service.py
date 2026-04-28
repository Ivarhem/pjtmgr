from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.models.hardware_spec import HardwareSpec
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.hardware_interface import HardwareInterfaceCreate
from app.modules.infra.schemas.hardware_spec import HardwareSpecCreate
from app.modules.infra.schemas.product_catalog import ProductCatalogCreate, ProductCatalogUpdate
from app.modules.infra.services.catalog_research_backend import run_catalog_research
from app.modules.infra.services.catalog_similarity_service import build_normalized_catalog_fields
from app.modules.infra.services.product_catalog_attribute_service import get_product_attributes
from app.modules.infra.services.product_catalog_service import (
    VERIFICATION_STATUS_UNVERIFIED,
    VERIFICATION_STATUS_PENDING_REVIEW,
    VERIFICATION_STATUS_SOURCE_FOUND,
    VERIFICATION_STATUS_VERIFIED,
    create_interface,
    create_product,
    delete_product,
    derive_catalog_family_fields,
    get_product,
    update_product,
    upsert_spec,
)

RESEARCH_PROVIDER = (
    (os.getenv("CATALOG_RESEARCH_PROVIDER") or "").strip().lower()
    or (os.getenv("CATALOG_RESEARCH_BACKEND") or "service").strip().lower()
)
DEFAULT_BATCH_LIMIT = int(os.getenv("CATALOG_RESEARCH_BATCH_LIMIT") or "5")

UNCERTAIN_MARKERS = {"", "unknown", "n/a", "na", "none", "null", "uncertain", "tbd"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_CAPACITY_TYPES = {"fixed", "base", "max"}
SPEC_FIELDS = [
    "size_unit",
    "width_mm",
    "height_mm",
    "depth_mm",
    "weight_kg",
    "power_count",
    "power_type",
    "power_watt",
    "power_summary",
    "cpu_summary",
    "memory_summary",
    "storage_summary",
    "os_firmware",
    "spec_url",
]

FAMILY_SKU_EXPANSION_RULES = {
    # Keep this list intentionally conservative: only expand line-up rows into
    # common concrete SKUs where the family naming is unambiguous.
    ("cisco", "C9300"): ["C9300-24T", "C9300-24P", "C9300-48T", "C9300-48P"],
    ("juniper", "EX4400"): ["EX4400-24T", "EX4400-24P", "EX4400-48T", "EX4400-48P", "EX4400-48F"],
    ("arista", "7050X3"): ["DCS-7050SX3-48YC8", "DCS-7050CX3-32S", "DCS-7050TX3-48C8"],
    ("aruba", "CX 6300"): ["JL658A", "JL659A", "JL661A", "JL662A", "JL663A", "JL664A", "JL665A", "JL666A"],
}


def _normalize_sku_model_name(family: str | None, detail_model: str | None) -> str | None:
    """Catalog naming rule for expanded SKUs: `{family} {detail_model}`.

    If the detail model already contains the family prefix (Cisco/Juniper-style
    SKUs such as C9300-24T or EX4400-48P), keep it as-is to avoid duplication.
    """
    family_text = (family or "").strip()
    detail_text = (detail_model or "").strip()
    if not detail_text:
        return None
    if not family_text:
        return detail_text
    family_key = re.sub(r"[^a-z0-9]+", "", family_text.lower())
    detail_key = re.sub(r"[^a-z0-9]+", "", detail_text.lower())
    if detail_key.startswith(family_key):
        return detail_text
    return f"{family_text} {detail_text}"


KNOWN_FAMILY_SPEC_OVERRIDES = {
    # Conservative physical form-factor/power defaults for expanded switch SKUs.
    ("cisco", "C9300"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("juniper", "EX4400"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("arista", "7050X3"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("aruba", "CX 6300"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
}

KNOWN_SKU_SPEC_OVERRIDES = {
    # Exact-model conservative defaults from vendor datasheet/service specs.
    # Power wattage varies by PSU option or configuration, so leave power_watt empty.
    ("aruba", "CX 6300 JL665A"): {"power_count": 1, "power_type": "AC"},
    ("aruba", "CX 6300 JL666A"): {"power_count": 1, "power_type": "AC"},
    ("a10 networks", "Thunder 1040S"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("axgate", "NF 600"): {"power_count": 2, "power_type": "AC", "cpu_summary": "5 Core", "memory_summary": "16 GB", "storage_summary": "System: SSD 250 GB; Log: 1 TB", "power_summary": "Dual power", "spec_url": "https://www.axgate.com/main/about/product/ngfw.php"},
    ("monitorapp", "AIWAF-500"): {"memory_summary": "16GB (Max 128GB)", "storage_summary": "HDD 500GB", "spec_url": "https://www.itls.co.kr/?page_id=793"},
    ("monitorapp", "AIWAF-1000"): {"memory_summary": "32GB (Max 2TB)", "storage_summary": "HDD 2TB", "spec_url": "https://www.itls.co.kr/?page_id=793"},
    ("monitorapp", "AIWAF-2000"): {"memory_summary": "32GB (Max 2TB)", "storage_summary": "HDD 2TB", "spec_url": "https://www.itls.co.kr/?page_id=793"},
    ("cisco", "Catalyst 8300"): {"power_count": 2, "power_type": "AC"},
    ("gigamon", "GigaVUE-HC3"): {"size_unit": 3, "power_count": 2, "power_type": "AC"},
    ("nutanix", "HCI NX-8155-G8"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "power_watt": 2000, "cpu_summary": "Dual Intel Xeon Scalable processor platform; exact CPU varies by configuration", "memory_summary": "Configurable DDR4 memory; exact capacity varies by configuration", "storage_summary": "Hybrid/HCI node storage varies by configuration"},
    ("aruba", "Mobility Controller 7200"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("cisco", "Nexus 5010"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("cisco", "Nexus 93180YC-FX3"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("cisco", "WLC 9800"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("dell", "PowerEdge R760"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Up to 2 x 4th Gen Intel Xeon Scalable processors", "memory_summary": "32 DDR5 DIMM slots", "storage_summary": "Supports 2.5-inch/3.5-inch SAS/SATA/NVMe drive configurations; exact drive count varies by chassis"},
    ("dell", "PowerEdge R760xa"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Up to 2 x 4th Gen Intel Xeon Scalable processors", "memory_summary": "32 DDR5 DIMM slots", "storage_summary": "Supports front-accessible SAS/SATA/NVMe drive configurations; exact drive count varies by chassis"},
    ("dell emc", "PowerStore 500T"): {"size_unit": 2, "power_count": 2, "power_type": "DC", "cpu_summary": "Dual active-active storage controllers", "memory_summary": "Memory/cache varies by PowerStore 500T configuration", "storage_summary": "PowerStore 500T supports NVMe flash expansion enclosures; capacity varies by drive configuration", "power_summary": "Redundant power supplies; AC/DC variant depends on model/configuration"},
    ("hpe", "Alletra 6070"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Dual-controller storage array", "memory_summary": "Controller cache/memory varies by configuration", "storage_summary": "All-flash array; raw/usable capacity varies by SSD configuration", "power_summary": "Redundant hot-plug power supplies; wattage varies by configuration"},
    ("check point", "Quantum 6200"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("cisco", "Catalyst 9120AXI"): {"power_count": 1, "power_type": "PoE/DC"},
    ("fortinet", "FortiSandbox 3000F"): {"size_unit": 2, "power_count": 2, "power_type": "AC"},
    ("juniper", "SRX4200"): {"size_unit": 1, "power_count": 2, "power_type": "AC/DC"},
    ("netapp", "AFF A400"): {"size_unit": 4, "power_count": 2, "power_type": "AC", "cpu_summary": "Dual-controller AFF A-Series storage system", "memory_summary": "Controller memory/cache varies by AFF A400 configuration", "storage_summary": "AFF A400 all-flash storage; drive count and capacity vary by shelf/SSD configuration", "power_summary": "Redundant hot-swappable power supplies; power draw varies by configuration"},
    ("netapp", "FAS2750"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Dual-controller FAS storage system", "memory_summary": "Controller memory/cache varies by configuration", "storage_summary": "FAS2750 supports internal drives plus expansion shelves; HDD/SSD capacity varies by configuration", "power_summary": "Redundant hot-swappable power supplies; power draw varies by configuration"},
    ("nvidia", "DGX A100"): {"size_unit": 6, "power_count": 6, "power_type": "AC", "cpu_summary": "2 x AMD EPYC 7742 CPUs", "memory_summary": "1 TB system memory", "storage_summary": "15 TB Gen4 NVMe cache plus 30 TB NVMe internal storage"},
    ("pulse secure", "PSA 3000"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("sonicwall", "NSa 4700"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("f5", "BIG-IP i5800"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("fortinet", "FortiGate 200F"): {"size_unit": 1, "power_count": 1, "power_type": "AC"},
    ("hpe", "ProLiant DL380 Gen11"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Up to 2 x 4th/5th Gen Intel Xeon Scalable processors", "memory_summary": "32 DDR5 DIMM slots", "storage_summary": "Supports SFF/LFF SAS/SATA/NVMe drive configurations; exact drive count varies by chassis"},
    ("juniper", "MX204"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("lenovo", "ThinkSystem SR650 V3"): {"size_unit": 2, "power_count": 2, "power_type": "AC", "cpu_summary": "Up to 2 x 4th/5th Gen Intel Xeon Scalable processors", "memory_summary": "32 DDR5 DIMM slots", "storage_summary": "Supports 2.5-inch/3.5-inch SAS/SATA/NVMe drive configurations; exact drive count varies by chassis"},
    ("palo alto networks", "PA-3220"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("palo alto networks", "PA-3260"): {"size_unit": 1, "power_count": 2, "power_type": "AC"},
    ("synology", "FlashStation FS2500"): {"size_unit": 1, "power_count": 1, "power_type": "AC", "cpu_summary": "AMD Ryzen V1780B 4-core processor", "memory_summary": "8 GB DDR4 ECC SODIMM, expandable", "storage_summary": "12 x 2.5-inch SATA SSD bays", "power_summary": "Single internal power supply"},
}

KNOWN_SKU_INTERFACE_OVERRIDES = {
    # Cisco Catalyst 9300 fixed downlink families. Optional uplink modules vary,
    # so only fixed access ports are asserted here.
    ("monitorapp", "AIWAF-500"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 4, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Network default from ITLS AIWAF partner spec page"},
    ],
    ("monitorapp", "AIWAF-1000"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 4, "connector_type": "RJ-45", "capacity_type": "max", "note": "Optional slot module: 1G UTP 4PORT; channel partner spec page"},
        {"interface_type": "GE SFP", "speed": "1G", "count": 4, "connector_type": "SFP", "capacity_type": "max", "note": "Optional slot module: 1G Fiber 4PORT; channel partner spec page"},
        {"interface_type": "SFP+", "speed": "10G", "count": 4, "connector_type": "SFP+", "capacity_type": "max", "note": "Optional slot modules include 10G Fiber 2PORT/4PORT; channel partner spec page"},
        {"interface_type": "QSFP+", "speed": "40G", "count": 2, "connector_type": "QSFP+", "capacity_type": "max", "note": "Optional slot module: 40G Fiber 2PORT; channel partner spec page"},
    ],
    ("monitorapp", "AIWAF-2000"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 4, "connector_type": "RJ-45", "capacity_type": "max", "note": "Optional slot module: 1G UTP 4PORT; channel partner spec page"},
        {"interface_type": "GE SFP", "speed": "1G", "count": 4, "connector_type": "SFP", "capacity_type": "max", "note": "Optional slot module: 1G Fiber 4PORT; channel partner spec page"},
        {"interface_type": "SFP+", "speed": "10G", "count": 4, "connector_type": "SFP+", "capacity_type": "max", "note": "Optional slot modules include 10G Fiber 2PORT/4PORT; channel partner spec page"},
        {"interface_type": "QSFP+", "speed": "40G", "count": 2, "connector_type": "QSFP+", "capacity_type": "max", "note": "Optional slot module: 40G Fiber 2PORT; channel partner spec page"},
    ],
    ("axgate", "NF 600"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 8, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "1GC ports from AXGATE NGFW product table"},
        {"interface_type": "GE SFP", "speed": "1G", "count": 4, "connector_type": "SFP", "capacity_type": "fixed", "note": "1GF ports from AXGATE NGFW product table"},
        {"interface_type": "SFP+", "speed": "10G", "count": 4, "connector_type": "SFP+", "capacity_type": "fixed", "note": "10GF ports from AXGATE NGFW product table"},
    ],
    ("cisco", "C9300-24T"): [{"interface_type": "GE RJ45", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"}],
    ("cisco", "C9300-24P"): [{"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed PoE+ access ports"}],
    ("cisco", "C9300-48T"): [{"interface_type": "GE RJ45", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"}],
    ("cisco", "C9300-48P"): [{"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed PoE+ access ports"}],
    # Juniper EX4400 fixed access/downlink ports only; uplinks/modules can vary by SKU/configuration.
    ("juniper", "EX4400-24T"): [{"interface_type": "GE RJ45", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"}],
    ("juniper", "EX4400-24P"): [{"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed PoE+ access ports"}],
    ("juniper", "EX4400-48T"): [{"interface_type": "GE RJ45", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"}],
    ("juniper", "EX4400-48P"): [{"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed PoE+ access ports"}],
    ("juniper", "EX4400-48F"): [{"interface_type": "GE SFP", "speed": "1G", "count": 48, "connector_type": "SFP", "capacity_type": "fixed", "note": "Fixed fiber access ports"}],
    # Aruba CX 6300 fixed access/uplink ports.
    ("aruba", "CX 6300 JL658A"): [
        {"interface_type": "SFP+", "speed": "10G", "count": 24, "connector_type": "SFP+", "capacity_type": "fixed", "note": "Fixed front-panel ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL659A"): [
        {"interface_type": "Smart Rate RJ45 PoE", "speed": "1/2.5/5G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed Class 6 PoE ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL661A"): [
        {"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed Class 4 PoE ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL662A"): [
        {"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed Class 4 PoE ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL663A"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL664A"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed access ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL665A"): [
        {"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed Class 4 PoE ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("aruba", "CX 6300 JL666A"): [
        {"interface_type": "GE RJ45 PoE+", "speed": "1G", "count": 24, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed Class 4 PoE ports"},
        {"interface_type": "SFP56", "speed": "50G", "count": 4, "connector_type": "SFP56", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    # Additional exact-model fixed port layouts where base ports are stable.
    ("cisco", "Nexus 5010"): [
        {"interface_type": "SFP+", "speed": "10G", "count": 20, "connector_type": "SFP+", "capacity_type": "fixed", "note": "Fixed ports; expansion module bays excluded"},
    ],
    ("cisco", "Nexus 93180YC-FX3"): [
        {"interface_type": "SFP28", "speed": "1/10/25G", "count": 48, "connector_type": "SFP28", "capacity_type": "fixed", "note": "Fixed front-panel ports"},
        {"interface_type": "QSFP28", "speed": "40/100G", "count": 6, "connector_type": "QSFP28", "capacity_type": "fixed", "note": "Fixed uplink ports"},
    ],
    ("juniper", "MX204"): [
        {"interface_type": "QSFP28", "speed": "100G", "count": 4, "connector_type": "QSFP28", "capacity_type": "fixed", "note": "Fixed front-panel ports"},
        {"interface_type": "QSFP+", "speed": "40G", "count": 8, "connector_type": "QSFP+", "capacity_type": "fixed", "note": "Fixed front-panel ports"},
        {"interface_type": "SFP+", "speed": "10G", "count": 4, "connector_type": "SFP+", "capacity_type": "fixed", "note": "Fixed front-panel ports"},
    ],
    ("fortinet", "FortiGate 200F"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 18, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Fixed RJ45 ports"},
        {"interface_type": "SFP", "speed": "1G", "count": 8, "connector_type": "SFP", "capacity_type": "fixed", "note": "Fixed SFP ports"},
        {"interface_type": "SFP+", "speed": "10G", "count": 4, "connector_type": "SFP+", "capacity_type": "fixed", "note": "Fixed SFP+ ports"},
    ],
    ("f5", "BIG-IP i5800"): [
        {"interface_type": "SFP+", "speed": "10G", "count": 8, "connector_type": "SFP+", "capacity_type": "fixed", "note": "Fixed network interfaces"},
        {"interface_type": "RJ45 Mgmt", "speed": "1G", "count": 1, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Management port"},
    ],
    ("a10 networks", "Thunder 1040S"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 4, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Base appliance ports"},
    ],
    ("check point", "Quantum 6200"): [
        {"interface_type": "GE RJ45", "speed": "1G", "count": 10, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Base configuration copper ports"},
    ],
    ("cisco", "Catalyst 9120AXI"): [
        {"interface_type": "mGig RJ45", "speed": "100M/1G/2.5G", "count": 1, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Ethernet uplink / PoE input"},
    ],
    ("nvidia", "DGX A100"): [
        {"interface_type": "InfiniBand/Ethernet", "speed": "200G", "count": 8, "connector_type": "QSFP56", "capacity_type": "config", "note": "Factory networking configuration varies; conservative base count"},
        {"interface_type": "Ethernet", "speed": "10/25G", "count": 2, "connector_type": "SFP28", "capacity_type": "fixed", "note": "System networking ports"},
    ],
    # Arista 7050X3 fixed front-panel ports.
    ("arista", "7050X3 DCS-7050SX3-48YC8"): [
        {"interface_type": "SFP", "speed": "10/25G", "count": 48, "connector_type": "SFP28", "capacity_type": "fixed", "note": "Front-panel ports"},
        {"interface_type": "QSFP", "speed": "40/100G", "count": 8, "connector_type": "QSFP100", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
    ("arista", "7050X3 DCS-7050CX3-32S"): [{"interface_type": "QSFP", "speed": "40/100G", "count": 32, "connector_type": "QSFP100", "capacity_type": "fixed", "note": "Front-panel ports"}],
    ("arista", "7050X3 DCS-7050TX3-48C8"): [
        {"interface_type": "10GE RJ45", "speed": "10G", "count": 48, "connector_type": "RJ-45", "capacity_type": "fixed", "note": "Front-panel ports"},
        {"interface_type": "QSFP", "speed": "40/100G", "count": 8, "connector_type": "QSFP100", "capacity_type": "fixed", "note": "Uplink ports"},
    ],
}


def _known_family_spec_overrides(product: ProductCatalog) -> dict:
    vendor_key = (product.vendor or "").strip().lower()
    family = (product.model_family or "").strip().upper()
    name_key = (product.name or "").strip().upper()
    overrides = dict(KNOWN_FAMILY_SPEC_OVERRIDES.get((vendor_key, family), {}))
    sku_lookup = {(vendor, name.upper()): data for (vendor, name), data in KNOWN_SKU_SPEC_OVERRIDES.items()}
    overrides.update(sku_lookup.get((vendor_key, name_key), {}))
    # Rack-unit height is deterministic enough to use as a derived physical height.
    # Store rounded millimetres (1U = 44.45mm) only when no exact height override exists.
    if overrides.get("size_unit") is not None and overrides.get("height_mm") is None:
        try:
            overrides["height_mm"] = int(round(float(overrides["size_unit"]) * 44.45))
        except Exception:
            pass
    return overrides


def _known_sku_interface_overrides(product: ProductCatalog) -> list[dict]:
    vendor_key = (product.vendor or "").strip().lower()
    name_key = (product.name or "").strip().upper()
    lookup = {(vendor, name.upper()): items for (vendor, name), items in KNOWN_SKU_INTERFACE_OVERRIDES.items()}
    return [dict(item) for item in lookup.get((vendor_key, name_key), [])]

def _clean_text(value, max_len: int | None = None):
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in UNCERTAIN_MARKERS:
        return None
    if max_len and len(text) > max_len:
        return text[:max_len]
    return text or None


def _clean_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text in UNCERTAIN_MARKERS:
        return None
    if text.endswith("u"):
        text = text[:-1]
    m = re.search(r"-?\d+", text)
    return int(m.group()) if m else None


def _clean_float(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in UNCERTAIN_MARKERS:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _clean_date(value):
    text = _clean_text(value, 32)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _merge_value(current, new, *, fill_only: bool):
    if new is None:
        return current
    if fill_only:
        if current is None:
            return new
        if isinstance(current, str) and not current.strip():
            return new
        return current
    return new


def _normalize_confidence(value) -> str:
    text = (_clean_text(value, 20) or "low").lower()
    return text if text in VALID_CONFIDENCE else "low"


def _normalize_capacity_type(value) -> str:
    text = (_clean_text(value, 10) or "fixed").lower()
    aliases = {"default": "base", "onboard": "fixed", "built-in": "fixed", "optional": "max"}
    text = aliases.get(text, text)
    return text if text in VALID_CAPACITY_TYPES else "fixed"


def _normalize_interfaces(items: list[dict]) -> tuple[list[dict], int]:
    merged: dict[tuple, dict] = {}
    skipped = 0
    for item in items or []:
        interface_type = _clean_text(item.get("interface_type"), 30)
        count = _clean_int(item.get("count"))
        if not interface_type or not count or count <= 0:
            skipped += 1
            continue
        row = {
            "interface_type": interface_type,
            "speed": _clean_text(item.get("speed"), 20),
            "count": count,
            "connector_type": _clean_text(item.get("connector_type"), 30),
            "capacity_type": _normalize_capacity_type(item.get("capacity_type")),
            "note": _clean_text(item.get("note"), 255),
        }
        key = (row["interface_type"], row["speed"], row["connector_type"], row["capacity_type"], row["note"])
        if key in merged:
            merged[key]["count"] += row["count"]
        else:
            merged[key] = row
    normalized = sorted(merged.values(), key=lambda x: (x["capacity_type"], x["interface_type"], x.get("speed") or "", x.get("connector_type") or ""))
    return normalized, skipped


def _count_non_null(mapping: dict, fields: list[str]) -> int:
    return sum(1 for field in fields if mapping.get(field) is not None)


def _interface_attr(item, name: str):
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _interface_signature(item) -> tuple:
    return (
        _clean_text(_interface_attr(item, "interface_type"), 30),
        _clean_text(_interface_attr(item, "speed"), 20),
        _clean_int(_interface_attr(item, "count")),
        _clean_text(_interface_attr(item, "connector_type"), 30),
        _normalize_capacity_type(_interface_attr(item, "capacity_type")),
    )


def _looks_legacy_interface_label(item) -> bool:
    interface_type = (_clean_text(_interface_attr(item, "interface_type"), 30) or "").lower()
    connector_type = (_clean_text(_interface_attr(item, "connector_type"), 30) or "").lower()
    speed = (_clean_text(_interface_attr(item, "speed"), 20) or "").lower()
    if not interface_type:
        return True
    if "usb" in interface_type:
        return True
    if interface_type in {"management", "management ethernet", "management rj45"} and not connector_type:
        return True
    if interface_type == "console" and not connector_type:
        return True
    if "port" in interface_type and not connector_type and not speed:
        return True
    return False


def _should_refresh_existing_interfaces(existing_interfaces: list[HardwareInterface], normalized_interfaces: list[dict]) -> bool:
    if not existing_interfaces or not normalized_interfaces:
        return False
    if any(_looks_legacy_interface_label(item) for item in existing_interfaces):
        return True
    existing_keys = {_interface_signature(item) for item in existing_interfaces}
    normalized_keys = {_interface_signature(item) for item in normalized_interfaces}
    return not normalized_keys.issubset(existing_keys)


def _spec_field_count(spec: HardwareSpec | None) -> int:
    if spec is None:
        return 0
    return sum(1 for field in SPEC_FIELDS if getattr(spec, field, None) not in (None, ""))


def _eosl_field_count(product) -> int:
    return sum(1 for value in [product.eos_date, product.eosl_date, product.eosl_note] if value not in (None, ""))


def should_skip_catalog_research(product, spec: HardwareSpec | None, interface_count: int, *, force: bool = False) -> tuple[bool, str | None]:
    if force:
        return False, None
    if getattr(product, "is_placeholder", False) or (product.vendor or "").strip() in {"—", "-"}:
        return True, "placeholder_product"

    spec_count = _spec_field_count(spec)
    eosl_count = _eosl_field_count(product)
    verification_status = (product.verification_status or "").strip().lower()
    source_name = (product.source_name or "").strip().lower()

    if verification_status == VERIFICATION_STATUS_VERIFIED and spec_count >= 6 and (eosl_count >= 2 or interface_count > 0):
        return True, "already_verified"

    if source_name in {"catalog_research", "spec_import", "manual"} and spec_count >= 9 and eosl_count >= 2 and interface_count > 0:
        return True, "already_enriched"

    if source_name == "catalog_research" and verification_status == VERIFICATION_STATUS_PENDING_REVIEW:
        has_spec_url = bool(getattr(spec, "spec_url", None))
        if spec_count >= 2 and has_spec_url and interface_count > 0:
            return True, "awaiting_review"

    return False, None

def _build_family_sku_candidates(db: Session, product: ProductCatalog) -> tuple[str | None, list[str]]:
    if product.product_type != "hardware":
        return None, []
    vendor_key = (product.vendor or "").strip().lower()
    derived = derive_catalog_family_fields(
        product.vendor,
        product.name,
        product.product_type,
        product.model_family,
        None,
    )
    family = (derived.get("model_family") or product.model_family or product.name or "").strip().upper() or None
    is_family_level = bool(derived.get("is_family_level") or product.is_family_level)
    if not family:
        return None, []
    if not (is_family_level or family == (product.name or "").strip().upper()):
        return family, []

    rule_details = FAMILY_SKU_EXPANSION_RULES.get((vendor_key, family), [])
    if not rule_details:
        return family, []

    existing_names = {
        (name or "").strip().upper()
        for name in db.scalars(
            select(ProductCatalog.name).where(ProductCatalog.vendor == product.vendor)
        )
    }
    candidates = []
    for detail in rule_details:
        candidate = _normalize_sku_model_name(family, detail)
        if candidate and candidate.upper() not in existing_names:
            candidates.append(candidate)
    return family, candidates


def preview_product_sku_expansion(db: Session, product_id: int) -> dict:
    product = get_product(db, product_id)
    family, candidates = _build_family_sku_candidates(db, product)
    message = "확장 가능한 SKU 후보가 없습니다."
    if candidates:
        message = f"{product.name} 패밀리에서 SKU 후보 {len(candidates)}건을 제안합니다."
    return {
        "product_id": product.id,
        "vendor": product.vendor,
        "name": product.name,
        "model_family": family,
        "is_family_level": bool(product.is_family_level),
        "candidates": candidates,
        "delete_family_default": True,
        "message": message,
    }


def apply_product_sku_expansion(db: Session, product_id: int, current_user: User, *, selected_names: list[str] | None = None, delete_family_after_expand: bool = True) -> dict:
    product = get_product(db, product_id)
    family, candidates = _build_family_sku_candidates(db, product)
    if not candidates:
        return {
            "product_id": product.id,
            "vendor": product.vendor,
            "name": product.name,
            "model_family": family,
            "created": 0,
            "created_products": [],
            "skipped_existing": [],
            "deleted_family": False,
            "message": "확장 가능한 SKU 후보가 없습니다.",
        }

    candidate_map = {name.upper(): name for name in candidates}
    requested = selected_names or candidates
    selected = []
    for raw in requested:
        cleaned = (raw or "").strip().upper()
        if cleaned and cleaned in candidate_map and candidate_map[cleaned] not in selected:
            selected.append(candidate_map[cleaned])

    if not selected:
        return {
            "product_id": product.id,
            "vendor": product.vendor,
            "name": product.name,
            "model_family": family,
            "created": 0,
            "created_products": [],
            "skipped_existing": [],
            "deleted_family": False,
            "message": "선택된 SKU 후보가 없습니다.",
        }

    attribute_payload = [
        {
            "attribute_key": item.get("attribute_key"),
            "option_key": item.get("option_key"),
            "raw_value": item.get("raw_value"),
        }
        for item in get_product_attributes(db, product.id)
        if item.get("attribute_key")
    ]

    created_products = []
    skipped_existing = []
    for sku_name in selected:
        existing = db.scalar(
            select(ProductCatalog).where(
                ProductCatalog.vendor == product.vendor,
                ProductCatalog.name == sku_name,
            )
        )
        if existing is not None:
            skipped_existing.append(sku_name)
            continue
        payload = ProductCatalogCreate(
            vendor=product.vendor,
            name=sku_name,
            product_type=product.product_type,
            version=product.version,
            reference_url=product.reference_url,
            source_name="family_expansion",
            source_url=product.source_url,
            source_confidence=product.source_confidence,
            model_family=family,
            is_family_level=False,
            attributes=attribute_payload or None,
            default_license_type=product.default_license_type,
            default_license_unit=product.default_license_unit,
        )
        try:
            created = create_product(db, payload, current_user)
            created_products.append({
                "id": created["id"],
                "vendor": created["vendor"],
                "name": created["name"],
            })
        except Exception:
            db.rollback()
            partial = db.scalar(
                select(ProductCatalog).where(
                    ProductCatalog.vendor == product.vendor,
                    ProductCatalog.name == sku_name,
                )
            )
            if partial is not None:
                created_products.append({
                    "id": partial.id,
                    "vendor": partial.vendor,
                    "name": partial.name,
                })
                continue
            normalized = build_normalized_catalog_fields(product.vendor, sku_name)
            fallback = ProductCatalog(
                vendor=product.vendor,
                name=sku_name,
                product_type=product.product_type,
                version=product.version,
                reference_url=product.reference_url,
                source_name="family_expansion",
                source_url=product.source_url,
                source_confidence=product.source_confidence,
                model_family=family,
                is_family_level=False,
                normalized_vendor=normalized["normalized_vendor"],
                normalized_name=normalized["normalized_name"],
                default_license_type=product.default_license_type,
                default_license_unit=product.default_license_unit,
            )
            db.add(fallback)
            db.commit()
            db.refresh(fallback)
            created_products.append({
                "id": fallback.id,
                "vendor": fallback.vendor,
                "name": fallback.name,
            })

    deleted_family = False
    message = f"SKU {len(created_products)}건을 생성했습니다."
    if delete_family_after_expand and created_products:
        try:
            delete_product(db, product.id, current_user)
            deleted_family = True
            message = f"SKU {len(created_products)}건 생성 후 패밀리 엔트리를 삭제했습니다."
        except Exception as exc:
            message = f"SKU {len(created_products)}건 생성했지만 패밀리 엔트리 삭제는 보류되었습니다: {exc}"

    return {
        "product_id": product.id,
        "vendor": product.vendor,
        "name": product.name,
        "model_family": family,
        "created": len(created_products),
        "created_products": created_products,
        "skipped_existing": skipped_existing,
        "deleted_family": deleted_family,
        "message": message,
    }




def _research_quality_status(
    *,
    spec_applied: int,
    spec_candidates: int,
    eosl_applied: int,
    eosl_candidates: int,
    interface_candidates: int,
    meaningful_spec_count: int,
    has_spec_url: bool,
    has_lifecycle_date: bool,
    has_source_url: bool,
) -> tuple[bool, str]:
    """Return (has_meaningful_research, verification_status).

    URLs alone are useful, but not enough for pending review. They become
    source_found so background automation can continue enriching later without
    flooding review queues with shallow rows.
    """
    strong_spec = meaningful_spec_count >= 3 and has_spec_url
    strong_lifecycle = bool(has_lifecycle_date and has_source_url)
    strong_interfaces = interface_candidates > 0 and (spec_applied > 0 or spec_candidates > 0 or has_spec_url)
    if strong_spec or strong_lifecycle or strong_interfaces:
        return True, VERIFICATION_STATUS_PENDING_REVIEW
    if has_spec_url or has_source_url or spec_applied > 0 or spec_candidates > 0 or eosl_applied > 0 or eosl_candidates > 0:
        return True, VERIFICATION_STATUS_SOURCE_FOUND
    return False, VERIFICATION_STATUS_UNVERIFIED

def _classification_label(product) -> str:
    parts = []
    for attr in [
        getattr(product, "classification_level_1_name", None),
        getattr(product, "classification_level_2_name", None),
        getattr(product, "classification_level_3_name", None),
        getattr(product, "classification_level_4_name", None),
        getattr(product, "classification_level_5_name", None),
    ]:
        if attr:
            parts.append(attr)
    return " > ".join(parts) if parts else "unclassified"


def research_catalog_product(db: Session, product_id: int, current_user: User, fill_only: bool = True, force: bool = False, expand_created_skus: bool = True) -> dict:
    product = get_product(db, product_id)
    if product.product_type != "hardware":
        raise BusinessRuleError("현재 카탈로그 조사는 하드웨어 제품만 지원합니다.", status_code=409)

    existing_spec = db.scalar(select(HardwareSpec).where(HardwareSpec.product_id == product_id))
    existing_interfaces = list(db.scalars(select(HardwareInterface).where(HardwareInterface.product_id == product_id).order_by(HardwareInterface.id.asc())))
    skip, skip_reason = should_skip_catalog_research(product, existing_spec, len(existing_interfaces), force=force)
    if skip:
        return {
            "product_id": product.id,
            "vendor": product.vendor,
            "name": product.name,
            "mode": "fill_empty" if fill_only else "replace_all",
            "confidence": product.source_confidence,
            "spec_candidates": 0,
            "spec_applied": 0,
            "eosl_candidates": 0,
            "eosl_applied": 0,
            "interfaces_created": 0,
            "interface_candidates": 0,
            "interfaces_skipped": 0,
            "uncertain_fields": [],
            "eos_date": product.eos_date,
            "eosl_date": product.eosl_date,
            "spec_url": getattr(existing_spec, "spec_url", None),
            "message": "재조사를 건너뛰었습니다.",
            "skipped": True,
            "skip_reason": skip_reason,
        }

    payload = run_catalog_research({
        "vendor": product.vendor,
        "name": product.name,
        "reference_url": product.reference_url or "none",
        "classification": _classification_label(product),
        "size_unit": getattr(existing_spec, "size_unit", None),
        "power_count": getattr(existing_spec, "power_count", None),
        "power_type": getattr(existing_spec, "power_type", None),
        "power_watt": getattr(existing_spec, "power_watt", None),
    })

    spec_data = payload.get("hardware_spec") or {}
    eosl_data = payload.get("eosl") or {}
    normalized_interfaces, invalid_interfaces = _normalize_interfaces(payload.get("interfaces") or [])
    known_interfaces = _known_sku_interface_overrides(product)
    if known_interfaces:
        existing_signatures = {_interface_signature(item) for item in normalized_interfaces}
        for item in known_interfaces:
            if _interface_signature(item) not in existing_signatures:
                normalized_interfaces.append(item)
    confidence = _normalize_confidence(payload.get("confidence"))
    uncertain_fields = [
        _clean_text(item, 40) for item in (payload.get("uncertain_fields") or [])
        if _clean_text(item, 40)
    ]

    fallback_source_url = product.source_url or product.reference_url
    known_overrides = _known_family_spec_overrides(product)
    spec_payload = {
        "size_unit": _merge_value(existing_spec.size_unit if existing_spec else None, _clean_int(spec_data.get("size_unit")) or known_overrides.get("size_unit"), fill_only=fill_only),
        "width_mm": _merge_value(existing_spec.width_mm if existing_spec else None, _clean_int(spec_data.get("width_mm")) or known_overrides.get("width_mm"), fill_only=fill_only),
        "height_mm": _merge_value(existing_spec.height_mm if existing_spec else None, _clean_int(spec_data.get("height_mm")) or known_overrides.get("height_mm"), fill_only=fill_only),
        "depth_mm": _merge_value(existing_spec.depth_mm if existing_spec else None, _clean_int(spec_data.get("depth_mm")) or known_overrides.get("depth_mm"), fill_only=fill_only),
        "weight_kg": _merge_value(existing_spec.weight_kg if existing_spec else None, _clean_float(spec_data.get("weight_kg")) or known_overrides.get("weight_kg"), fill_only=fill_only),
        "power_count": _merge_value(existing_spec.power_count if existing_spec else None, _clean_int(spec_data.get("power_count")) or known_overrides.get("power_count"), fill_only=fill_only),
        "power_type": _merge_value(existing_spec.power_type if existing_spec else None, _clean_text(spec_data.get("power_type"), 50) or known_overrides.get("power_type"), fill_only=fill_only),
        "power_watt": _merge_value(existing_spec.power_watt if existing_spec else None, _clean_int(spec_data.get("power_watt")) or known_overrides.get("power_watt"), fill_only=fill_only),
        "power_summary": _merge_value(existing_spec.power_summary if existing_spec else None, _clean_text(spec_data.get("power_summary")) or known_overrides.get("power_summary"), fill_only=fill_only),
        "cpu_summary": _merge_value(existing_spec.cpu_summary if existing_spec else None, _clean_text(spec_data.get("cpu_summary")) or known_overrides.get("cpu_summary"), fill_only=fill_only),
        "memory_summary": _merge_value(existing_spec.memory_summary if existing_spec else None, _clean_text(spec_data.get("memory_summary")) or known_overrides.get("memory_summary"), fill_only=fill_only),
        "storage_summary": _merge_value(existing_spec.storage_summary if existing_spec else None, _clean_text(spec_data.get("storage_summary")) or known_overrides.get("storage_summary"), fill_only=fill_only),
        "os_firmware": _merge_value(existing_spec.os_firmware if existing_spec else None, _clean_text(spec_data.get("os_firmware")) or known_overrides.get("os_firmware"), fill_only=fill_only),
        "spec_url": _merge_value(existing_spec.spec_url if existing_spec else None, _clean_text(spec_data.get("spec_url"), 500) or _clean_text(fallback_source_url, 500), fill_only=fill_only),
    }
    spec_candidates = _count_non_null({field: spec_payload.get(field) if spec_payload.get(field) != getattr(existing_spec, field, None) or not fill_only else _clean_text(spec_data.get(field), 500) if field in {"power_type", "power_summary", "cpu_summary", "memory_summary", "storage_summary", "os_firmware", "spec_url"} else None for field in SPEC_FIELDS}, SPEC_FIELDS)
    spec_applied = sum(1 for field in SPEC_FIELDS if spec_payload.get(field) != getattr(existing_spec, field, None))
    upsert_spec(db, product_id, HardwareSpecCreate(**spec_payload), current_user)

    new_eos = _clean_date(eosl_data.get("eos_date"))
    new_eosl = _clean_date(eosl_data.get("eosl_date"))
    new_note = _clean_text(eosl_data.get("eosl_note"))
    new_source_url = _clean_text(eosl_data.get("source_url"), 500) or _clean_text(spec_data.get("spec_url"), 500)
    if new_eos and new_eosl and new_eosl < new_eos:
        new_eosl = None
        if "eosl_date" not in uncertain_fields:
            uncertain_fields.append("eosl_date")
    eosl_candidates = sum(1 for value in [new_eos, new_eosl, new_note, new_source_url] if value is not None)
    meaningful_spec_count = sum(1 for field in SPEC_FIELDS if spec_payload.get(field) is not None)
    has_lifecycle_date = bool(new_eos or new_eosl)
    has_spec_url = bool(spec_payload.get("spec_url"))
    has_source_url = bool(new_source_url or product.source_url)
    has_meaningful_research, next_verification_status = _research_quality_status(
        spec_applied=spec_applied,
        spec_candidates=spec_candidates,
        eosl_applied=0,
        eosl_candidates=eosl_candidates,
        interface_candidates=len(normalized_interfaces),
        meaningful_spec_count=meaningful_spec_count,
        has_spec_url=has_spec_url,
        has_lifecycle_date=has_lifecycle_date,
        has_source_url=has_source_url,
    )
    product_update = ProductCatalogUpdate(
        eos_date=_merge_value(product.eos_date, new_eos, fill_only=fill_only),
        eosl_date=_merge_value(product.eosl_date, new_eosl, fill_only=fill_only),
        eosl_note=_merge_value(product.eosl_note, new_note, fill_only=fill_only),
        reference_url=_merge_value(product.reference_url, _clean_text(spec_data.get("spec_url"), 500), fill_only=fill_only),
        source_name="catalog_research" if has_meaningful_research else product.source_name,
        source_url=_merge_value(product.source_url, new_source_url, fill_only=fill_only) if has_meaningful_research else product.source_url,
        source_confidence=confidence if has_meaningful_research else product.source_confidence,
        researched_at=datetime.now(timezone.utc).replace(tzinfo=None) if has_meaningful_research else product.researched_at,
        research_provider=RESEARCH_PROVIDER if has_meaningful_research else product.research_provider,
        verification_status=next_verification_status if has_meaningful_research else VERIFICATION_STATUS_UNVERIFIED,
        last_verified_at=None,
    )
    eosl_applied = sum(
        1 for old, new in [
            (product.eos_date, product_update.eos_date),
            (product.eosl_date, product_update.eosl_date),
            (product.eosl_note, product_update.eosl_note),
            (product.source_url, product_update.source_url),
        ]
        if new != old
    )
    update_product(db, product_id, product_update, current_user)

    interfaces_created = 0
    interfaces_skipped = invalid_interfaces
    should_refresh_interfaces = _should_refresh_existing_interfaces(existing_interfaces, normalized_interfaces)
    should_replace_interfaces = bool(normalized_interfaces) and existing_interfaces and (not fill_only or should_refresh_interfaces)
    should_create_interfaces = bool(normalized_interfaces) and (not existing_interfaces or should_replace_interfaces)
    if should_create_interfaces:
        if should_replace_interfaces:
            db.execute(delete(HardwareInterface).where(HardwareInterface.product_id == product_id))
            existing_interfaces = []
        for item in normalized_interfaces:
            create_interface(db, product_id, HardwareInterfaceCreate(**item), current_user)
            interfaces_created += 1
    elif normalized_interfaces and existing_interfaces:
        interfaces_skipped += len(normalized_interfaces)

    if spec_applied == 0 and eosl_applied == 0 and interfaces_created == 0 and not uncertain_fields:
        uncertain_fields.append("pending_review")

    audit.log(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="product_catalog",
        entity_id=product_id,
        summary=f"카탈로그 조사 적용: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()

    # 자동 SKU 확장: 조사 대상이 라인업/패밀리 row이면 보수적 rule 기반
    # 대표 SKU를 즉시 생성하고, 확장 성공 시 모델계열 row는 제거한다.
    sku_expansion_result = apply_product_sku_expansion(
        db,
        product_id,
        current_user,
        delete_family_after_expand=True,
    )
    sku_expansion_created = sku_expansion_result.get("created", 0)
    sku_expansion_candidates = [
        item.get("name")
        for item in sku_expansion_result.get("created_products", [])
        if item.get("name")
    ]
    sku_research_results = []
    if expand_created_skus and sku_expansion_result.get("created_products"):
        for created_product in sku_expansion_result.get("created_products", []):
            created_id = created_product.get("id")
            if not created_id:
                continue
            try:
                child_result = research_catalog_product(
                    db,
                    created_id,
                    current_user,
                    fill_only=fill_only,
                    force=force,
                    expand_created_skus=False,
                )
                sku_research_results.append({
                    "id": created_id,
                    "name": created_product.get("name"),
                    "skipped": child_result.get("skipped", False),
                    "spec_applied": child_result.get("spec_applied", 0),
                    "eosl_applied": child_result.get("eosl_applied", 0),
                    "interfaces_created": child_result.get("interfaces_created", 0),
                    "spec_url": child_result.get("spec_url"),
                })
            except Exception as exc:
                db.rollback()
                sku_research_results.append({
                    "id": created_id,
                    "name": created_product.get("name"),
                    "error": str(exc),
                })

    return {
        "product_id": product_id,
        "vendor": product.vendor,
        "name": product.name,
        "mode": "fill_empty" if fill_only else "replace_all",
        "confidence": confidence,
        "spec_candidates": spec_candidates,
        "spec_applied": spec_applied,
        "eosl_candidates": eosl_candidates,
        "eosl_applied": eosl_applied,
        "interfaces_created": interfaces_created,
        "interface_candidates": len(normalized_interfaces),
        "interfaces_skipped": interfaces_skipped,
        "uncertain_fields": uncertain_fields,
        "eos_date": product_update.eos_date,
        "eosl_date": product_update.eosl_date,
        "spec_url": spec_payload.get("spec_url"),
        "message": "카탈로그 조사 결과를 반영했습니다." if not sku_expansion_created else f"카탈로그 조사 결과를 반영하고 대표 SKU {sku_expansion_created}건을 자동 생성했습니다.",
        "sku_expansion_candidates": sku_expansion_candidates,
        "sku_expansion_created": sku_expansion_created,
        "sku_research_results": sku_research_results,
        "skipped": False,
        "skip_reason": None,
    }


def batch_research_catalog_products(
    db: Session,
    current_user: User,
    *,
    limit: int | None = None,
    fill_only: bool = True,
    force: bool = False,
    include_pending_review: bool = False,
) -> dict:
    target_limit = max(1, min(int(limit or DEFAULT_BATCH_LIMIT), 20))
    statuses = [VERIFICATION_STATUS_UNVERIFIED, VERIFICATION_STATUS_SOURCE_FOUND]
    if include_pending_review:
        statuses.append(VERIFICATION_STATUS_PENDING_REVIEW)

    stmt = (
        select(ProductCatalog.id)
        .where(ProductCatalog.product_type == "hardware")
        .where(ProductCatalog.is_placeholder.is_(False))
        .where(ProductCatalog.verification_status.in_(statuses))
        .order_by(ProductCatalog.researched_at.asc().nullsfirst(), ProductCatalog.updated_at.asc(), ProductCatalog.id.asc())
        .limit(target_limit)
    )
    product_ids = list(db.scalars(stmt))

    rows: list[dict] = []
    success = 0
    skipped = 0
    failed = 0
    for product_id in product_ids:
        try:
            result = research_catalog_product(
                db,
                product_id=product_id,
                current_user=current_user,
                fill_only=fill_only,
                force=force,
                expand_created_skus=True,
            )
            rows.append(result)
            if result.get("skipped"):
                skipped += 1
            else:
                success += 1
        except Exception as exc:
            db.rollback()
            product = get_product(db, product_id)
            rows.append(
                {
                    "product_id": product.id,
                    "vendor": product.vendor,
                    "name": product.name,
                    "mode": "fill_empty" if fill_only else "replace_all",
                    "confidence": None,
                    "spec_candidates": 0,
                    "spec_applied": 0,
                    "eosl_candidates": 0,
                    "eosl_applied": 0,
                    "interfaces_created": 0,
                    "interface_candidates": 0,
                    "interfaces_skipped": 0,
                    "uncertain_fields": [],
                    "eos_date": product.eos_date,
                    "eosl_date": product.eosl_date,
                    "spec_url": None,
                    "message": str(exc),
                    "skipped": False,
                    "skip_reason": "error",
                    "status": "error",
                }
            )
            failed += 1

    return {
        "requested_limit": target_limit,
        "selected": len(product_ids),
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "rows": rows,
    }
