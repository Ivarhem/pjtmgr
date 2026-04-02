# 카탈로그 속성 옵션 — 다국어 라벨 + Alias 관리 설계

> 작성일: 2026-04-02
> 상태: 승인 대기

---

## 목적

카탈로그 속성 옵션(아이템)에 영문 기본 라벨(`label`) + 한글 보조 라벨(`label_kr`)을 분리하고, 한/영 전환 UI와 인라인 alias 관리를 제공한다. 검색 시 `option_key`, `label`, `label_kr`, 모든 alias를 통합 매칭한다.

---

## 데이터 모델

### 컬럼 변경: `catalog_attribute_options`

| 컬럼 | 변경 | 설명 |
|------|------|------|
| `label` | 기존 유지, **영문 전용으로 제약** | 기본 라벨. 한글 문자(`[\uAC00-\uD7A3\u3130-\u318F]`) 포함 불가 |
| `label_kr` | **신규 추가** `VARCHAR(100) NULL` | 한글명. 한글 혼용 또는 영문과 동일값 허용 |

### 자동 alias 동기화

- `label_kr` 저장 시 `catalog_attribute_option_aliases`에 자동 upsert
- `match_type = 'label_kr_auto'`로 수동 alias와 구분
- `label_kr` 변경 → 기존 `label_kr_auto` alias 교체
- `label_kr` 삭제(빈 값) → `label_kr_auto` alias 삭제
- `label_kr_auto` alias는 UI에서 `×` 삭제 불가 (한글명 필드에서 제어)

### 마이그레이션 (0055)

1. `label_kr VARCHAR(100) NULL` 컬럼 추가
2. 기존 한글 `label` 값을 `label_kr`로 복사
3. `label`을 영문명으로 교체 (backfill 매핑 테이블 사용)
4. `label_kr` 값을 `match_type='label_kr_auto'` alias로 자동 등록 — `INSERT ... ON CONFLICT (attribute_option_id, normalized_alias) DO NOTHING`으로 기존 수동 alias와의 충돌 방지
5. 검증: alias 등록 후 `label_kr`이 있는 옵션 수와 `label_kr_auto` alias 수를 비교 로그 출력

---

## 백엔드

### 모델

- `CatalogAttributeOption.label_kr: Mapped[str | None]` 추가

### 스키마

- `CatalogAttributeOptionCreate`: `label_kr: str | None` 추가, `label` 필드에 한글 불가 validator
- `CatalogAttributeOptionUpdate`: `label_kr: str | None` 추가, `label` 필드에 한글 불가 validator
- `CatalogAttributeOptionRead`: `label_kr: str | None`, `domain_option_label_kr: str | None`, `aliases: list[dict]` 추가

### 서비스 (catalog_attribute_service.py)

- `create_attribute_option`: 저장 후 `label_kr` 값이 있으면 `label_kr_auto` alias 자동 생성
- `update_attribute_option`: `label_kr` 변경 감지 → `label_kr_auto` alias upsert/삭제. 같은 트랜잭션 내에서 처리하며 alias insert는 `ON CONFLICT DO NOTHING`으로 중복 방지
- `_guard_same_attribute_option_duplicate`, `_guard_cross_attribute_option_duplicate`: `label_kr`도 중복 비교 대상에 추가
- `_enrich_option_scope`: `domain_option_label_kr` 필드도 함께 반환
- 옵션 목록 조회 시 alias 배열도 함께 반환 (aliases eager load 또는 서브쿼리)

### API 변경

기존 엔드포인트 그대로 사용. 요청/응답에 `label_kr`, `aliases` 필드 추가.

- `GET /api/v1/catalog-attributes/{id}/options` → 응답에 `label_kr`, `aliases[]` 포함
- `POST /api/v1/catalog-attributes/{id}/options` → `label_kr` 수신
- `PATCH /api/v1/catalog-attributes/options/{id}` → `label_kr` 수신

Alias 개별 CRUD는 기존 엔드포인트 그대로 사용:
- `GET /api/v1/catalog-integrity/attribute-aliases?attribute_key=X`
- `POST /api/v1/catalog-integrity/attribute-aliases`
- `DELETE /api/v1/catalog-integrity/attribute-aliases/{id}`

---

## 프론트엔드

### 한/영 토글

- 카탈로그 toolbar에 `한/EN` 토글 버튼 추가
- 토글 상태: `localStorage` key `CATALOG_LABEL_LANG_KEY = "catalog_label_lang"` (허용값: `"ko"` | `"en"`, 기본: `"ko"`) — JS 상수로 선언
- 토글 시 데이터 재로드 없이 표시만 전환:
  - 트리 노드 라벨
  - 그리드 분류 컬럼 셀값
- 투영 함수(`projectCatalogRowForCurrentLayout`)에서 현재 lang에 따라 `label` 또는 `label_kr` 선택
- `label_kr`이 없으면 `label`(영문) fallback

### 통합 검색

- 옵션 로드 시 `aliases` 배열을 함께 캐시
- 트리 필터·그리드 필터에서 검색어를 다음 대상에 매칭:
  - `option_key`
  - `label` (영문)
  - `label_kr` (한글)
  - `aliases[].alias_value` (모든 별칭)
- 부분 문자열 매칭 (예: "firew" → "Firewall" 매칭)

### 아이템 모달 변경

**모달 크기**: `.modal-lg` (720px) — alias 태그 영역 확보 필요

**필드 배치**:

```
코드: fw              정렬: 10         활성: ✓
영문명: Firewall      한글명: 방화벽
도메인: 보안
별칭  [FW] [fire wall] [파이어월]  [+ 추가]
      ※ 한글명은 자동 등록됩니다
설명: ______________________________________
```

**필드 규칙**:

| 필드 | ID | 필수 | 제약 |
|------|----|------|------|
| 코드 | `catalog-classification-node-code` | Y | `^[a-z][a-z0-9_]*$`, 생성 후 읽기전용 |
| 영문명 | `catalog-classification-node-name` | Y | 한글 완성형·자모(`[\uAC00-\uD7A3\u3130-\u318F]`) 포함 불가 |
| 한글명 | `catalog-classification-node-name-kr` | N | 자유 입력 |
| 도메인 | `catalog-classification-node-domain` | 조건부 | product_family 속성일 때만 표시 |
| 별칭 | 태그 영역 | N | 인라인 추가/삭제 |
| 정렬 | `catalog-classification-node-sort-order` | N | 기본 100 |
| 활성 | `catalog-classification-node-active` | N | 기본 true |
| 설명 | `catalog-classification-node-note` | N | textarea |

**Alias 태그 동작**:

| 동작 | 처리 |
|------|------|
| 모달 열기 | 옵션의 alias 목록 로드 → 태그로 렌더링 |
| `label_kr_auto` 태그 | 배경색 구분, `×` 비활성 (한글명 필드에서 자동 관리) |
| `×` 클릭 (수동 alias) | `DELETE /api/v1/catalog-integrity/attribute-aliases/{id}` |
| `+ 추가` 클릭 | 인라인 input 활성화 → Enter로 `POST` → 태그 추가 |
| ESC 또는 빈 값 Enter | 인라인 input 닫기 |

---

## 마이그레이션 backfill 매핑 (주요 항목)

모든 기존 옵션에 대해 현재 한글 `label` → `label_kr`로 이동, `label`을 영문으로 교체.

### domain

| option_key | label (영문) | label_kr |
|---|---|---|
| net | Network | 네트워크 |
| sec | Security | 보안 |
| svr | Server | 서버 |
| sto | Storage | 스토리지 |
| db | Database | 데이터베이스 |
| app | Application | 애플리케이션 |

### imp_type

| option_key | label (영문) | label_kr |
|---|---|---|
| hw | Hardware | 하드웨어 |
| sw | Software | 소프트웨어 |
| svc | Service | 서비스 |

### platform

| option_key | label (영문) | label_kr |
|---|---|---|
| appliance | Appliance | - |
| x86 | x86 | - |
| windows | Windows | - |
| linux | Linux | - |
| unix | UNIX | - |
| vm | VM | - |
| container | Container | - |
| cloud | Cloud | - |
| virtual_appliance | Virtual Appliance | - |

### deployment_model

| option_key | label (영문) | label_kr |
|---|---|---|
| onprem | On-Prem | 온프레미스 |
| saas | SaaS | - |
| managed | Managed Service | - |
| hybrid | Hybrid | - |
| paas | PaaS | - |

### license_model

| option_key | label (영문) | label_kr |
|---|---|---|
| perpetual | Perpetual | 영구 |
| subscription | Subscription | 구독 |
| capacity | Capacity | 용량기반 |
| user_based | User Based | 사용자기반 |
| open_source | Open Source | 오픈소스 |
| freemium | Freemium | - |
| metered | Metered | 종량제 |

### product_family

기존 시드 + 0054 신규 ~80개 옵션 전체에 대해 영문명 매핑. 대부분은 이미 영문 라벨(UTM, IPS, WAF 등)이므로 `label` 유지, 한글 라벨(방화벽, L2 스위치 등)만 `label_kr`로 이동.

예시:

| option_key | label (영문) | label_kr |
|---|---|---|
| fw | Firewall | 방화벽 |
| l2 | L2 Switch | L2 스위치 |
| l3 | L3 Switch | L3 스위치 |
| router | Router | 라우터 |
| x86_server | x86 Server | x86 서버 |
| unix_server | UNIX Server | UNIX 서버 |
| blade_server | Blade Server | 블레이드 서버 |
| virtualization | Virtualization | 가상화 |
| container_platform | Container Platform | 컨테이너 플랫폼 |
| monitoring | Monitoring | 모니터링 |
| backup_sw | Backup Software | 백업 소프트웨어 |
| gpu_server | GPU Server | GPU 서버 |
| wlan_controller | WLAN Controller | 무선 컨트롤러 |
| access_point | Access Point | AP |
| sandbox | Sandbox | 샌드박스 |
| anti_malware | Anti-Malware | 안티멀웨어 |
| db_access_control | DB Access Control | DB 접근제어 |
| api_gateway | API Gateway | API 게이트웨이 |
| nosql | NoSQL | - |
| data_warehouse | Data Warehouse | 데이터 웨어하우스 |
| db_encryption | DB Encryption | DB 암호화 |
| in_memory_db | In-Memory DB | 인메모리 DB |

(전체 매핑은 마이그레이션 파일에 포함)

---

## 범위 외 (향후)

- 정합성 탭에 옵션 alias 일괄 관리 그리드 추가
- Import 시 alias 자동 매칭 적용
- 다국어 3개 이상 확장
