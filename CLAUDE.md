# 프로젝트 개발 지침

> 프로젝트 구조·아키텍처·데이터 모델·기능 현황·향후 계획은 `README.md` 참조.

---

## 작업별 상세 지침 (필요 시 참조)

- 프론트엔드(JS/CSS/HTML) 작업 → `docs/guidelines/frontend.md`
- 인증/권한/보안 작업 → `docs/guidelines/auth.md`
- Excel Import/Export 작업 → `docs/guidelines/excel.md`

---

## 1. 도메인 용어 정의

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
| GP% | GP ÷ 매출 × 100 |
| 미수금 | 이번 달까지 도래한 매출 확정 합계 - 매칭완료(ReceiptMatch) 합계. 사업 상세 GP 요약에서는 미래 귀속월 제외. 사업 상세, 대시보드, 보고서, Excel Export 모두 동일 공식을 사용 |
| 용어 설정 (TermConfig) | 관리자 커스터마이징 가능한 UI 용어 라벨 (term_configs 테이블) |

---

## 2. 코드 규칙

- **코드 일관성을 기능 추가 속도보다 우선한다.** 동일 문제 해결 시 기존 패턴을 우선 사용하고, 새로운 구조 도입은 최소화한다.
- Python 버전: 3.11 이상
- 포매터: `black`, 린터: `ruff`
- 타입 힌트를 모든 함수에 명시한다.
- Pydantic 스키마는 `app/schemas/` 디렉토리에 정의한다. 라우터 파일에 스키마 클래스를 직접 정의하지 않는다.
- Pydantic 스키마로 입출력 유효성 검사를 수행한다.
  - enum 성격의 필드는 `Literal` 타입으로 정의 (예: `Stage = Literal["10%", "50%", ...]`)
  - 계약유형(contract_type)은 DB 동적 관리 (`ContractTypeConfig` 테이블) — `Literal` 대신 `str` + 런타임 검증
  - 날짜/월 필드는 `@field_validator` + `_normalize.py`로 정규화 및 검증
    - `normalize_month()`: `2501`, `202501`, `2025-01` → `2025-01-01`
    - `normalize_date()`: `250115`, `20250115`, `2025-1-5` → `2025-01-15`
    - `/` 구분자도 자동 변환, 2자리 연도(00-79 → 2000s) 지원
- 라우터는 기능 단위로 분리한다 (예: `routers/contracts.py`, `routers/customers.py`).
- 서비스도 도메인 단위로 분리한다. 하나의 서비스 파일이 비대해지면(~500줄 이상) 엔티티별로 분리하고, 교차 도메인 공유 함수는 `_` 접두사 헬퍼 모듈(예: `_contract_helpers.py`)에 둔다.
- 서비스 레이어에 비즈니스 로직을 집중시키고, 라우터는 얇게 유지한다.
  - 라우터는 요청 파라미터 전달과 응답 선언에 집중하고, 조회·권한·업로드 검증·ORM→Schema 변환은 서비스에 위임한다.
  - 라우터에서 `if not obj: raise HTTPException(...)`, `db.get()`, `db.query()`, `_to_read()` 같은 패턴을 직접 두지 않는다.
  - 서비스에서 커스텀 예외를 발생시키고, 전역 핸들러(`app/app_factory.py`)가 HTTP 응답으로 자동 변환한다.
  - 단건 수정/삭제처럼 path에 상위 계약 ID가 없는 엔드포인트도 서비스에서 대상 리소스의 계약/소유 범위를 역추적해 권한을 확인한다.
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식(`tbl.select()`, `tbl.insert()`)을 사용한다.
  - 예외적으로 `app/migrations_legacy.py`의 경량 마이그레이션은 불가피한 raw SQL을 허용하되, 식별자는 화이트리스트/정규식 검증으로 제한한다.
- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- `DATABASE_URL` 기반 설정은 특정 DB 전용 `connect_args`를 전역 고정하지 말고 backend별로 분기한다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다. 초기 관리자처럼 설치 시점에 필요한 값은 환경변수 bootstrap 절차를 문서화한다.
- 비밀번호 정책은 `settings` + `app/config.py` 기본값으로 관리한다. 동적 정책 검증은 서비스 레이어에서 현재 설정값을 조회해 수행하고, 라우터/템플릿은 그 값을 표시만 한다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결.
- **코드 변경 시 문서 갱신 규칙**: 아래 매핑 표에 따라 해당하는 문서만 갱신한다. 매핑에 없는 변경은 문서 갱신 불필요 (코드가 source of truth).

  | 변경 유형 | 갱신 대상 |
  | --------- | --------- |
  | 비즈니스 규칙 변경 | CLAUDE.md §6 데이터 원칙 |
  | 코딩 패턴/규칙 변경 | CLAUDE.md 해당 섹션 |
  | 테스트 파일 추가 | CLAUDE.md §7 테스트 파일 목록 |
  | 권한 변경 | `docs/guidelines/auth.md` |
  | 프론트엔드 패턴 변경 | `docs/guidelines/frontend.md` |
  | Excel Import/Export 변경 | `docs/guidelines/excel.md` |
  | 아키텍처 결정 | `docs/DECISIONS.md` (추가 전용) |
  | 임시 우회/제약 추가 | `docs/KNOWN_ISSUES.md` |
  | 임시 우회 해소 | `docs/KNOWN_ISSUES.md` (항목 삭제) |
  | 모델/API/파일 구조 변경 | 문서 갱신 불필요 (코드가 source of truth) |

---

## 3. 명명 규칙

### 파일명

| 레이어 | 패턴 | 예시 |
| ------ | ---- | --- |
| 모델/스키마/서비스 | 단수 snake_case | `contract.py`, `transaction_line.py` |
| 서비스 내부 헬퍼 | `_` 접두사 + snake_case | `_contract_helpers.py` (패키지 내부 전용) |
| 라우터 | 복수 snake_case | `contracts.py`, `customers.py`, `term_configs.py` |
| 템플릿/JS/CSS | 화면 단위 snake_case | `contract_detail.html`, `contract_detail.js` |

### Python (백엔드)

- **모델 클래스**: `PascalCase` 단수 — **테이블명**: 복수 snake_case
- **스키마 클래스**: `{Model}{Operation}` (Operation: `Create`, `Update`, `Read`)
- **서비스 함수 (CRUD)**: `create_*`, `list_*`, `get_*`, `update_*`, `delete_*`
  - `get_all` / `add` / `set` 사용 금지
- **서비스 함수 (비-CRUD)**: 동사_목적어 형태 (예: `move_period()`)
- **Private 함수**: `_` 접두사
- **SQLAlchemy Boolean 필터**: `.is_(True)` / `.is_(False)` 사용 (`== True` 금지)

### API 라우트

- `prefix="/api/v1/{리소스}"` 사용 (경로 하드코딩 금지)
  - 여러 리소스를 하나의 라우터에서 처리 시 `prefix="/api/v1"` 사용
- 리소스 URL: 복수 kebab-case (예: `/contract-periods`)
- 중첩 리소스: `/{부모}/{id}/{자식}` (예: `/contracts/{contract_id}/periods`)
- CRUD: GET/POST/PATCH/DELETE — **PUT 사용 금지**
- 비-CRUD 동작: `POST /{리소스}/{id}/{동작}`

### 도메인 용어 통일

| 개념 | 표준 용어 (DB/API) | 비고 |
| ---- | ----------------- | ---- |
| 거래처 | `customer` | `counterparty`, `company` 사용 금지 |
| END 고객사 | `end_customer` | Contract에 직접 연결된 최종 고객 |
| 금액 필드 접미사 | `_amount` | `_total` 사용 금지. 매출: `revenue_amount`, 매입: `cost_amount`. ※ `expected_revenue_total`, `expected_gp_total`은 레거시 — DB 마이그레이션 시 `_amount`로 변경 예정 |
| 월 | `_month` (YYYY-MM-01) | `forecast_month`, `revenue_month` |
| 구분 (매출/매입) | `line_type` (revenue/cost) | DB 영문, UI 한글 |

> 프론트엔드(JS/HTML/CSS) 명명 규칙은 `docs/guidelines/frontend.md` 참조.

---

## 4. 예외 처리

- 커스텀 예외: `app/exceptions.py`
  - `UnauthorizedError`→401, `NotFoundError`→404, `BusinessRuleError`→403, `DuplicateError`→409, `PermissionDeniedError`→403, `ValidationError`→422
- 서비스 함수는 `None`/`False` 반환 대신 예외를 발생시킨다.
- 서비스 함수는 `ValueError` 등 표준 예외 대신 커스텀 예외(`BusinessRuleError` 등)를 발생시킨다. 라우터에서 `try-except`로 변환하는 패턴 금지.
- 라우터는 예외를 직접 처리하지 않고 전역 핸들러에 위임한다.

---

## 5. 감사 로그

- 모델: `app/models/audit_log.py`, 유틸: `app/services/audit.py`
- `audit.log(db, user_id=..., action=..., entity_type=..., ...)`
- `flush`만 수행, `commit`은 호출자 트랜잭션에 맡김

---

## 6. 데이터 원칙

- 계약 삭제는 **관리자(admin) 전용**. 일반 사용자는 상태를 cancelled로 변경.
- 금액은 **정수(원 단위, VAT 별도)**. 부동소수점 사용 금지.
- 월 범위는 `YYYY-MM-01` 문자열로 저장.
- 생성일시·수정일시는 `TimestampMixin`으로 공통 적용.
- `created_by`는 라우터에서 `get_current_user`를 통해 서비스로 전달.
- FIFO 자동 배분은 입금의 `revenue_month`가 속하는 **ContractPeriod 범위 내** 매출만 대상. 기간 간 배분 격리.
- 완료된 귀속기간(`is_completed`)의 데이터는 생성/수정/삭제 불가 (프론트+백엔드 이중 보호).
- 미수금은 모든 화면/보고서/Export에서 `매출 확정 - 배분완료(ReceiptMatch)` 단일 공식을 유지한다. raw `Receipt.amount`는 입금 지표로만 사용한다.

---

## 7. 테스트·확장성

- GP/GP%/미수금 계산, CRUD 플로우, Excel Import: 단위/통합 테스트 필수. 프레임워크: `pytest`.
- 기본 회귀 테스트는 `tests/test_metrics.py`, `tests/test_contract_service.py`, `tests/test_importer.py`, `tests/test_dashboard_service.py`, `tests/test_receipt_match_service.py`, `tests/test_contract_schema.py`, `tests/test_report_service.py`, `tests/test_auth_service.py`, `tests/test_database.py`, `tests/test_startup.py`, `tests/test_transaction_safety.py`에서 관리한다.
- 완료된 귀속기간 보호, FIFO 배분 격리, ReceiptMatch 권한, 대시보드 집계(`is_planned`, `실주`, 목표 vs 실적, 월/분기/반기/연 재집계), 보고서/Excel Export의 미수금·합계 행 규칙은 위 테스트군으로 회귀를 보호한다.
- DB 스키마 변경은 Alembic(`alembic/versions/`)으로 관리한다. 기존 `app/migrations_legacy.py`는 레거시 호환용으로 유지.
  - 새 테이블/컬럼 추가 시: `alembic revision --autogenerate -m "설명"` → `upgrade()`에 `inspector` 존재 여부 체크 권장
  - startup 시 `app/startup/database_init.py`가 자동으로 `alembic upgrade head` 실행
- 설정값(세율, 날짜 형식 등)은 코드가 아닌 설정 파일에서 관리.
- API는 `/api/v1/` 버전 prefix를 유지.

---

## 8. 완료 조건 (Definition of Done)

코드 변경이 "완료"되려면 다음을 모두 충족해야 한다:

1. 코드 변경 완료
2. 관련 테스트 통과 (새 기능은 테스트 추가)
3. §2 매핑 표에 해당하는 문서가 있으면 갱신 완료
4. 해결된 KNOWN_ISSUES 항목이 있으면 삭제 완료

### 문서 정합성 체크리스트

변경 커밋 전 아래를 확인한다:

- [ ] KNOWN_ISSUES.md에 이번 변경으로 해소된 항목이 있는가? → 삭제
- [ ] 비즈니스 규칙을 변경했는가? → CLAUDE.md §6 확인
- [ ] 권한 로직을 변경했는가? → `docs/guidelines/auth.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? → `docs/guidelines/frontend.md` 확인
- [ ] 새 테스트 파일을 추가했는가? → CLAUDE.md §7 목록에 추가
