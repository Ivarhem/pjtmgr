"""주요 제조사별 대표 제품 라인업 시드."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import SessionLocal
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.catalog_similarity_service import normalize_vendor_name, normalize_product_name

# (vendor, name, product_type)
PRODUCTS = [
    # ── 네트워크 ──
    ("Cisco", "Catalyst 9300L", "hardware"),
    ("Cisco", "ASR 1001-X", "hardware"),
    ("Cisco", "Firepower 2100", "hardware"),
    ("Cisco", "Meraki MR46", "hardware"),
    ("Juniper", "SRX 340", "hardware"),
    ("Juniper", "EX4300", "hardware"),
    ("Juniper", "MX204", "hardware"),
    ("Arista", "7050X3", "hardware"),
    ("Arista", "CloudVision", "software"),
    ("Palo Alto Networks", "PA-440", "hardware"),
    ("Palo Alto Networks", "Prisma Access", "software"),
    ("Palo Alto Networks", "Cortex XDR", "software"),
    ("Fortinet", "FortiAnalyzer", "software"),
    ("Fortinet", "FortiManager", "software"),
    ("F5", "BIG-IP i2600", "hardware"),
    ("F5", "BIG-IP Virtual Edition", "software"),
    ("A10 Networks", "Thunder ADC", "hardware"),
    ("Nokia", "7750 SR", "hardware"),

    # ── 보안 ──
    ("Check Point", "Quantum 6200", "hardware"),
    ("Check Point", "CloudGuard", "software"),
    ("CrowdStrike", "Falcon Insight", "software"),
    ("SentinelOne", "Singularity XDR", "software"),
    ("Trellix", "Endpoint Security", "software"),
    ("Trellix", "Network Security", "hardware"),
    ("Sophos", "XGS Firewall", "hardware"),
    ("Sophos", "Intercept X", "software"),
    ("Trend Micro", "Deep Security", "software"),
    ("Trend Micro", "Vision One", "software"),
    ("Zscaler", "ZIA", "software"),
    ("Zscaler", "ZPA", "software"),
    ("Netskope", "CASB", "software"),
    ("SonicWall", "NSa 2700", "hardware"),
    ("Imperva", "WAF Gateway", "hardware"),
    ("AhnLab", "TrusGuard", "hardware"),
    ("AhnLab", "MDS", "hardware"),
    ("SECUI", "MF2 3000", "hardware"),
    ("SECUI", "BLUEMAX NGF", "hardware"),
    ("Genians", "Genian NAC", "software"),
    ("Genians", "Genian EDR", "software"),
    ("AXGATE", "AXGATE 80E", "hardware"),
    ("WINS", "Sniper IPS", "hardware"),
    ("IGLOO Security", "SPiDER TM", "software"),
    ("MONITORAPP", "AIWAF", "hardware"),
    ("PIOLINK", "WEBFRONT-K", "hardware"),
    ("PIOLINK", "PAS-K", "hardware"),

    ("Radware", "DefensePro", "hardware"),
    ("Gigamon", "GigaVUE HC1", "hardware"),
    ("Infoblox", "BloxOne DDI", "software"),
    ("WAREVALLEY", "Chakra Max", "software"),
    ("Tenable", "Nessus", "software"),
    ("Qualys", "VMDR", "software"),
    ("Tanium", "Tanium Core", "software"),
    ("SK Shieldus", "SecuCloudia", "software"),

    # ── 서버·스토리지 ──
    ("Dell", "PowerEdge R760", "hardware"),
    ("Dell", "PowerStore 500T", "hardware"),
    ("Dell", "PowerScale F900", "hardware"),
    ("HPE", "ProLiant DL380 Gen11", "hardware"),
    ("HPE", "Nimble Storage", "hardware"),
    ("HPE", "Aruba CX 6300", "hardware"),
    ("IBM", "Power S1022", "hardware"),
    ("IBM", "FlashSystem 5200", "hardware"),
    ("Lenovo", "ThinkSystem SR650 V3", "hardware"),
    ("Supermicro", "SuperServer 1U", "hardware"),
    ("NetApp", "AFF A250", "hardware"),
    ("Pure Storage", "FlashArray//X", "hardware"),
    ("Pure Storage", "FlashBlade//S", "hardware"),
    ("Nutanix", "NX-3060", "hardware"),
    ("Nutanix", "Prism Central", "software"),
    ("Synology", "SA3600", "hardware"),
    ("Huawei", "OceanStor 5300 V6", "hardware"),
    ("Huawei", "CloudEngine S5735", "hardware"),
    ("Samsung Electronics", "PM9A3 NVMe SSD", "hardware"),

    # ── 가상화·클라우드 ──
    ("VMware", "vSphere 8", "software"),
    ("VMware", "NSX 4", "software"),
    ("VMware", "vSAN 8", "software"),
    ("Citrix", "Virtual Apps and Desktops", "software"),
    ("Red Hat", "OpenShift", "software"),
    ("Red Hat", "Ansible Automation Platform", "software"),
    ("Red Hat", "Enterprise Linux 9", "software"),
    ("HashiCorp", "Terraform", "software"),
    ("HashiCorp", "Vault", "software"),
    ("Amazon", "EC2", "software"),
    ("Amazon", "S3", "software"),
    ("Amazon", "RDS", "software"),
    ("Google", "Compute Engine", "software"),
    ("Google", "BigQuery", "software"),
    ("Microsoft", "Azure Virtual Machines", "software"),
    ("Microsoft", "SQL Server 2022", "software"),
    ("Microsoft", "Windows Server 2022", "software"),
    ("Veeam", "Backup & Replication", "software"),
    ("Veritas", "NetBackup", "software"),
    ("Rubrik", "Cloud Data Management", "software"),

    # ── DB·미들웨어 ──
    ("Oracle", "Database 19c", "software"),
    ("Oracle", "WebLogic Server", "software"),
    ("TmaxSoft", "JEUS", "software"),
    ("SAP", "S/4HANA", "software"),
    ("SAP", "HANA DB", "software"),
    ("Elastic", "Elasticsearch", "software"),
    ("Splunk", "Enterprise", "software"),
    ("Cloudera", "CDP Private Cloud", "software"),
    ("MongoDB", "Atlas", "software"),
    ("Snowflake", "Data Cloud", "software"),
    ("Graylog", "Enterprise", "software"),

    # ── CDN·기타 ──
    ("Akamai", "Kona Site Defender", "software"),
    ("Akamai", "Ion", "software"),
    ("Cloudflare", "WAF", "software"),
    ("Cloudflare", "CDN", "software"),
    ("NVIDIA", "A100 GPU", "hardware"),
    ("NVIDIA", "H100 GPU", "hardware"),
    ("Intel", "Xeon Scalable 4th Gen", "hardware"),
    ("AMD", "EPYC 9004", "hardware"),
    ("Anthropic", "Claude", "software"),
    ("OpenAI", "GPT-4o", "software"),
]


def run():
    db = SessionLocal()
    try:
        added = 0
        skipped = 0
        for vendor, name, product_type in PRODUCTS:
            exists = db.scalar(
                select(ProductCatalog.id).where(
                    ProductCatalog.vendor == vendor,
                    ProductCatalog.name == name,
                )
            )
            if exists:
                skipped += 1
                continue
            nv = normalize_vendor_name(vendor)
            nn = normalize_product_name(name)
            db.add(ProductCatalog(
                vendor=vendor,
                name=name,
                product_type=product_type,
                normalized_vendor=nv,
                normalized_name=nn,
            ))
            added += 1
        db.commit()
        print(f"Done: {added} products added, {skipped} skipped (already exist)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
