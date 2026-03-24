# 백엔드 작업 지침

> Python/FastAPI/SQLAlchemy 백엔드 작업 시 참조. 모든 모듈(common, accounting, infra)에 공통 적용.

---

## 파일 / 모듈 명명 규칙

| 레이어 | 패턴 | 예시 |
| ------ | ---- | --- |
| 모델/스키마/서비스 | 단수 snake_case | `contract.py`, `transaction_line.py`, `asset.py` |
| 서비스 내부 헬퍼 | `_` 접두사 + snake_case | `_contract_helpers.py` |
| 라우터 | 복수 snake_case | `contracts.py`, `partners.py`, `assets.py` |

## 모듈별 파일 배치

```text
app/modules/{module}/
├── models/          # ORM 모델
├── schemas/         # Pydantic 스키마
├── services/        # 비즈니스 로직
├── routers/         # API 라우터
└── templates/       # Jinja2 템플릿 (모듈별)
```

- 스키마는 `app/modules/{module}/schemas/`에 정의한다. 라우터 파일에 스키마 클래스를 직접 정의하지 않는다.
- 공통 유틸(`_normalize.py` 등)은 `app/core/`에 배치한다.

## 모듈 간 import 규칙

```text
core/              <- 누구든 import 가능
modules/common/    <- accounting, infra가 import 가능
modules/accounting <- accounting 내부에서만
modules/infra      <- infra 내부에서만
accounting <-> infra   절대 금지
```

- 모듈 경계를 넘는 import는 위 규칙을 엄격히 따른다.
- `test_module_isolation.py`로 CI에서 강제한다.

## Python 규칙

- 모델 클래스: `PascalCase` 단수
- 테이블명: 복수 snake_case
- 스키마 클래스: `{Model}{Operation}` (`Create`, `Update`, `Read`)
- 서비스 함수(CRUD): `create_*`, `list_*`, `get_*`, `update_*`, `delete_*`
- `get_all`, `add`, `set` 사용 금지
- 비-CRUD 서비스 함수는 동사_목적어 형태 사용
- private 함수는 `_` 접두사 사용
- SQLAlchemy Boolean 필터는 `.is_(True)`, `.is_(False)` 사용

## API 라우트 규칙

- `prefix="/api/v1/{리소스}"` 사용
- 여러 리소스를 하나의 라우터에서 처리할 때만 `prefix="/api/v1"` 사용
- 리소스 URL은 복수 kebab-case 사용
- 중첩 리소스는 `/{부모}/{id}/{자식}` 패턴 사용
- CRUD는 GET/POST/PATCH/DELETE를 사용하고 PUT은 사용하지 않는다
- Upsert(생성-또는-갱신) 동작도 POST를 사용한다 (예: `POST /{부모}/{id}/{하위리소스}`)
- 비-CRUD 동작은 `POST /{리소스}/{id}/{동작}` 패턴을 사용한다
- 라우터는 `current_user`와 입력값을 service에 전달하고, access helper 호출과 권한 최종 판단은 service가 소유한다.

## 도메인 용어 통일

| 개념 | 표준 용어 (DB/API) | 비고 |
| ---- | ----------------- | ---- |
| 업체 | `partner` | `counterparty`, `company`, `customer` 사용 금지 |
| END 고객사 | `end_partner` | Contract에 직접 연결된 최종 고객 |
| 금액 필드 접미사 | `_amount` | `_total` 사용 금지. `expected_revenue_total`, `expected_gp_total`은 레거시 |
| 월 | `_month` (YYYY-MM-01) | `forecast_month`, `revenue_month` |
| 구분 (매출/매입) | `line_type` (revenue/cost) | DB 영문, UI 한글 |

---

## 레이어 분리 규칙

### 라우터 (얇게 유지)

- 라우터는 요청 파라미터 전달과 응답 선언에 집중하고, 조회/권한/업로드 검증/ORM→Schema 변환은 서비스에 위임한다.
- 라우터에서 `if not obj: raise HTTPException(...)`, `db.get()`, `db.query()`, `_to_read()` 같은 패턴을 직접 두지 않는다.

### 서비스 (비즈니스 로직 집중)

- 서비스도 도메인 단위로 분리한다. 하나의 서비스 파일이 비대해지면(~500줄 이상) 엔티티별로 분리하고, 교차 도메인 공유 함수는 `_` 접두사 헬퍼 모듈(예: `_contract_helpers.py`)에 둔다.
- 서비스에서 커스텀 예외를 발생시키고, 전역 핸들러(`app/core/app_factory.py`)가 HTTP 응답으로 자동 변환한다.
- 계약/기간 단위 조회/생성/수정/삭제의 접근 권한 검사는 서비스가 최종 책임진다. 라우터는 `current_user`와 입력값만 전달한다.
- 서비스는 데이터 scope 권한과 기능 action 권한(예: 삭제 가능 여부)을 모두 최종 검증한다.
- 단건 수정/삭제처럼 path에 상위 계약 ID가 없는 엔드포인트도 서비스에서 대상 리소스의 계약/소유 범위를 역추적해 권한을 확인한다.

## Pydantic / 유효성 검사

- Pydantic 스키마로 입출력 유효성 검사를 수행한다.
  - enum 성격의 필드는 `Literal` 타입으로 정의 (예: `Stage = Literal["10%", "50%", ...]`)
  - 계약유형(contract_type)은 DB 동적 관리 (`ContractTypeConfig` 테이블) — `Literal` 대신 `str` + 런타임 검증
  - 날짜/월 필드는 `@field_validator` + `app/core/_normalize.py`로 정규화 및 검증
    - `normalize_month()`: `2501`, `202501`, `2025-01` → `2025-01-01`
    - `normalize_date()`: `250115`, `20250115`, `2025-1-5` → `2025-01-15`
    - `/` 구분자도 자동 변환, 2자리 연도(00-79 → 2000s) 지원

## 예외 처리

- 커스텀 예외: `app/core/exceptions.py`
  - `UnauthorizedError`→401, `NotFoundError`→404, `BusinessRuleError`→403, `DuplicateError`→409, `PermissionDeniedError`→403, `ValidationError`→422
- 서비스 함수는 `None`/`False` 반환 대신 예외를 발생시킨다.
- 서비스 함수는 `ValueError` 등 표준 예외 대신 커스텀 예외(`BusinessRuleError` 등)를 발생시킨다. 라우터에서 `try-except`로 변환하는 패턴 금지.
- 라우터는 예외를 직접 처리하지 않고 전역 핸들러에 위임한다.

## 감사 로그

- 모델: `app/modules/common/models/audit_log.py`, 유틸: `app/modules/common/services/audit.py`
- `audit.log(db, user_id=..., action=..., entity_type=..., ...)`
- `flush`만 수행, `commit`은 호출자 트랜잭션에 맡김

## 환경변수 / 보안

- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다. 초기 관리자처럼 설치 시점에 필요한 값은 환경변수 bootstrap 절차를 문서화한다.
- 비밀번호 정책은 `settings` + `app/core/config.py` 기본값으로 관리한다. 동적 정책 검증은 서비스 레이어에서 현재 설정값을 조회해 수행하고, 라우터/템플릿은 그 값을 표시만 한다.
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식을 사용한다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결.
