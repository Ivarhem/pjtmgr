"""국산 보안/네트워크 제품 시드 보강."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import SessionLocal
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.catalog_similarity_service import normalize_vendor_name, normalize_product_name

PRODUCTS = [
    ("AhnLab", "TrusGuard 100B", "hardware"),
    ("AhnLab", "TrusGuard 500B", "hardware"),
    ("AhnLab", "TrusGuard 1000B", "hardware"),
    ("AhnLab", "MDS 2000", "hardware"),
    ("AhnLab", "MDS 10000", "hardware"),
    ("AXGATE", "NF 100", "hardware"),
    ("AXGATE", "NF 200", "hardware"),
    ("AXGATE", "NF 1000", "hardware"),
    ("SECUI", "BLUEMAX NGF 2000", "hardware"),
    ("SECUI", "BLUEMAX NGF 4000", "hardware"),
    ("SECUI", "BLUEMAX NGF 6000", "hardware"),
    ("SECUI", "BLUEMAX IPS 2000", "hardware"),
    ("WINS", "SNIPER IPS 5000", "hardware"),
    ("WINS", "SNIPER IPS 20000", "hardware"),
    ("MONITORAPP", "AIWAF-1000", "hardware"),
    ("MONITORAPP", "AIWAF-2000", "hardware"),
    ("PENTA Security", "WAPPLES 1000", "hardware"),
    ("PENTA Security", "WAPPLES 5000", "hardware"),
    ("PIOLINK", "PAS-K 2824", "hardware"),
    ("PIOLINK", "PAS-K 4424", "hardware"),
    ("PIOLINK", "WEBFRONT-K 4000", "hardware"),
    ("PIOLINK", "WEBFRONT-K 8000", "hardware"),
]


def run():
    db = SessionLocal()
    try:
        added = skipped = 0
        for vendor, name, product_type in PRODUCTS:
            exists = db.scalar(select(ProductCatalog.id).where(ProductCatalog.vendor == vendor, ProductCatalog.name == name))
            if exists:
                skipped += 1
                continue
            db.add(ProductCatalog(
                vendor=vendor,
                name=name,
                product_type=product_type,
                verification_status="unverified",
                normalized_vendor=normalize_vendor_name(vendor),
                normalized_name=normalize_product_name(name),
            ))
            added += 1
        db.commit()
        print(f"Done: {added} domestic products added, {skipped} skipped")
    finally:
        db.close()


if __name__ == "__main__":
    run()
