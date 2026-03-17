# 프로젝트 개발 지침

> 항상 읽는 상위 지침. 실행 방법/프로젝트 개요는 `README.md`, 작업별 세부 규칙은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`, 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.

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
- 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델의 1차 기준은 코드다 (`app/main.py`, `app/app_factory.py`, `app/startup/`, `app/routers/`, `app/models/`).
- README나 guideline은 코드의 세부 inventory를 중복 소유하지 않는다. 코드 경로를 안내하거나, 변경 판단 기준만 제공한다.

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
  - 계약/기간 단위 조회·생성·수정·삭제의 접근 권한 검사는 서비스가 최종 책임진다. 라우터는 `current_user`와 입력값만 전달한다.
  - 단건 수정/삭제처럼 path에 상위 계약 ID가 없는 엔드포인트도 서비스에서 대상 리소스의 계약/소유 범위를 역추적해 권한을 확인한다.
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식(`tbl.select()`, `tbl.insert()`)을 사용한다.
- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- `DATABASE_URL` 기반 설정은 특정 DB 전용 `connect_args`를 전역 고정하지 말고 backend별로 분기한다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다. 초기 관리자처럼 설치 시점에 필요한 값은 환경변수 bootstrap 절차를 문서화한다.
- 비밀번호 정책은 `settings` + `app/config.py` 기본값으로 관리한다. 동적 정책 검증은 서비스 레이어에서 현재 설정값을 조회해 수행하고, 라우터/템플릿은 그 값을 표시만 한다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결.
- **코드 변경 시 문서 갱신 규칙**: 아래 매핑 표에 따라 변경 의미에 맞는 문서만 갱신한다. 세부 모델/API/파일 목록 자체는 코드가 1차 기준이지만, 실행 절차/권한 정책/운영 제약/핵심 규칙이 바뀌면 해당 문서를 함께 갱신한다.

  | 변경 유형 | 갱신 대상 |
  | --------- | --------- |
  | 비즈니스 규칙 변경 | CLAUDE.md §6 데이터 원칙 |
  | 코딩 패턴/규칙 변경 | CLAUDE.md 해당 섹션, `docs/guidelines/backend.md` |
  | 테스트 전략/회귀 범위 변경 | CLAUDE.md §7 테스트·확장성 |
  | 권한 변경 | `docs/guidelines/auth.md` |
  | 프론트엔드 패턴 변경 | `docs/guidelines/frontend.md` |
  | Excel Import/Export 변경 | `docs/guidelines/excel.md` |
  | startup/bootstrap/migration/배포 초기화 흐름 변경 | `docs/DECISIONS.md`, 필요 시 `README.md` 실행/초기 설정 |
  | 공개 엔드포인트/인증 흐름 변경 | `docs/guidelines/auth.md`, 필요 시 `README.md` |
  | 아키텍처 결정 | `docs/DECISIONS.md` (추가 전용) |
  | 임시 우회/제약 추가 | `docs/KNOWN_ISSUES.md` |
  | 임시 우회 해소 | `docs/KNOWN_ISSUES.md` (항목 삭제) |
  | 외부 사용자가 알아야 하는 실행/운영 방법 변경 | `README.md` |
  | 파일/디렉토리 추가·삭제 | `docs/PROJECT_STRUCTURE.md` |
  | 모델/API/파일 구조 세부 변경 | 문서 갱신 기본 불필요 (코드가 source of truth) |

---

## 3. 명명 / 인터페이스 규칙

- 백엔드 파일명, Python 명명, API 라우트, 도메인 용어 통일 규칙은 `docs/guidelines/backend.md`를 따른다.
- 프론트엔드(JS/HTML/CSS) 명명 및 스타일링 규칙은 `docs/guidelines/frontend.md`를 따른다.
- 상위 지침에는 “어떤 세부 규칙을 어디서 찾는지”만 남기고, 작업 중 반복 확인이 필요한 상세 naming inventory는 하위 guideline이 소유한다.

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
- 기본 회귀 테스트는 metrics/contract/importer/dashboard/receipt_match/report/auth/database/startup/transaction safety 범위를 포함한다. 세부 파일 목록은 `tests/`가 1차 기준이다.
- 완료된 귀속기간 보호, FIFO 배분 격리, ReceiptMatch 권한, 대시보드 집계(`is_planned`, `실주`, 목표 vs 실적, 월/분기/반기/연 재집계), 보고서/Excel Export의 미수금·합계 행 규칙은 위 테스트군으로 회귀를 보호한다.
- DB 스키마 변경은 Alembic(`alembic/versions/`)으로 관리한다.
  - 새 테이블/컬럼 추가 시: `alembic revision --autogenerate -m "설명"` → `upgrade()`에 `inspector` 존재 여부 체크 권장
  - startup 시 `app/startup/database_init.py`가 자동으로 `alembic upgrade head` 실행
  - 빈 DB도 `stamp`가 아니라 `upgrade` 대상으로 처리한다.
  - fresh production startup 경로는 회귀 테스트로 보호한다.
- 설정값(세율, 날짜 형식 등)은 코드가 아닌 설정 파일에서 관리.
- API는 `/api/v1/` 버전 prefix를 유지.

---

## 8. 완료 조건 (Definition of Done)

코드 변경이 "완료"되려면 다음을 모두 충족해야 한다:

1. 코드 변경 완료
2. 관련 테스트 통과 (새 기능은 테스트 추가)
3. 변경 유형을 식별하고 §2 매핑 표의 필수 문서를 갱신 완료
4. 해결된 KNOWN_ISSUES 항목이 있으면 삭제 완료
5. 문서에 적은 경로/엔드포인트/권한/초기화 절차가 코드와 일치함을 확인

### 문서 정합성 체크리스트

변경 커밋 전 아래를 확인한다:

- [ ] KNOWN_ISSUES.md에 이번 변경으로 해소된 항목이 있는가? → 삭제
- [ ] 비즈니스 규칙을 변경했는가? → CLAUDE.md §6 확인
- [ ] 권한 로직을 변경했는가? → `docs/guidelines/auth.md` 확인
- [ ] 공개 엔드포인트/로그인 흐름을 변경했는가? → `docs/guidelines/auth.md`, 필요 시 `README.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? → `docs/guidelines/frontend.md` 확인
- [ ] Excel Import/Export 계약을 변경했는가? → `docs/guidelines/excel.md` 확인
- [ ] startup/bootstrap/migration/초기 설정 흐름을 변경했는가? → `docs/DECISIONS.md`, 필요 시 `README.md` 확인
- [ ] 외부 사용자가 알아야 하는 실행/운영 방법을 바꿨는가? → `README.md` 확인
- [ ] 문서에 적은 경로/엔드포인트/권한명이 실제 코드와 일치하는가?
