# 프로젝트 개발 지침

> 항상 읽는 상위 지침. 사업 관리 통합 플랫폼 (공통 + 회계 + 인프라 모듈).
> 실행 방법/프로젝트 개요는 `README.md`, 작업별 세부 규칙은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`, 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.

---

## 작업별 상세 지침 (필요 시 참조)

- 백엔드(Python/FastAPI/SQLAlchemy) 작업 → `docs/guidelines/backend.md`
- 프론트엔드(JS/CSS/HTML) 작업 → `docs/guidelines/frontend.md`
- 인증/권한/보안 작업 → `docs/guidelines/auth.md`
- Excel Import/Export 작업 → `docs/guidelines/excel.md`

---

## 문서 계층 / Source of Truth

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태, 문서 안내
- `CLAUDE.md`: 항상 유지해야 하는 핵심 규칙, 문서 갱신 매핑, 완료 조건
- `docs/guidelines/*.md`: 작업 영역별 상세 규칙과 패턴
- `docs/DECISIONS.md`: 왜 그런 구조/정책을 택했는지에 대한 결정 기록
- `docs/KNOWN_ISSUES.md`: 아직 해소되지 않은 임시 제약, 우회, 운영상 주의점
- `docs/PROJECT_CONTEXT.md`: 도메인 배경, 사용자, 문제 정의
- `docs/PROJECT_STRUCTURE.md`: 파일 단위 프로젝트 구조와 모듈별 역할
- 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델의 1차 기준은 코드다 (`app/main.py`, `app/core/app_factory.py`, `app/core/startup/`, `app/modules/*/routers/`, `app/modules/*/models/`).
- README나 guideline은 코드의 세부 inventory를 중복 소유하지 않는다. 코드 경로를 안내하거나, 변경 판단 기준만 제공한다.

## 1. 도메인 용어 정의

### 회계모듈 (accounting)

| 용어 | 설명 |
| --- | --- |
| 계약 (Contract) | 수주 추진 또는 계약 완료된 사업 건 (원장의 1행) |
| 계약유형 (contract_type) | DB 동적 관리 (ContractTypeConfig 테이블). 기본: MA, SI, HW, TS, Prod, ETC |
| 진행단계 (stage) | 수주 확률: 계약완료, 90%, 70%, 50%, 10%, 실주 |
| 계획 여부 (is_planned) | 연초 보고 사업 여부 (ContractPeriod). True=계획사업, False=수시사업 |
| 실주 | stage 값. 수주 실패 건. 매출 목표 집계 시 손실 매출로 분류 |
| 계약기간 (ContractPeriod) | 계약 주기 단위 버전. 달력 연도가 아닌 계약 시작 연도 기준 |
| 담당자 (ContractContact) | Period별 영업/세금계산서 담당자. ContractPeriod 레벨에 귀속 |
| 거래처 (Customer) | 매출처(고객사) 또는 매입처(공급사) |
| 매출처 (Period.customer) | ContractPeriod별 매출처. 미지정 시 Contract.end_customer 사용 |
| 입금 매칭 (ReceiptMatch) | Receipt를 매출 라인(TransactionLine)에 매핑. FIFO 자동(귀속기간 내) + 수동 |
| 선수금 | 입금 배분 합계 > 매출 확정 합계일 때의 초과 금액 (AR 음수) |
| GP | Gross Profit = 매출 합계 - 매입 합계 |
| GP% | GP / 매출 x 100 |
| 미수금 | 이번 달까지 도래한 매출 확정 합계 - 매칭완료(ReceiptMatch) 합계. 사업 상세 GP 요약에서는 미래 귀속월 제외. 사업 상세, 대시보드, 보고서, Excel Export 모두 동일 공식을 사용 |
| 용어 설정 (TermConfig) | 관리자 커스터마이징 가능한 UI 용어 라벨 (term_configs 테이블) |

### 인프라모듈 (infra)

| 용어 | 설명 |
| --- | --- |
| 프로젝트 (Project) | 기술 인벤토리를 관리하는 최상위 단위 |
| 프로젝트 단계 (ProjectPhase) | 분석, 설계, 구축, 시험, 안정화 등 진행 단계 |
| 산출물 (Deliverable) | 프로젝트 단계별 제출 대상 문서/결과물 |
| 자산 (Asset) | 서버, 네트워크 장비, 보안 장비 등 기술 자산 |
| IP 대역 (IpSubnet) | 프로젝트 범위의 IP 대역, 역할/지역/상대국 등 메타데이터 포함 |
| IP 인벤토리 (AssetIP) | Asset에 연결된 IP 정보, IpSubnet 참조 가능 |
| 포트맵 (PortMap) | 자산 간 통신 관계 |
| 정책 정의 (PolicyDefinition) | 적용 기준이 되는 정책 원본 |
| 정책 적용 상태 (PolicyAssignment) | 프로젝트/자산 단위 정책 준수 현황 |
| 자산 담당자 매핑 (AssetContact) | 특정 자산과 담당자(CustomerContact)의 역할 연결 |
| 프로젝트-자산 연결 (ProjectAsset) | Asset↔Project N:M 연결. role, note 포함 |
| 자산 관계 (AssetRelation) | 자산 간 관계(parent-child, cluster, ha-pair 등) |
| 프로젝트 업체 (ProjectCustomer) | 프로젝트별 업체 역할(고객사/수행사/유지보수사/통신사/벤더) |
| 프로젝트 담당자 (ProjectCustomerContact) | 프로젝트별 담당자 역할(고객PM/수행PM/구축엔지니어 등) |
| Pin 프로젝트 | UserPreference 기반 사용자별 고정 프로젝트. topbar 뱃지 표시, 전 페이지 기본 선택 |

### 공통모듈 (common)

| 용어 | 설명 |
| --- | --- |
| 거래처 (Customer) | 고객사, 공급사, 유지보수사, 통신사 등. 회계/인프라 모듈이 공유 |
| 거래처 담당자 (CustomerContact) | 거래처 소속 담당자 |
| 역할 (Role) | RBAC 역할. permissions JSON으로 모듈별 접근 수준 관리 |

---

## 2. 코드 규칙

- **코드 일관성을 기능 추가 속도보다 우선한다.** 동일 문제 해결 시 기존 패턴을 우선 사용하고, 새로운 구조 도입은 최소화한다.
- Python 버전: 3.11 이상
- DB: PostgreSQL 16
- 포매터: `black`, 린터: `ruff`
- 타입 힌트를 모든 함수에 명시한다.
- Pydantic 스키마는 `app/modules/{module}/schemas/` 디렉토리에 정의한다. 라우터 파일에 스키마 클래스를 직접 정의하지 않는다.
- Pydantic 스키마로 입출력 유효성 검사를 수행한다.
  - enum 성격의 필드는 `Literal` 타입으로 정의 (예: `Stage = Literal["10%", "50%", ...]`)
  - 계약유형(contract_type)은 DB 동적 관리 (`ContractTypeConfig` 테이블) — `Literal` 대신 `str` + 런타임 검증
  - 날짜/월 필드는 `@field_validator` + `app/core/_normalize.py`로 정규화 및 검증
    - `normalize_month()`: `2501`, `202501`, `2025-01` -> `2025-01-01`
    - `normalize_date()`: `250115`, `20250115`, `2025-1-5` -> `2025-01-15`
    - `/` 구분자도 자동 변환, 2자리 연도(00-79 -> 2000s) 지원
- 라우터는 기능 단위로 분리한다 (예: `routers/contracts.py`, `routers/customers.py`).
- 서비스도 도메인 단위로 분리한다. 하나의 서비스 파일이 비대해지면(~500줄 이상) 엔티티별로 분리하고, 교차 도메인 공유 함수는 `_` 접두사 헬퍼 모듈(예: `_contract_helpers.py`)에 둔다.
- 서비스 레이어에 비즈니스 로직을 집중시키고, 라우터는 얇게 유지한다.
  - 라우터는 요청 파라미터 전달과 응답 선언에 집중하고, 조회/권한/업로드 검증/ORM->Schema 변환은 서비스에 위임한다.
  - 라우터에서 `if not obj: raise HTTPException(...)`, `db.get()`, `db.query()`, `_to_read()` 같은 패턴을 직접 두지 않는다.
  - 서비스에서 커스텀 예외를 발생시키고, 전역 핸들러(`app/core/app_factory.py`)가 HTTP 응답으로 자동 변환한다.
  - 계약/기간 단위 조회/생성/수정/삭제의 접근 권한 검사는 서비스가 최종 책임진다. 라우터는 `current_user`와 입력값만 전달한다.
  - 서비스는 데이터 scope 권한과 기능 action 권한(예: 삭제 가능 여부)을 모두 최종 검증한다.
  - 단건 수정/삭제처럼 path에 상위 계약 ID가 없는 엔드포인트도 서비스에서 대상 리소스의 계약/소유 범위를 역추적해 권한을 확인한다.
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식(`tbl.select()`, `tbl.insert()`)을 사용한다.
- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다. 초기 관리자처럼 설치 시점에 필요한 값은 환경변수 bootstrap 절차를 문서화한다.
- 비밀번호 정책은 `settings` + `app/core/config.py` 기본값으로 관리한다. 동적 정책 검증은 서비스 레이어에서 현재 설정값을 조회해 수행하고, 라우터/템플릿은 그 값을 표시만 한다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결.

### 모듈 구조 및 import 규칙

```text
app/
├── main.py                          # ENABLED_MODULES 기반 동적 모듈 등록
├── core/                            # 모듈-독립 인프라 (누구든 import 가능)
│   ├── app_factory.py, config.py, database.py, exceptions.py
│   ├── auth/                        # 인증 미들웨어, 세션, 패스워드, RBAC
│   └── startup/                     # lifespan, DB init, bootstrap
├── modules/
│   ├── common/                      # 항상 활성 (accounting, infra가 import 가능)
│   ├── accounting/                  # common만 참조 가능
│   └── infra/                       # common만 참조 가능
```

**모듈 간 import 규칙:**

```text
core/              <- 누구든 import 가능
modules/common/    <- accounting, infra가 import 가능
modules/accounting <- accounting 내부에서만
modules/infra      <- infra 내부에서만
accounting <-> infra   절대 금지
```

`ruff` 또는 `import-linter` 설정과 `test_module_isolation.py`로 CI에서 강제한다.

### 모듈 활성화

`ENABLED_MODULES` 환경변수로 활성 모듈을 제어한다.

```bash
ENABLED_MODULES=common,accounting,infra   # 본사 전체
ENABLED_MODULES=common,infra              # 현장 standalone
ENABLED_MODULES=common,accounting         # 영업 전용
```

- 모든 모델은 항상 import (Alembic 정합성을 위해 비활성 모듈 테이블도 DB에 존재)
- 라우터는 활성 모듈만 등록 (`ENABLED_MODULES`에 따라 `app.include_router()` 호출)
- 템플릿 로더에 활성 모듈 경로만 추가 (Jinja2 `ChoiceLoader`)

### 코드 변경 시 문서 갱신 규칙

아래 매핑 표에 따라 변경 의미에 맞는 문서만 갱신한다. 세부 모델/API/파일 목록 자체는 코드가 1차 기준이지만, 실행 절차/권한 정책/운영 제약/핵심 규칙이 바뀌면 해당 문서를 함께 갱신한다.

  | 변경 유형 | 갱신 대상 |
  | --------- | --------- |
  | 비즈니스 규칙 변경 | CLAUDE.md SS6 데이터 원칙 |
  | 코딩 패턴/규칙 변경 | CLAUDE.md 해당 섹션, `docs/guidelines/backend.md` |
  | 테스트 전략/회귀 범위 변경 | CLAUDE.md SS7 테스트/확장성 |
  | 권한 변경 | `docs/guidelines/auth.md` |
  | 프론트엔드 패턴 변경 | `docs/guidelines/frontend.md` |
  | Excel Import/Export 변경 | `docs/guidelines/excel.md` |
  | startup/bootstrap/migration/배포 초기화 흐름 변경 | `docs/DECISIONS.md`, 필요 시 `README.md` 실행/초기 설정 |
  | 공개 엔드포인트/인증 흐름 변경 | `docs/guidelines/auth.md`, 필요 시 `README.md` |
  | 아키텍처 결정 | `docs/DECISIONS.md` (추가 전용) |
  | 임시 우회/제약 추가 | `docs/KNOWN_ISSUES.md` |
  | 임시 우회 해소 | `docs/KNOWN_ISSUES.md` (항목 삭제) |
  | 외부 사용자가 알아야 하는 실행/운영 방법 변경 | `README.md` |
  | 파일/디렉토리 추가/삭제 | `docs/PROJECT_STRUCTURE.md` |
  | 모델/API/파일 구조 세부 변경 | 문서 갱신 기본 불필요 (코드가 source of truth) |

---

## 3. 명명 / 인터페이스 규칙

- 백엔드 파일명, Python 명명, API 라우트, 도메인 용어 통일 규칙은 `docs/guidelines/backend.md`를 따른다.
- 프론트엔드(JS/HTML/CSS) 명명 및 스타일링 규칙은 `docs/guidelines/frontend.md`를 따른다.
- 위 가이드라인은 모든 모듈(common, accounting, infra)에 공통으로 적용한다.
- 상위 지침에는 "어떤 세부 규칙을 어디서 찾는지"만 남기고, 작업 중 반복 확인이 필요한 상세 naming inventory는 하위 guideline이 소유한다.

---

## 4. 예외 처리

- 커스텀 예외: `app/core/exceptions.py`
  - `UnauthorizedError`->401, `NotFoundError`->404, `BusinessRuleError`->403, `DuplicateError`->409, `PermissionDeniedError`->403, `ValidationError`->422
- 서비스 함수는 `None`/`False` 반환 대신 예외를 발생시킨다.
- 서비스 함수는 `ValueError` 등 표준 예외 대신 커스텀 예외(`BusinessRuleError` 등)를 발생시킨다. 라우터에서 `try-except`로 변환하는 패턴 금지.
- 라우터는 예외를 직접 처리하지 않고 전역 핸들러에 위임한다.

---

## 5. 감사 로그

- 모델: `app/modules/common/models/audit_log.py`, 유틸: `app/modules/common/services/audit.py`
- `audit.log(db, user_id=..., action=..., entity_type=..., ...)`
- `flush`만 수행, `commit`은 호출자 트랜잭션에 맡김

---

## 6. 데이터 원칙

### 회계모듈

- 계약 삭제는 **관리자(admin) 전용**. 일반 사용자는 상태를 cancelled로 변경.
- 금액은 **정수(원 단위, VAT 별도)**. 부동소수점 사용 금지.
- 월 범위는 `YYYY-MM-01` 문자열로 저장.
- 생성일시/수정일시는 `TimestampMixin`으로 공통 적용.
- `created_by`는 라우터에서 `get_current_user`를 통해 서비스로 전달.
- FIFO 자동 배분은 입금의 `revenue_month`가 속하는 **ContractPeriod 범위 내** 매출만 대상. 기간 간 배분 격리.
- 완료된 귀속기간(`is_completed`)의 데이터는 생성/수정/삭제 불가 (프론트+백엔드 이중 보호).
- 미수금은 모든 화면/보고서/Export에서 `매출 확정 - 배분완료(ReceiptMatch)` 단일 공식을 유지한다. raw `Receipt.amount`는 입금 지표로만 사용한다.

### 인프라모듈

- `Project`는 상위 컨텍스트이고, 기술 인벤토리의 탐색 중심은 `Asset`이다.
- `Asset`을 중심으로 `AssetIP`, `PortMap`, `AssetContact`가 연결된다.
- `Asset`은 `ProjectAsset` N:M 테이블을 통해 여러 프로젝트에 연결 가능. 기존 `Asset.project_id` FK는 병행 유지.
- `AssetRelation`으로 자산 간 관계(parent-child, cluster, ha-pair 등)를 표현한다.
- `ProjectCustomer`로 프로젝트-업체 역할(고객사/수행사/유지보수사/통신사/벤더)을 관리한다.
- `ProjectCustomerContact`로 프로젝트-담당자 역할(고객PM/수행PM/구축엔지니어 등)을 관리한다. `ProjectCustomer`에 종속(CASCADE 삭제).
- Pin 프로젝트: `UserPreference`(key=`infra.pinned_project_id`)로 사용자별 고정 프로젝트를 DB 저장. 인프라 전 페이지에서 기본 컨텍스트로 동작.
- 정책은 반드시 `PolicyDefinition`과 `PolicyAssignment`로 분리한다.
- IP 중복 검증은 최소한 프로젝트 범위 내에서 수행한다.
- 자산명은 프로젝트 내 unique를 기본 원칙으로 한다.
- 상태값은 문자열 하드코딩 대신 enum으로 통일한다.
- 포트맵은 자산 간 연결뿐 아니라 외부 구간 표현을 위해 `src_asset_id`, `dst_asset_id`를 nullable로 둘 수 있다.
- 정책 적용 상태는 `not_checked`, `compliant`, `non_compliant`, `exception`, `not_applicable` 범위를 기본값으로 사용한다.
- 연락처는 거래처에 소속되고, 자산에는 매핑(AssetContact)으로 연결한다.
- 인프라 CRUD(프로젝트/자산/IP대역/포트맵/정책)는 `audit.log()`로 감사 로그를 기록한다.
- Excel Export는 프로젝트 단위 3시트(Inventory/IP대역/Portmap)로 내보낸다.

### 공통

- 생성일시/수정일시는 `TimestampMixin`으로 공통 적용.
- `created_by`는 라우터에서 `get_current_user`를 통해 서비스로 전달.

---

## 7. 테스트/확장성

- GP/GP%/미수금 계산, CRUD 플로우, Excel Import: 단위/통합 테스트 필수. 프레임워크: `pytest`.
- DB fixture: PostgreSQL 테스트 컨테이너 (`testcontainers-python` 또는 테스트용 별도 DB).
- 테스트 디렉토리는 모듈별로 구성한다:

  ```text
  tests/
  ├── conftest.py              # DB 세션, 기본 유저/역할 fixture
  ├── common/                  # 공통모듈 테스트
  ├── accounting/              # 회계모듈 테스트
  ├── infra/                   # 인프라모듈 테스트
  ├── test_database.py         # 스키마 정합성
  ├── test_startup.py          # bootstrap, lifespan
  └── test_module_isolation.py # accounting <-> infra import 금지 검증
  ```

- 기본 회귀 테스트는 metrics/contract/importer/dashboard/receipt_match/report/auth/database/startup/transaction safety 범위를 포함한다. 세부 파일 목록은 `tests/`가 1차 기준이다.
- 인프라모듈 테스트 범위: 프로젝트 CRUD, 자산 CRUD, IP 중복 검증, 포트맵 연결 검증, 정책 정의/적용 상태 CRUD, 자산 담당자(AssetContact) 매핑.
- CRUD/설정 변경 회귀에는 삭제 경로, 다중 필드 업데이트, 부분 실패 시 롤백 같은 원자성 시나리오를 포함한다.
- 권한 회귀 테스트는 router 응답뿐 아니라 service 직접 호출 경로의 action 권한과 scope 차단도 포함한다.
- 완료된 귀속기간 보호, FIFO 배분 격리, ReceiptMatch 권한, 대시보드 집계(`is_planned`, `실주`, 목표 vs 실적, 월/분기/반기/연 재집계), 보고서/Excel Export의 미수금/합계 행 규칙은 위 테스트군으로 회귀를 보호한다.
- 모듈 격리 테스트 (`test_module_isolation.py`): accounting <-> infra 간 import 금지를 AST 파싱으로 검증.
- 모듈 등록 테스트: `ENABLED_MODULES`에 따른 라우터 등록/미등록 검증.
- RBAC 테스트: 역할별 모듈 접근, read/full 권한 수준 동작 검증.
- DB 스키마 변경은 Alembic(`alembic/versions/`)으로 관리한다.
  - 새 테이블/컬럼 추가 시: `alembic revision --autogenerate -m "설명"` -> `upgrade()`에 `inspector` 존재 여부 체크 권장
  - startup 시 `app/core/startup/database_init.py`가 자동으로 `alembic upgrade head` 실행
  - 빈 DB도 `stamp`가 아니라 `upgrade` 대상으로 처리한다.
  - 단일 migration 체인 유지. 비활성 모듈의 테이블도 스키마에 존재.
  - fresh production startup 경로는 회귀 테스트로 보호한다.
- 설정값(세율, 날짜 형식 등)은 코드가 아닌 설정 파일에서 관리.
- API는 `/api/v1/` 버전 prefix를 유지.

---

## 8. 완료 조건 (Definition of Done)

코드 변경이 "완료"되려면 다음을 모두 충족해야 한다:

1. 코드 변경 완료
2. 관련 테스트 통과 (새 기능은 테스트 추가)
3. 변경 유형을 식별하고 SS2 매핑 표의 필수 문서를 갱신 완료
4. 해결된 KNOWN_ISSUES 항목이 있으면 삭제 완료
5. 문서에 적은 경로/엔드포인트/권한/초기화 절차가 코드와 일치함을 확인

### 문서 정합성 체크리스트

변경 커밋 전 아래를 확인한다:

- [ ] KNOWN_ISSUES.md에 이번 변경으로 해소된 항목이 있는가? -> 삭제
- [ ] 비즈니스 규칙을 변경했는가? -> CLAUDE.md SS6 확인
- [ ] 권한 로직을 변경했는가? -> `docs/guidelines/auth.md` 확인
- [ ] 공개 엔드포인트/로그인 흐름을 변경했는가? -> `docs/guidelines/auth.md`, 필요 시 `README.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? -> `docs/guidelines/frontend.md` 확인
- [ ] Excel Import/Export 계약을 변경했는가? -> `docs/guidelines/excel.md` 확인
- [ ] startup/bootstrap/migration/초기 설정 흐름을 변경했는가? -> `docs/DECISIONS.md`, 필요 시 `README.md` 확인
- [ ] 외부 사용자가 알아야 하는 실행/운영 방법을 바꿨는가? -> `README.md` 확인
- [ ] 문서에 적은 경로/엔드포인트/권한명이 실제 코드와 일치하는가?

### 세션 컨텍스트 관리

장시간 작업 시 대화 컨텍스트가 커져 API 과부하(529 에러)나 성능 저하가 발생할 수 있다. 다음 규칙을 적용한다:

- **API 529 에러가 2회 연속 발생하면** 즉시 작업을 중단하고 세션 전환을 제안한다.
- **에이전트는 항상 1개씩 순차 파견**한다. 병렬 파견은 API 부하를 가중시킨다.
- **단순 HTML/JS/CSS 수정은 에이전트 파견 대신 직접 처리**한다.
- **대규모 Task 3개 이상 완료 후** 에이전트 파견 전에 컨텍스트 크기를 고려하고, 필요 시 세션 전환을 제안한다.
- 세션 전환 시: memory에 진행 상태(`project_active_plan.md`)를 저장하고, 사용자에게 새 세션 시작을 안내한다. 새 세션에서는 plan 파일과 memory를 읽어 이어서 진행한다.

### 마이그레이션 기간 예외 (완료 시 삭제)

현재 모듈화 마이그레이션이 진행 중이다 (`docs/superpowers/plans/2026-03-18-modular-migration-plan.md` 참조).

- 지침은 목표 구조를 반영하도록 **선행 수정**될 수 있다. 코드가 아직 구 구조일 수 있다.
- 코드-문서 경로 불일치가 있더라도, 마이그레이션 계획에 따른 의도적 불일치이면 문서를 되돌리지 않는다.
- SS8 정합성 체크리스트의 "경로/엔드포인트가 코드와 일치하는가" 항목은 해당 단계의 코드 이동이 완료된 후에만 적용한다.
- 미구현/부분구현 코드를 근거로 지침을 수정하지 않는다. 단, 지침 간 상호 모순 또는 지침이 구현을 차단하는 경우에 한해 충돌을 보고하고 사용자 확인을 요청할 수 있다.
- 마이그레이션 완료 후 이 섹션을 삭제한다.
