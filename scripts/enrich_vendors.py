"""제조사 메타 정보(한글명, 메모) 일괄 보강 스크립트."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import SessionLocal
from app.modules.infra.models.catalog_vendor_meta import CatalogVendorMeta
from app.modules.infra.models.catalog_vendor_alias import CatalogVendorAlias
from app.modules.infra.services.catalog_similarity_service import normalize_vendor_name

VENDOR_DATA = [
    # (vendor_canonical, name_ko, memo, extra_aliases)
    ("A10 Networks", "에이텐 네트웍스", "ADC·로드밸런서·DDoS 방어 솔루션 전문. Thunder 시리즈.", []),
    ("AhnLab", "안랩", "한국 대표 보안 기업. V3, TrusGuard, MDS 등.", []),
    ("Ansible", "앤서블", "Red Hat 소속 오픈소스 IT 자동화 도구.", ["Red Hat Ansible"]),
    ("Apache", "아파치", "Apache Software Foundation 오픈소스 프로젝트 (HTTP Server, Kafka, Hadoop 등).", ["ASF", "Apache Software Foundation"]),
    ("Arista", "아리스타", "데이터센터 네트워크 스위치·라우터 전문. EOS 기반.", ["Arista Networks"]),
    ("Aruba", "아루바", "HPE 자회사. 무선 AP·스위치·SD-WAN.", ["Aruba Networks", "HPE Aruba"]),
    ("AXGATE", "엑스게이트", "한국 방화벽·VPN 전문 기업.", []),
    ("Broadcom", "브로드컴", "반도체·인프라SW 대기업. VMware·Symantec·CA Technologies 인수.", ["Broadcom Inc."]),
    ("Ceph", None, "오픈소스 분산 스토리지 플랫폼. Red Hat이 주도.", ["Red Hat Ceph"]),
    ("Check Point", "체크포인트", "이스라엘 보안 기업. 차세대 방화벽·VPN·CloudGuard.", ["CheckPoint", "CPSL"]),
    ("Cisco", "시스코", "글로벌 네트워크 장비 1위. 라우터·스위치·보안·협업 솔루션.", ["Cisco Systems"]),
    ("Citrix", "시트릭스", "VDI·가상화·원격 접속 솔루션. Cloud Software Group 소속.", ["Citrix Systems"]),
    ("Cloudera", "클라우데라", "엔터프라이즈 데이터 플랫폼. Hadoop·Spark 기반 빅데이터.", []),
    ("CrowdStrike", "크라우드스트라이크", "클라우드 네이티브 EDR·XDR 보안 플랫폼. Falcon.", ["Crowd Strike"]),
    ("D'Amo", "디아모", "펜타시큐리티 DB 암호화 솔루션 브랜드.", ["DAmo"]),
    ("Dell", "델", "서버·스토리지·PC 제조사. PowerEdge·PowerStore.", ["Dell Technologies", "Dell Inc."]),
    ("Dell EMC", "델 이엠씨", "Dell 엔터프라이즈 스토리지·데이터 보호 브랜드.", ["DellEMC", "EMC"]),
    ("Elastic", "엘라스틱", "Elasticsearch·Kibana·Logstash (ELK 스택) 개발사.", ["Elastic NV", "ELK"]),
    ("F5", "에프파이브", "ADC·로드밸런서·WAF 전문. BIG-IP 시리즈.", ["F5 Networks", "F5 Inc."]),
    ("Fortinet", "포티넷", "UTM·차세대 방화벽 FortiGate 제조사. FortiOS 기반.", ["forti net"]),
    ("FutureSystems", "퓨처시스템", "한국 네트워크 보안 기업. Wapples WAF 개발사 (현 파이오링크와 협력).", []),
    ("Genians", "지니언스", "한국 NAC(네트워크 접근제어) 전문 기업. Genian NAC.", []),
    ("Gigamon", "기가몬", "네트워크 가시성·패킷 브로커 전문 기업.", []),
    ("GitLab", "깃랩", "DevOps 플랫폼. Git 저장소·CI/CD·이슈 트래커 통합.", []),
    ("Graylog", "그레이로그", "오픈소스 로그 관리·SIEM 플랫폼.", []),
    ("Hancom", "한컴", "한국 소프트웨어 기업. 한글(HWP)·오피스 제품군.", ["한글과컴퓨터", "Hancom Inc."]),
    ("HashiCorp", "하시코프", "인프라 자동화 도구. Terraform·Vault·Consul.", []),
    ("HPE", "에이치피이", "서버(ProLiant)·스토리지·네트워크 인프라 기업.", ["HP", "Hewlett Packard Enterprise"]),
    ("IBM", "아이비엠", "엔터프라이즈 서버·미들웨어·AI·클라우드 기업.", ["International Business Machines"]),
    ("IGLOO Security", "이글루시큐리티", "한국 통합보안관제(SIEM) 전문 기업. SPiDER TM.", ["이글루", "IGLOO"]),
    ("Imperva", "임퍼바", "WAF·데이터 보안·DDoS 방어 솔루션.", []),
    ("Infoblox", "인포블록스", "DDI(DNS·DHCP·IPAM) 전문 기업.", []),
    ("Jenkins", "젠킨스", "오픈소스 CI/CD 자동화 서버.", []),
    ("Juniper", "주니퍼", "네트워크 장비 기업. SRX 방화벽·EX/QFX 스위치.", ["Juniper Networks"]),
    ("Kong", "콩", "오픈소스 API 게이트웨이·서비스 메시 플랫폼.", ["Kong Inc."]),
    ("Kubernetes", "쿠버네티스", "컨테이너 오케스트레이션 오픈소스 플랫폼. CNCF 프로젝트.", ["K8s"]),
    ("Lenovo", "레노버", "글로벌 PC·서버(ThinkSystem) 제조사.", ["레노보"]),
    ("MariaDB", "마리아디비", "MySQL 포크 오픈소스 관계형 데이터베이스.", ["MariaDB Foundation"]),
    ("Microsoft", "마이크로소프트", "Windows·Azure·M365·SQL Server 등 글로벌 SW 기업.", ["MS"]),
    ("MinIO", "미니오", "고성능 오브젝트 스토리지. S3 호환 오픈소스.", []),
    ("MongoDB", "몽고디비", "문서형 NoSQL 데이터베이스.", ["Mongo"]),
    ("MONITORAPP", "모니터랩", "한국 WAF·SSL 가시성 전문 기업. AIWAF.", ["모니터앱"]),
    ("MySQL", "마이에스큐엘", "Oracle 소속 오픈소스 관계형 데이터베이스.", []),
    ("NetApp", "넷앱", "엔터프라이즈 스토리지·데이터 관리 전문 기업. ONTAP.", []),
    ("Netskope", "넷스코프", "SASE·CASB·SWG 클라우드 보안 플랫폼.", []),
    ("NexG", "넥스지", "한국 네트워크 장비 기업.", ["넥스지테크놀로지"]),
    ("NGINX", "엔진엑스", "웹서버·리버스프록시·로드밸런서. F5 소속.", ["nginx"]),
    ("Nokia", "노키아", "통신 인프라·네트워크 장비 기업.", []),
    ("Nutanix", "뉴타닉스", "HCI(하이퍼컨버지드 인프라)·멀티클라우드 플랫폼.", []),
    ("NVIDIA", "엔비디아", "GPU·AI 가속기·네트워크(Mellanox) 기업.", []),
    ("OpenAI", "오픈에이아이", "AI 연구 기업. GPT·ChatGPT·DALL-E 개발사.", []),
    ("Oracle", "오라클", "RDBMS·클라우드·ERP 글로벌 기업.", []),
    ("Palo Alto Networks", "팔로알토 네트웍스", "차세대 방화벽·Prisma·Cortex XDR 보안 플랫폼.", ["PAN", "팔로알토"]),
    ("PENTA Security", "펜타시큐리티", "한국 웹 보안·DB 암호화·IoT 보안 기업. WAPPLES WAF.", ["펜타시큐리티시스템즈"]),
    ("PIOLINK", "파이오링크", "한국 ADC·로드밸런서·웹방화벽 기업. WEBFRONT.", ["Piolink"]),
    ("PostgreSQL", "포스트그레스큐엘", "오픈소스 관계형 데이터베이스. PGDG 커뮤니티.", ["Postgres", "PG"]),
    ("Pulse Secure", "펄스시큐어", "SSL VPN·NAC 솔루션. Ivanti에 인수됨.", ["Ivanti Pulse", "PulseSecure"]),
    ("Pure Storage", "퓨어스토리지", "올플래시 스토리지 전문 기업. FlashArray·FlashBlade.", []),
    ("Radware", "래드웨어", "ADC·DDoS 방어·WAF 솔루션 이스라엘 기업.", []),
    ("Red Hat", "레드햇", "엔터프라이즈 리눅스(RHEL)·OpenShift·Ansible. IBM 소속.", ["RedHat", "RHEL"]),
    ("Redis", "레디스", "인메모리 데이터 구조 저장소. 캐시·메시지 브로커.", ["Redis Labs"]),
    ("Samsung SDS", "삼성SDS", "한국 IT서비스 기업. 클라우드·보안·물류 플랫폼.", ["삼성에스디에스"]),
    ("SECUI", "시큐아이", "한국 네트워크 보안 기업. MF2 방화벽·IPS.", ["시큐아이닷컴"]),
    ("SentinelOne", "센티넬원", "AI 기반 EDR·XDR 엔드포인트 보안 플랫폼.", []),
    ("Snowflake", "스노우플레이크", "클라우드 데이터 웨어하우스·데이터 레이크 플랫폼.", []),
    ("SolarWinds", "솔라윈즈", "네트워크·시스템 모니터링 소프트웨어.", []),
    ("SonicWall", "소닉월", "방화벽·VPN·이메일 보안 솔루션.", []),
    ("Splunk", "스플렁크", "로그 분석·SIEM·관제 플랫폼. Cisco에 인수됨.", []),
    ("Symantec", "시만텍", "엔드포인트·DLP·이메일 보안. Broadcom 소속.", ["Symantec Enterprise"]),
    ("Synology", "시놀로지", "NAS(네트워크 스토리지)·감시 솔루션 전문.", []),
    ("Tibero", "티베로", "TmaxSoft 국산 관계형 데이터베이스.", ["TmaxSoft Tibero", "티맥스티베로"]),
    ("Trend Micro", "트렌드마이크로", "엔드포인트·서버·클라우드 보안 솔루션.", ["TrendMicro"]),
    ("Veeam", "빔", "백업·재해복구·데이터 보호 소프트웨어.", ["Veeam Software"]),
    ("Veritas", "베리타스", "데이터 보호·백업(NetBackup)·정보 관리.", ["Veritas Technologies"]),
    ("VMware", "브이엠웨어", "서버 가상화·NSX·vSAN. Broadcom 소속.", ["VMWare"]),
    ("WAREVALLEY", "웨어밸리", "한국 DB 접근제어·감사 솔루션 기업. Chakra Max.", ["웨어벨리"]),
    ("WINS", "윈스", "한국 IPS·네트워크 보안 솔루션 기업. Sniper IPS.", ["윈스테크넷", "WINS Technologies"]),
    ("Zscaler", "지스케일러", "클라우드 보안 플랫폼. ZIA·ZPA·Zero Trust.", []),
]


def run():
    db = SessionLocal()
    try:
        updated_meta = 0
        added_aliases = 0

        for vendor_canonical, name_ko, memo, extra_aliases in VENDOR_DATA:
            # 1) CatalogVendorMeta upsert
            meta = db.get(CatalogVendorMeta, vendor_canonical)
            if meta is None:
                meta = CatalogVendorMeta(vendor_canonical=vendor_canonical)
                db.add(meta)
            if name_ko:
                meta.name_ko = name_ko
            if memo:
                meta.memo = memo
            updated_meta += 1

            # 2) extra aliases 추가
            for alias_value in extra_aliases:
                normalized = normalize_vendor_name(alias_value)
                if not normalized:
                    continue
                exists = db.scalar(
                    select(CatalogVendorAlias.id).where(
                        CatalogVendorAlias.vendor_canonical == vendor_canonical,
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
                    added_aliases += 1

        # 3) Piolink 중복 정리 → PIOLINK로 통합
        piolink_dupes = db.scalars(
            select(CatalogVendorAlias).where(
                CatalogVendorAlias.vendor_canonical == "Piolink",
            )
        ).all()
        for alias in piolink_dupes:
            alias.vendor_canonical = "PIOLINK"

        db.commit()
        print(f"Done: {updated_meta} vendors updated, {added_aliases} aliases added")
    finally:
        db.close()


if __name__ == "__main__":
    run()
