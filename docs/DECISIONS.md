# Architecture Decisions

> 아키텍처 결정 사항을 기록한다. 결정은 추가 전용(append-only) — 폐기 시 취소선으로 표시하고 이유를 남긴다.
>
> **새 결정 추가 시 템플릿**
>
> ```markdown
> ## 결정 제목
>
> ### 이유
> - 왜 이 결정을 내렸는가
>
> ### 영향
> - 코드/운영에 어떤 영향이 있는가
> ```

---

## AG Grid Community 사용

### 이유

- AG Grid Enterprise의 라이선스 비용 문제
- 무료 버전으로도 기본 필터, 정렬, 셀 편집, 복사/붙여넣기 지원
- 영업 담당자에게 익숙한 엑셀 유사 UX 제공

### 영향

- Set Filter 등 Enterprise 전용 기능 사용 불가 → 체크박스 드롭다운 커스텀 필터 구현
- 서버사이드 모델 없음 → 클라이언트 사이드 전체 로드

---

## 귀속월 기준 매출 관리

### 이유

- 실제 매출 인식 기준이 귀속월 (세금계산서 발행월과 다를 수 있음)
- 영업 담당자가 월별 실적을 귀속월 기준으로 보고

### 영향

- 모든 Actual/Forecast에 `revenue_month` (YYYY-MM-01) 필드 사용
- 보고서 집계 시 귀속월 기준 그룹핑

---

## 공급가액 기준 금액 저장

### 이유

- VAT는 업종/거래 유형에 따라 다를 수 있음
- 공급가액 기준이 GP 계산의 표준

### 영향

- 모든 금액 필드는 정수(원 단위) 저장
- 부동소수점 사용 금지
- UI에서 VAT 포함 금액이 필요하면 프론트에서 계산

---

## ~~SQLite로 시작~~ (폐기 — SQLite -> PostgreSQL 전환으로 대체)

### 이유

- ~~사내 단일 서버 배포, 동시 사용자 ~20명 수준~~
- ~~초기 개발 속도 우선, 별도 DB 서버 불필요~~
- ~~파일 기반이라 백업/이동 간편~~

### 영향

- ~~동시 쓰기 제한 (WAL 모드로 완화)~~
- ~~향후 사용자 증가 시 PostgreSQL 마이그레이션 필요~~
- ~~Alembic 도입 완료 — `alembic/versions/`에서 마이그레이션 관리~~

---

## 세션 기반 인증 (JWT 미사용)

### 이유

- 서버 렌더링(Jinja2) 중심 아키텍처에서 세션이 자연스러움
- SPA가 아니므로 JWT의 장점(stateless) 불필요
- 사내 네트워크 전용이라 토큰 관리 복잡도 불필요

### 영향

- 서버에 세션 상태 저장
- API 전용 클라이언트 추가 시 토큰 인증 별도 구현 필요

---

## 입금(Receipt)과 매출 실적(Actual) 분리

### 이유

- 입금은 별도 기능으로 관리하여 미수금 추적 명확화
- 향후 국세청 API 연동 시 입금 데이터 자동 대조 가능성

### 영향

- 입금은 `Receipt`, 배분은 `ReceiptMatch`로 분리 관리
- 미수금 = 매출 확정 합계 - 배분완료(`ReceiptMatch`) 합계
- raw `Receipt.amount`는 입금/선수금 추적 지표로 유지

---

## Forecast → Actual 동기화 기능

### 이유

- MA(유지보수) 사업은 월별 금액이 동일하므로 Forecast를 Actual로 일괄 복사 필요
- 수작업 입력 반복을 줄이기 위한 편의 기능

### 영향

- 동기화 시 기존 Actual이 있으면 건너뛰기/덮어쓰기 선택
- 동기화된 Actual은 "임시" 상태로 생성 → 확정 필요

---

## Startup 시 DB 준비와 마이그레이션 자동 수행

### 이유

- 개발/배포 시 애플리케이션 시작 직후 최소 실행 가능 상태를 자동으로 보장해야 함
- SQLite 파일 DB와 레거시 스키마 이력을 함께 다루므로 수동 초기화 순서 의존을 줄일 필요가 있음
- 참조 데이터 seed와 bootstrap 관리자 생성은 스키마 준비 이후에만 안전하게 수행 가능함

### 영향

- startup에서 DB 준비 단계가 `create_all`(dev), 레거시 마이그레이션, Alembic stamp/upgrade를 순서대로 수행한다
- 참조 데이터 seed와 bootstrap 관리자 생성은 DB 준비 이후 단계로 분리 유지한다
- 초기화 흐름을 변경할 때는 `README.md` 실행/초기 설정과 `docs/DECISIONS.md`를 함께 검토해야 한다

---

## 단일 코드베이스 + 배포 프로필 (모듈화)

### 이유

- projmgr(회계)와 inframgr(인프라) 두 프로젝트가 기술 스택, 아키텍처 패턴, 코드 규칙이 거의 동일
- 공통 도메인(사용자, 업체, 인증) 중복 제거 필요
- 마이크로서비스 대신 단일 코드베이스 선택: 오프라인 배포 단순성, 개발 효율, 리포 하나/테스트 한 번
- 모듈 격리는 코드 규칙 + lint로 충분한 규모

### 영향

- `ENABLED_MODULES` 환경변수로 모듈 선택적 활성화
- 하나의 Docker 이미지, `.env`만 달리하여 본사/현장 배포 구분
- 의존성이 이미 끊어져 있으므로 향후 분리 필요 시 추출 가능

---

## 모듈 구조 (core / common / accounting / infra)

### 이유

- 영업팀은 회계모듈만, 기술팀은 인프라모듈만 사용 가능하도록 분리 필요
- 인프라모듈을 오프라인 환경(프로젝트 현장)에 standalone 배포 가능해야 함
- 회계모듈과 인프라모듈 간 의존성 zero 유지

### 영향

- `app/core/`: 모듈 독립 인프라 (app_factory, config, database, exceptions, auth, startup)
- `app/modules/common/`: 항상 활성 (User, Partner, Setting 등)
- `app/modules/accounting/`: 회계 도메인 (Contract, Transaction, Receipt 등)
- `app/modules/infra/`: 인프라 도메인 (Project, Asset, IP, Policy 등)
- import 규칙: `core <- common <- {accounting, infra}`, `accounting <-> infra` 금지

---

## RBAC 도입 (실용적 역할 기반 접근 제어)

### 이유

- 기존 admin/user 2단계 권한으로는 모듈별 접근 제어 불가
- 풀 RBAC(resource x action 조합)는 현 규모에 과함
- 모듈 접근 + 모듈별 권한 수준(read/full)으로 충분

### 영향

- Role 모델 도입, `permissions` JSON 컬럼으로 모듈별 접근 수준 관리
- User.role (문자열) -> User.role_id (FK -> Role.id)로 전환
- 기본 역할 4종: 관리자, 영업담당자, 기술담당자, PM
- `require_module_access()` 의존성으로 라우터 레벨 접근 제어
- 풀 RBAC 확장 플레이스홀더 유지

---

## common 모델은 infra 전용 FK를 직접 참조하지 않음

### 이유

- `ContractPeriod`는 common 모듈의 공유 엔티티라서 infra 전용 테이블 구조에 ORM 레벨로 결합되면 모듈 경계가 흐려진다
- Python import 규칙뿐 아니라 ORM 메타데이터에서도 `core <- common <- {accounting, infra}` 방향을 지키는 편이 유지보수와 분리 가능성에 유리하다
- 프로젝트별 분류 레이아웃 연결은 인프라 기능이지만, 계약단위 식별 자체는 공통 도메인에 남아 있어야 한다

### 영향

- `ContractPeriod.classification_layout_id`는 common 모델에서 plain nullable ID로 유지한다
- infra 서비스가 이 값을 해석해 `classification_layouts`와 연결한다
- DB 레벨 FK 정리나 제약 변경은 별도 Alembic migration으로 따라간다

---

## ~~Partner -> Customer 통합~~ (폐기 — D-015에서 Customer → Partner로 재리네이밍)

### 이유

- ~~inframgr의 Partner/Contact와 projmgr의 Customer/CustomerContact가 동일 개념~~
- ~~공통모듈에서 통합 관리하여 중복 제거~~

### 영향

- ~~Customer 모델에 `customer_type`, `phone`, `address`, `note` 필드 추가~~
- ~~CustomerContact에 `department`, `title`, `emergency_phone`, `note` 필드 추가~~
- ~~Partner.project_id FK 제거 (common -> infra 의존성 위반)~~
- ~~inframgr의 `external_id`, `external_source` 필드 제거 (sync_service 제거)~~

---

## SQLite -> PostgreSQL 전환

### 이유

- 모듈 통합으로 동시 사용자/데이터 규모 증가 예상
- 멀티워커 지원 필요 (SQLite 단일 워커 제한 해소)
- inframgr가 이미 PostgreSQL 사용 중

### 영향

- DB: PostgreSQL 16, 드라이버: psycopg
- Docker Compose에 PostgreSQL 서비스 추가
- SQLite 전용 코드(WAL, busy_timeout, check_same_thread) 제거
- 앱 포트: 8000 -> 9000
- 기존 파일럿 데이터 폐기, 새 DB에서 시작

---

## bcrypt 전환

### 이유

- PBKDF2-SHA256에서 bcrypt로 전환하여 보안 강화
- inframgr와 해싱 방식 통일
- 파일럿 데이터 폐기 시점이므로 전환 비용 최소

### 영향

- `bcrypt>=4.0.0` 의존성 추가
- `app/core/auth/password.py`에서 bcrypt 해싱 사용
- 기존 PBKDF2 해시 호환 불필요 (파일럿 데이터 폐기)

---

## 단일 Alembic migration 체인

### 이유

- 모듈별 분리 migration은 순서 관리와 크로스 모듈 FK 처리가 복잡
- 비활성 모듈의 테이블도 DB에 존재하는 것이 단순하고 안전

### 영향

- 기존 projmgr/inframgr migration 모두 폐기, 통합 후 새 initial migration 생성
- standalone 배포 시에도 모든 테이블(accounting 포함)이 생성됨 (스키마 수준 결합이지만 운영상 무해)
- 단일 `alembic/versions/` 디렉토리에서 전체 스키마 관리

## Product Catalog — 글로벌 리소스 설계

### 이유

- HW 제품(vendor+model)은 여러 업체에서 공유되는 참조 데이터이므로 partner_id 없이 글로벌로 관리
- Asset.hardware_model_id FK로 연결하되, 기존 vendor/model 텍스트 컬럼은 하위호환 유지
- 장기적으로 HW스펙(size_unit)→랙배치, 인터페이스→포트맵 자동생성에 활용

### 영향

- product_catalog, hardware_specs, hardware_interfaces: 마이그레이션 0007
- asset.hardware_model_id FK + asset_software: 마이그레이션 0008
- ProductCatalog 삭제 시 자산 참조 guard (409)
- SPEC/EOSL Excel Import는 partner_id 불필요 (글로벌 upsert)

---

### D-013: 사업/계약단위 통합 (2026-03-23)

**결정:** Contract/ContractPeriod/ContractTypeConfig를 common 모듈로 이동. infra의 Project 테이블을 삭제하고 ContractPeriod를 인프라 작업 단위로 통합. 영업 전용 필드는 ContractSalesDetail 1:1 확장 테이블로 분리.

**이유:** 동일 사업이 영업/인프라에 각각 등록되는 데이터 중복 해소, 모듈 간 import 규칙 준수, ProjectContractLink N:N 관계 제거.

**영향:** infra의 `project_*` 테이블이 `period_*`로 리네이밍, FK가 `contract_period_id`로 변경. 원장 엔드포인트 `/api/v1/ledger/periods`로 이동. 영업 확장 정보는 `/api/v1/contract-periods/{id}/sales-detail` API로 분리.

---

### D-014: 계층적 코드 채번 체계 (2026-03-23)

**결정:** 고객코드(C000)·사업코드(C000-P000)·기간코드(C000-P000-Y26A) 계층적 코드 체계 도입. base36 순번 사용, 고객코드 생성 후 불변. CXXX는 고객 미지정 사업 예약 코드. 채번 유틸리티를 `app/core/code_generator.py`에 집중.

**이유:** 기존 코드(`SI-2026-0016`)가 고객·사업·기간 간 관계를 표현하지 못함. 코드만으로 소속 고객/사업 식별 가능해야 함.

**영향:** customer_code `C-000`→`C000` 변환, contract_code 재채번, period_code 신규 컬럼 추가. 비가역 마이그레이션(0011). UNIQUE 제약 + 3회 retry로 동시성 처리.

---

### D-015: Customer → Partner 리네이밍 (2026-03-24)

**결정:** Customer(거래처) 모델을 Partner(업체)로 리네이밍한다.

**이유:**

- "Customer"는 고객사만을 의미하지만, 실제로는 수행사/유지보수사/통신사/벤더 등 다양한 업체 유형을 포괄한다.
- Partner는 사업 관계의 모든 참여자를 포함하는 중립적 용어.
- partner_type으로 CUSTOMER/IMPLEMENTER/MAINTAINER/CARRIER/VENDOR/ETC 구분.

**영향:** DB 테이블/컬럼 rename (migration 0012), 코드 prefix C→P(업체), P→B(사업), ~90 파일 수정.

---

## 카탈로그 속성 기반 분류체계 (2026-04)

**결정:** 고정 분류 노드(ClassificationScheme/ClassificationNode)를 폐기하고, 카탈로그 속성(CatalogAttributeDef/CatalogAttributeOption) + 분류 레이아웃(ClassificationLayout) 기반의 유연한 분류체계로 전환한다.

**이유:**

- 기존 고정 노드 방식은 분류 깊이/구성 변경 시 데이터 마이그레이션 필요.
- 속성 기반 방식은 도메인/구현형태/제품군/플랫폼 등 속성을 자유롭게 조합하여 분류 레이아웃을 구성할 수 있음.
- 같은 제품을 프로젝트별로 다른 분류 기준으로 볼 수 있음.

**영향:** migrations 0026-0045 (노드→속성 데이터 마이그레이션 + 레거시 테이블 삭제), 프론트엔드 동적 분류 컬럼 생성.

---

## ag-Grid 상호작용 표준화 (2026-04)

**결정:** 모든 ag-Grid에 `buildStandardGridBehavior()` 헬퍼를 적용하여 싱글클릭=선택/상세, 더블클릭=편집/이동 패턴으로 통일한다. `singleClickEdit: true`는 전면 금지.

**이유:**

- 그리드마다 클릭 동작이 달라 사용자가 예측 불가능했음.
- 더블클릭 편집으로 통일하면 실수로 셀이 수정되는 것을 방지.
- 하이브리드 인라인 편집: 단순 필드는 더블클릭 셀 편집, 복잡 필드는 모달 유지.

**영향:** 27개 그리드 전환, "테이블 편집" 토글 버튼 제거, `frontend.md`에 표준 문서화.

---

## AssetRole.role_type 컬럼 제거 (2026-04)

**결정:** `asset_roles` 테이블에서 `role_type` 컬럼을 삭제한다.

**이유:**

- "firewall", "db" 같은 역할 유형은 카탈로그 분류체계(도메인/제품군)에서 이미 관리됨.
- 별도 자유 텍스트 필드는 데이터 품질을 보장할 수 없고, 분류체계와 중복.

**영향:** migration 0062, 스키마/서비스/라우터/프론트에서 role_type 참조 제거.

---

## common 모델의 infra FK 분리 (2026-04)

**결정:** `ContractPeriod.classification_layout_id` FK를 제거한다 (migration 0061).

**이유:**

- common 모듈 모델이 infra 모듈 테이블(`classification_layouts`)을 직접 참조하면 `core ← common ← {accounting, infra}` 규칙 위반.
- 분류 레이아웃 연결은 infra 서비스에서 동적으로 처리.

**영향:** FK 제거 + plain integer 컬럼으로 대체, infra 서비스에서 조인 로직 유지.
