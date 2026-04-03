"""분류 미지정 제품에 domain/imp_type/product_family 속성값 일괄 매핑."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import SessionLocal
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue

# attribute_id / option_id 맵 (DB에서 확인한 값)
ATTR_DOMAIN = 8
ATTR_IMP_TYPE = 9
ATTR_PRODUCT_FAMILY = 10

# domain option_ids
D_NET = 41; D_SEC = 42; D_SVR = 43; D_STO = 44; D_DB = 45; D_APP = 153

# imp_type option_ids
I_HW = 46; I_SW = 47; I_SVC = 48

# product_family option_ids (주요)
PF_FW = 49; PF_IPS = 50; PF_WAF = 51; PF_L2 = 53; PF_L3 = 54; PF_L4 = 55
PF_ROUTER = 86; PF_LB = 89; PF_WLAN = 161; PF_AP = 162; PF_PKT = 164
PF_SANDBOX = 165; PF_ANTI = 169; PF_DBA = 171; PF_X86 = 58; PF_UNIX = 59
PF_GPU = 174; PF_HYPER = 175; PF_VIRT = 106; PF_CONTAINER = 107; PF_OS = 63
PF_BACKUP_SW = 114; PF_LOG = 178; PF_AUTO = 179; PF_API_GW = 180
PF_WEB = 112; PF_MW = 65; PF_MON = 93; PF_GENERIC = 66; PF_DEVOPS = 119
PF_DBMS = None  # will look up
PF_DW = 185; PF_INMEM = 187; PF_DB_ENC = 186; PF_NOSQL = None
PF_CACHE = 115; PF_MQ = 116; PF_OBJ_STO = 110; PF_MAIL_SEC = 102
PF_THREAT = 170; PF_CFG = 176

# (vendor, name) → (domain_opt, imp_type_opt, family_opt)
CLASSIFICATIONS = {
    # ── Cisco ──
    ("Cisco", "ASR 1001-X"): (D_NET, I_HW, PF_ROUTER),
    ("Cisco", "Catalyst 9300L"): (D_NET, I_HW, PF_L3),
    ("Cisco", "Firepower 2100"): (D_SEC, I_HW, PF_FW),
    ("Cisco", "Meraki MR46"): (D_NET, I_HW, PF_AP),
    # ── Juniper ──
    ("Juniper", "SRX 340"): (D_SEC, I_HW, PF_FW),
    ("Juniper", "EX4300"): (D_NET, I_HW, PF_L3),
    ("Juniper", "MX204"): (D_NET, I_HW, PF_ROUTER),
    # ── Palo Alto ──
    ("Palo Alto Networks", "PA-440"): (D_SEC, I_HW, PF_FW),
    ("Palo Alto Networks", "Prisma Access"): (D_SEC, I_SVC, PF_FW),
    ("Palo Alto Networks", "Cortex XDR"): (D_SEC, I_SW, PF_ANTI),
    # ── Fortinet ──
    ("Fortinet", "FortiAnalyzer"): (D_SEC, I_SW, PF_LOG),
    ("Fortinet", "FortiManager"): (D_SEC, I_SW, PF_MON),
    # ── F5 ──
    ("F5", "BIG-IP i2600"): (D_NET, I_HW, PF_LB),
    ("F5", "BIG-IP Virtual Edition"): (D_NET, I_SW, PF_LB),
    # ── Check Point ──
    ("Check Point", "CloudGuard"): (D_SEC, I_SW, PF_FW),
    # ── CrowdStrike ──
    ("CrowdStrike", "Falcon Insight"): (D_SEC, I_SW, PF_ANTI),
    # ── Trellix ──
    ("Trellix", "Endpoint Security"): (D_SEC, I_SW, PF_ANTI),
    ("Trellix", "Network Security"): (D_SEC, I_HW, PF_IPS),
    # ── Sophos ──
    ("Sophos", "XGS Firewall"): (D_SEC, I_HW, PF_FW),
    ("Sophos", "Intercept X"): (D_SEC, I_SW, PF_ANTI),
    # ── Trend Micro ──
    ("Trend Micro", "Deep Security"): (D_SEC, I_SW, PF_ANTI),
    ("Trend Micro", "Vision One"): (D_SEC, I_SW, PF_ANTI),
    # ── Zscaler ──
    ("Zscaler", "ZPA"): (D_SEC, I_SW, PF_FW),
    # ── 한국 보안 ──
    ("AhnLab", "TrusGuard"): (D_SEC, I_HW, PF_FW),
    ("AhnLab", "MDS"): (D_SEC, I_HW, PF_SANDBOX),
    ("SECUI", "MF2 3000"): (D_SEC, I_HW, PF_FW),
    ("SECUI", "BLUEMAX NGF"): (D_SEC, I_HW, PF_FW),
    ("AXGATE", "AXGATE 80E"): (D_SEC, I_HW, PF_FW),
    ("WINS", "Sniper IPS"): (D_SEC, I_HW, PF_IPS),
    ("IGLOO Security", "SPiDER TM"): (D_SEC, I_SW, PF_LOG),
    ("MONITORAPP", "AIWAF"): (D_SEC, I_HW, PF_WAF),
    ("PIOLINK", "PAS-K"): (D_NET, I_HW, PF_LB),
    ("PIOLINK", "WEBFRONT-K"): (D_SEC, I_HW, PF_WAF),
    ("Genians", "Genian NAC"): (D_SEC, I_SW, PF_GENERIC),
    ("Genians", "Genian EDR"): (D_SEC, I_SW, PF_ANTI),
    ("WAREVALLEY", "Chakra Max"): (D_SEC, I_SW, PF_DBA),
    ("Radware", "DefensePro"): (D_SEC, I_HW, PF_IPS),
    ("Gigamon", "GigaVUE HC1"): (D_NET, I_HW, PF_PKT),
    ("Infoblox", "BloxOne DDI"): (D_NET, I_SW, PF_GENERIC),
    ("SK Shieldus", "SecuCloudia"): (D_SEC, I_SW, PF_GENERIC),
    ("Netskope", "CASB"): (D_SEC, I_SVC, PF_GENERIC),
    ("SonicWall", "NSa 2700"): (D_SEC, I_HW, PF_FW),
    ("Imperva", "WAF Gateway"): (D_SEC, I_HW, PF_WAF),
    ("Tenable", "Nessus"): (D_SEC, I_SW, PF_MON),
    ("Qualys", "VMDR"): (D_SEC, I_SW, PF_MON),
    ("Tanium", "Tanium Core"): (D_SEC, I_SW, PF_MON),
    # ── 서버·스토리지 ──
    ("Dell", "PowerEdge R760"): (D_SVR, I_HW, PF_X86),
    ("Dell", "PowerStore 500T"): (D_STO, I_HW, PF_GENERIC),
    ("Dell", "PowerScale F900"): (D_STO, I_HW, PF_OBJ_STO),
    ("HPE", "ProLiant DL380 Gen11"): (D_SVR, I_HW, PF_X86),
    ("HPE", "Nimble Storage"): (D_STO, I_HW, PF_GENERIC),
    ("HPE", "Aruba CX 6300"): (D_NET, I_HW, PF_L3),
    ("IBM", "Power S1022"): (D_SVR, I_HW, PF_UNIX),
    ("IBM", "FlashSystem 5200"): (D_STO, I_HW, PF_GENERIC),
    ("Lenovo", "ThinkSystem SR650 V3"): (D_SVR, I_HW, PF_X86),
    ("Supermicro", "SuperServer 1U"): (D_SVR, I_HW, PF_X86),
    ("NetApp", "AFF A250"): (D_STO, I_HW, PF_GENERIC),
    ("Pure Storage", "FlashArray//X"): (D_STO, I_HW, PF_GENERIC),
    ("Pure Storage", "FlashBlade//S"): (D_STO, I_HW, PF_OBJ_STO),
    ("Nutanix", "NX-3060"): (D_SVR, I_HW, PF_GENERIC),
    ("Nutanix", "Prism Central"): (D_SVR, I_SW, PF_MON),
    ("Synology", "SA3600"): (D_STO, I_HW, PF_GENERIC),
    ("Huawei", "OceanStor 5300 V6"): (D_STO, I_HW, PF_GENERIC),
    ("Huawei", "CloudEngine S5735"): (D_NET, I_HW, PF_L3),
    ("Samsung Electronics", "PM9A3 NVMe SSD"): (D_STO, I_HW, PF_GENERIC),
    ("NVIDIA", "A100 GPU"): (D_SVR, I_HW, PF_GPU),
    ("NVIDIA", "H100 GPU"): (D_SVR, I_HW, PF_GPU),
    ("Intel", "Xeon Scalable 4th Gen"): (D_SVR, I_HW, PF_GENERIC),
    ("AMD", "EPYC 9004"): (D_SVR, I_HW, PF_GENERIC),
    # ── 가상화·클라우드 ──
    ("VMware", "NSX 4"): (D_NET, I_SW, PF_VIRT),
    ("VMware", "vSAN 8"): (D_STO, I_SW, PF_VIRT),
    ("Citrix", "Virtual Apps and Desktops"): (D_SVR, I_SW, PF_VIRT),
    ("Red Hat", "OpenShift"): (D_SVR, I_SW, PF_CONTAINER),
    ("Red Hat", "Ansible Automation Platform"): (D_SVR, I_SW, PF_AUTO),
    ("Red Hat", "Enterprise Linux 9"): (D_SVR, I_SW, PF_OS),
    ("HashiCorp", "Terraform"): (D_SVR, I_SW, PF_CFG),
    ("HashiCorp", "Vault"): (D_SEC, I_SW, PF_GENERIC),
    ("Amazon", "EC2"): (D_SVR, I_SVC, PF_GENERIC),
    ("Amazon", "S3"): (D_STO, I_SVC, PF_OBJ_STO),
    ("Amazon", "RDS"): (D_DB, I_SVC, PF_GENERIC),
    ("Google", "Compute Engine"): (D_SVR, I_SVC, PF_GENERIC),
    ("Google", "BigQuery"): (D_DB, I_SVC, PF_DW),
    ("Microsoft", "Azure Virtual Machines"): (D_SVR, I_SVC, PF_GENERIC),
    ("Microsoft", "SQL Server 2022"): (D_DB, I_SW, PF_GENERIC),
    ("Microsoft", "Windows Server 2022"): (D_SVR, I_SW, PF_OS),
    ("Veeam", "Backup & Replication"): (D_STO, I_SW, PF_BACKUP_SW),
    ("Veritas", "NetBackup"): (D_STO, I_SW, PF_BACKUP_SW),
    ("Rubrik", "Cloud Data Management"): (D_STO, I_SW, PF_BACKUP_SW),
    # ── DB·미들웨어 ──
    ("Oracle", "Database 19c"): (D_DB, I_SW, PF_GENERIC),
    ("Oracle", "WebLogic Server"): (D_SVR, I_SW, PF_MW),
    ("TmaxSoft", "JEUS"): (D_SVR, I_SW, PF_MW),
    ("SAP", "S/4HANA"): (D_APP, I_SW, PF_GENERIC),
    ("SAP", "HANA DB"): (D_DB, I_SW, PF_INMEM),
    ("Elastic", "Elasticsearch"): (D_SVR, I_SW, PF_LOG),
    ("Splunk", "Enterprise"): (D_SEC, I_SW, PF_LOG),
    ("Cloudera", "CDP Private Cloud"): (D_DB, I_SW, PF_DW),
    ("MongoDB", "Atlas"): (D_DB, I_SVC, PF_GENERIC),
    ("Snowflake", "Data Cloud"): (D_DB, I_SVC, PF_DW),
    ("Graylog", "Enterprise"): (D_SVR, I_SW, PF_LOG),
    # ── CDN·기타 ──
    ("Akamai", "Kona Site Defender"): (D_SEC, I_SVC, PF_WAF),
    ("Akamai", "Ion"): (D_NET, I_SVC, PF_GENERIC),
    ("Cloudflare", "WAF"): (D_SEC, I_SVC, PF_WAF),
    ("Cloudflare", "CDN"): (D_NET, I_SVC, PF_GENERIC),
    ("Anthropic", "Claude"): (D_APP, I_SVC, PF_GENERIC),
    ("OpenAI", "GPT-4o"): (D_APP, I_SVC, PF_GENERIC),
    # ── Arista ──
    ("Arista", "7050X3"): (D_NET, I_HW, PF_L3),
    ("Arista", "CloudVision"): (D_NET, I_SW, PF_MON),
    # ── Nokia ──
    ("Nokia", "7750 SR"): (D_NET, I_HW, PF_ROUTER),
    # ── A10 ──
    ("A10 Networks", "Thunder ADC"): (D_NET, I_HW, PF_LB),
}


def run():
    db = SessionLocal()
    try:
        assigned = 0
        skipped = 0
        for (vendor, name), (domain_opt, imp_opt, family_opt) in CLASSIFICATIONS.items():
            product = db.scalar(
                select(ProductCatalog).where(
                    ProductCatalog.vendor == vendor,
                    ProductCatalog.name == name,
                )
            )
            if not product:
                skipped += 1
                continue
            # 이미 attribute가 있는지 확인
            existing = db.scalar(
                select(ProductCatalogAttributeValue.id).where(
                    ProductCatalogAttributeValue.product_id == product.id,
                    ProductCatalogAttributeValue.attribute_id == ATTR_DOMAIN,
                )
            )
            if existing:
                skipped += 1
                continue
            # 3개 속성 추가
            for attr_id, opt_id in [(ATTR_DOMAIN, domain_opt), (ATTR_IMP_TYPE, imp_opt), (ATTR_PRODUCT_FAMILY, family_opt)]:
                if opt_id is None:
                    continue
                db.add(ProductCatalogAttributeValue(
                    product_id=product.id,
                    attribute_id=attr_id,
                    option_id=opt_id,
                    sort_order=100,
                    is_primary=True,
                ))
            assigned += 1
        db.commit()
        print(f"Done: {assigned} products classified, {skipped} skipped")
    finally:
        db.close()


if __name__ == "__main__":
    run()
