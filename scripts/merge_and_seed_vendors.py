"""제조사 통합 (소속 명확한 건) + 인지도 있는 회사 시드 추가."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import select, update
from app.core.database import SessionLocal
from app.modules.infra.models.catalog_vendor_meta import CatalogVendorMeta
from app.modules.infra.models.catalog_vendor_alias import CatalogVendorAlias
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.catalog_similarity_service import normalize_vendor_name


def _ensure_alias(db, vendor_canonical, alias_value):
    normalized = normalize_vendor_name(alias_value)
    if not normalized:
        return
    # 글로벌 유니크 제약 — 다른 vendor에 이미 있어도 안됨
    exists = db.scalar(
        select(CatalogVendorAlias.id).where(
            CatalogVendorAlias.normalized_alias == normalized,
        )
    )
    if not exists:
        db.add(CatalogVendorAlias(
            vendor_canonical=vendor_canonical,
            alias_value=alias_value,
            normalized_alias=normalized,
            sort_order=100,
            is_active=True,
        ))


def _ensure_self_alias(db, vendor_canonical):
    normalized = normalize_vendor_name(vendor_canonical)
    if not normalized:
        return
    # 글로벌 유니크 체크
    exists = db.scalar(
        select(CatalogVendorAlias.id).where(
            CatalogVendorAlias.normalized_alias == normalized,
        )
    )
    if not exists:
        db.add(CatalogVendorAlias(
            vendor_canonical=vendor_canonical,
            alias_value=vendor_canonical,
            normalized_alias=normalized,
            sort_order=0,
            is_active=True,
        ))


def _ensure_meta(db, vendor_canonical, name_ko, memo):
    meta = db.get(CatalogVendorMeta, vendor_canonical)
    if meta is None:
        meta = CatalogVendorMeta(vendor_canonical=vendor_canonical)
        db.add(meta)
    if name_ko and not meta.name_ko:
        meta.name_ko = name_ko
    if memo and not meta.memo:
        meta.memo = memo


def merge_vendor(db, old_vendor, new_vendor):
    """old_vendor의 제품·alias를 new_vendor로 이동하고, old_vendor를 alias로 등록."""
    # 1) ProductCatalog.vendor 이동
    db.execute(
        update(ProductCatalog)
        .where(ProductCatalog.vendor == old_vendor)
        .values(vendor=new_vendor)
    )
    # 2) CatalogVendorAlias 이동
    db.execute(
        update(CatalogVendorAlias)
        .where(CatalogVendorAlias.vendor_canonical == old_vendor)
        .values(vendor_canonical=new_vendor)
    )
    # 3) old_vendor를 new_vendor의 alias로 추가
    _ensure_alias(db, new_vendor, old_vendor)
    # 4) old meta 삭제
    old_meta = db.get(CatalogVendorMeta, old_vendor)
    if old_meta:
        db.delete(old_meta)


# ── 통합 대상 ──
MERGES = [
    # (old_vendor, new_vendor)
    ("MySQL", "Oracle"),
    ("NGINX", "F5"),
    ("Dell EMC", "Dell"),
    ("Piolink", "PIOLINK"),
]

# Tibero → TmaxSoft (TmaxSoft가 없으므로 새로 생성)
TIBERO_MERGE = ("Tibero", "TmaxSoft")

# ── 신규 시드 ──
NEW_SEEDS = [
    ("TmaxSoft", "티맥스소프트", "한국 미들웨어·DBMS 기업. Tibero·JEUS·ProObject.", ["티맥스", "Tmax"]),
    ("Anthropic", "앤스로픽", "AI 안전 연구 기업. Claude 시리즈 개발사.", []),
    ("Apple", "애플", "iPhone·Mac·iPad·macOS·iOS 글로벌 기업.", ["Apple Inc."]),
    ("ASUS", "에이수스", "대만 PC·마더보드·서버 제조사.", ["아수스", "ASUSTeK"]),
    ("SAP", "에스에이피", "ERP·S/4HANA·비즈니스 애플리케이션 글로벌 기업.", ["SAP SE"]),
    ("Google", "구글", "검색·클라우드(GCP)·Android·AI 글로벌 기업.", ["Google Cloud", "Alphabet"]),
    ("Amazon", "아마존", "AWS 클라우드·e커머스 글로벌 기업.", ["AWS", "Amazon Web Services"]),
    ("Intel", "인텔", "x86 CPU·서버 프로세서·반도체 기업.", ["Intel Corporation"]),
    ("AMD", "에이엠디", "CPU·GPU·서버 프로세서 반도체 기업. EPYC·Ryzen.", ["Advanced Micro Devices"]),
    ("Samsung Electronics", "삼성전자", "반도체·메모리·SSD·서버·모바일 글로벌 기업.", ["삼성", "Samsung"]),
    ("LG CNS", "엘지씨엔에스", "한국 IT서비스·클라우드·AI 기업.", []),
    ("SK Shieldus", "에스케이쉴더스", "한국 통합 보안·관제 서비스 기업.", ["SK쉴더스", "ADT캡스"]),
    ("Sophos", "소포스", "엔드포인트·방화벽·이메일 보안 솔루션 영국 기업.", []),
    ("Huawei", "화웨이", "네트워크·서버·스토리지·통신장비 중국 기업.", ["화웨이테크놀로지"]),
    ("Supermicro", "슈퍼마이크로", "서버·스토리지 하드웨어 제조사.", ["Super Micro", "SMCI"]),
    ("Rubrik", "루브릭", "제로 트러스트 데이터 보안·백업·복구 플랫폼.", []),
    ("Trellix", "트렐릭스", "XDR 보안 플랫폼. McAfee Enterprise+FireEye 합병.", ["McAfee", "FireEye"]),
    ("Akamai", "아카마이", "CDN·DDoS 방어·웹 보안 글로벌 기업.", ["Akamai Technologies"]),
    ("Cloudflare", "클라우드플레어", "CDN·DNS·DDoS 방어·Zero Trust 보안 플랫폼.", []),
    ("Mimecast", "마임캐스트", "이메일 보안·아카이빙 솔루션.", []),
    ("Proofpoint", "프루프포인트", "이메일 보안·위협 탐지 플랫폼.", []),
    ("Tanium", "타니움", "엔드포인트 관리·보안·컴플라이언스 플랫폼.", []),
    ("Tenable", "테너블", "취약점 관리·Nessus 개발사.", []),
    ("Qualys", "퀄리스", "클라우드 기반 취약점 관리·컴플라이언스 플랫폼.", []),
]


def run():
    db = SessionLocal()
    try:
        merged = 0
        seeded = 0

        # 1) 제조사 통합
        for old_vendor, new_vendor in MERGES:
            # old_vendor가 존재하는지 확인
            has_products = db.scalar(
                select(ProductCatalog.id).where(ProductCatalog.vendor == old_vendor).limit(1)
            )
            has_aliases = db.scalar(
                select(CatalogVendorAlias.id).where(CatalogVendorAlias.vendor_canonical == old_vendor).limit(1)
            )
            has_meta = db.get(CatalogVendorMeta, old_vendor)
            if has_products or has_aliases or has_meta:
                merge_vendor(db, old_vendor, new_vendor)
                merged += 1
                print(f"  Merged: {old_vendor} → {new_vendor}")

        # Tibero → TmaxSoft
        has_tibero = db.scalar(
            select(ProductCatalog.id).where(ProductCatalog.vendor == "Tibero").limit(1)
        ) or db.scalar(
            select(CatalogVendorAlias.id).where(CatalogVendorAlias.vendor_canonical == "Tibero").limit(1)
        ) or db.get(CatalogVendorMeta, "Tibero")
        if has_tibero:
            merge_vendor(db, "Tibero", "TmaxSoft")
            merged += 1
            print(f"  Merged: Tibero → TmaxSoft")

        # 중간 커밋 (통합분)
        db.commit()

        # 2) 신규 시드
        for vendor, name_ko, memo, extra_aliases in NEW_SEEDS:
            _ensure_meta(db, vendor, name_ko, memo)
            _ensure_self_alias(db, vendor)
            db.flush()  # self-alias flush 후 extra alias 추가
            for alias in extra_aliases:
                _ensure_alias(db, vendor, alias)
            db.flush()
            seeded += 1

        db.commit()
        print(f"\nDone: {merged} vendors merged, {seeded} vendors seeded")
    finally:
        db.close()


if __name__ == "__main__":
    run()
