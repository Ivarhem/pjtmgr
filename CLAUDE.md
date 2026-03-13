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
| 진행단계 (stage) | 수주 확률: 계약완료, 90%, 70%, 50%, 10% |
| 계약기간 (ContractPeriod) | 계약 주기 단위 버전. 달력 연도가 아닌 계약 시작 연도 기준 |
| 담당자 (ContractContact) | Period별 영업/세금계산서 담당자. ContractPeriod 레벨에 귀속 |
| 거래처 (Customer) | 매출처(고객사) 또는 매입처(공급사) |
| 매출처 (Period.customer) | ContractPeriod별 매출처. 미지정 시 Contract.end_customer 사용 |
| 입금 매칭 (ReceiptMatch) | Receipt를 매출 라인(TransactionLine)에 매핑. FIFO 자동(귀속기간 내) + 수동 |
| 선수금 | 입금 배분 합계 > 매출 확정 합계일 때의 초과 금액 (AR 음수) |
| GP | Gross Profit = 매출 합계 - 매입 합계 |
| GP% | GP ÷ 매출 × 100 |
| 미수금 | 매출 확정 합계 - 매칭완료(ReceiptMatch) 합계 |
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
- 서비스 레이어에 비즈니스 로직을 집중시키고, 라우터는 얇게 유지한다.
  - 라우터에서 `if not obj: raise HTTPException(...)` 패턴 사용 금지
  - 라우터에서 `db.get()` / `db.query()` 직접 호출 금지 — 조회·권한 체크 포함 모든 로직은 서비스에 위임
  - 서비스에서 커스텀 예외 발생, 전역 핸들러(`app/main.py`)가 HTTP 응답으로 자동 변환
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식(`tbl.select()`, `tbl.insert()`)을 사용한다.
  - 예외적으로 런타임 마이그레이션 같은 불가피한 raw SQL은 허용하되, 식별자는 화이트리스트/정규식 검증으로 제한한다.
- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다. 초기 관리자처럼 설치 시점에 필요한 값은 환경변수 bootstrap 절차를 문서화한다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결.
- 코드 변경 시 관련 문서를 함께 업데이트한다 (API 추가 → README API 목록).

---

## 3. 명명 규칙

### 파일명

| 레이어 | 패턴 | 예시 |
| ------ | ---- | --- |
| 모델/스키마/서비스 | 단수 snake_case | `contract.py`, `transaction_line.py` |
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

---

## 7. 테스트·확장성

- GP/GP%/미수금 계산, CRUD 플로우, Excel Import: 단위/통합 테스트 필수. 프레임워크: `pytest`.
- 기본 회귀 테스트는 `tests/test_metrics.py`, `tests/test_contract_service.py`, `tests/test_importer.py`에서 관리한다.
- DB 스키마 변경은 마이그레이션 도구(Alembic)로 관리.
- 설정값(세율, 날짜 형식 등)은 코드가 아닌 설정 파일에서 관리.
- API는 `/api/v1/` 버전 prefix를 유지.
