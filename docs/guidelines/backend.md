# 백엔드 작업 지침

> Python/FastAPI/SQLAlchemy 백엔드 작업 시 참조. 모든 모듈(common, accounting, infra)에 공통 적용.

---

## 파일 / 모듈 명명 규칙

| 레이어 | 패턴 | 예시 |
| ------ | ---- | --- |
| 모델/스키마/서비스 | 단수 snake_case | `contract.py`, `transaction_line.py`, `asset.py` |
| 서비스 내부 헬퍼 | `_` 접두사 + snake_case | `_contract_helpers.py` |
| 라우터 | 복수 snake_case | `contracts.py`, `customers.py`, `assets.py` |

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
- 비-CRUD 동작은 `POST /{리소스}/{id}/{동작}` 패턴을 사용한다
- 라우터는 `current_user`와 입력값을 service에 전달하고, access helper 호출과 권한 최종 판단은 service가 소유한다.

## 도메인 용어 통일

| 개념 | 표준 용어 (DB/API) | 비고 |
| ---- | ----------------- | ---- |
| 거래처 | `customer` | `counterparty`, `company`, `partner` 사용 금지 |
| END 고객사 | `end_customer` | Contract에 직접 연결된 최종 고객 |
| 금액 필드 접미사 | `_amount` | `_total` 사용 금지. `expected_revenue_total`, `expected_gp_total`은 레거시 |
| 월 | `_month` (YYYY-MM-01) | `forecast_month`, `revenue_month` |
| 구분 (매출/매입) | `line_type` (revenue/cost) | DB 영문, UI 한글 |
