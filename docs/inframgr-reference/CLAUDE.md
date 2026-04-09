# 프로젝트 개발 지침

> 항상 읽는 상위 지침. 실행 방법/프로젝트 개요는 `README.md`, 작업별 세부 규칙은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md`, 구조 설계는 `docs/ARCHITECTURE.md` 참조.

---

## 작업별 상세 지침

- 백엔드(Python/FastAPI/SQLAlchemy) 작업 → `docs/guidelines/backend.md`
- 프론트엔드(JS/CSS/HTML) 작업 → `docs/guidelines/frontend.md`
- 인증/권한/보안 작업 → `docs/guidelines/auth.md`
- Excel Import/Export 작업 → `docs/guidelines/excel.md`

---

## 문서 계층 / Source of Truth

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태, 문서 안내
- `CLAUDE.md`: 항상 유지해야 하는 핵심 규칙, 문서 갱신 매핑, 완료 조건
- `docs/ARCHITECTURE.md`: 전체 시스템 구조, 핵심 엔티티 관계, API/화면 설계
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
| 프로젝트 (Project) | 기술 인벤토리를 관리하는 최상위 단위 |
| 프로젝트 단계 (ProjectPhase) | 분석, 설계, 구축, 시험, 안정화 등 진행 단계 |
| 산출물 (Deliverable) | 프로젝트 단계별 제출 대상 문서/결과물 |
| 자산 (Asset) | 서버, 네트워크 장비, 보안 장비 등 기술 자산 |
| IP 대역 (IpSubnet) | 프로젝트 범위의 IP 대역, 역할·지역·상대국 등 메타데이터 포함 |
| IP 인벤토리 (AssetIP) | Asset에 연결된 IP 정보, IpSubnet 참조 가능 |
| 포트맵 (PortMap) | 자산 간 통신 관계 |
| 정책 정의 (PolicyDefinition) | 적용 기준이 되는 정책 원본 |
| 정책 적용 상태 (PolicyAssignment) | 프로젝트/자산 단위 정책 준수 현황 |
| 업체 (Partner) | 고객사, 공급사, 유지보수사, 통신사 등 프로젝트 관련 업체 |
| 담당자 (Contact) | 업체 소속 담당자 |
| 자산 담당자 매핑 (AssetContact) | 특정 자산과 담당자의 역할 연결 |

### 범위 정의

- 본 시스템은 **프로젝트 기술 인벤토리 시스템**이다.
- 태스크 관리, 간트 차트, 메시징, 알림, 일정 관리는 구현 범위에서 제외한다.
- 프로젝트 수행에 필요한 기술 자산, 네트워크 정보, 정책 현황, 연락망의 단일 원장을 제공하는 것이 목표다.

---

## 2. 코드 규칙

- **코드 일관성을 기능 추가 속도보다 우선한다.** 동일 문제 해결 시 기존 패턴을 우선 사용하고, 새로운 구조 도입은 최소화한다.
- Python 버전: 3.11 이상
- 포매터: `black`, 린터: `ruff`
- 타입 힌트를 모든 함수에 명시한다.
- Pydantic 스키마는 `app/schemas/` 디렉토리에 정의한다. 라우터 파일에 스키마 클래스를 직접 정의하지 않는다.
- enum 성격의 필드는 Python `Enum` 또는 `Literal`로 선언한다.
- 라우터는 기능 단위로 분리한다 (예: `routers/projects.py`, `routers/assets.py`).
- 서비스도 도메인 단위로 분리한다. 하나의 서비스 파일이 비대해지면(~500줄 이상) 엔티티별로 분리하고, 교차 도메인 공유 함수는 `_` 접두사 헬퍼 모듈에 둔다.
- 서비스 레이어에 비즈니스 로직을 집중시키고, 라우터는 얇게 유지한다.
  - 라우터는 요청 파라미터 전달과 응답 선언에 집중하고, 조회·권한·유효성 검증·ORM→Schema 변환은 서비스에 위임한다.
  - 라우터에서 `if not obj: raise HTTPException(...)`, `db.get()`, `db.query()` 같은 패턴을 직접 두지 않는다.
  - 서비스에서 커스텀 예외를 발생시키고, 전역 핸들러(`app/app_factory.py`)가 HTTP 응답으로 자동 변환한다.
- SQL 작성 시 f-string으로 테이블명/컬럼명을 삽입하지 않는다. SQLAlchemy ORM 또는 Core 표현식만 사용한다.
- 환경변수는 `.env` 파일로 관리하고, 코드에 하드코딩하지 않는다.
- `DATABASE_URL` 기반 설정은 특정 DB 전용 `connect_args`를 전역 고정하지 말고 backend별로 분기한다.
- 보안 관련 환경변수는 insecure fallback을 두지 않는다.
- 모듈 간 순환 import는 허용하지 않는다. 공통 모듈 추출 또는 `TYPE_CHECKING` 분기로 해결한다.
- **코드 변경 시 문서 갱신 규칙**: 아래 매핑 표에 따라 변경 의미에 맞는 문서만 갱신한다.

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
  | 핵심 데이터 흐름/API/화면 구조 변경 | `docs/ARCHITECTURE.md` |
  | 모델/API/파일 구조 세부 변경 | 문서 갱신 기본 불필요 (코드가 source of truth) |

---

## 3. 명명 / 인터페이스 규칙

- 백엔드 파일명, Python 명명, API 라우트, 도메인 용어 통일 규칙은 `docs/guidelines/backend.md`를 따른다.
- 프론트엔드(JS/HTML/CSS) 명명 및 스타일링 규칙은 `docs/guidelines/frontend.md`를 따른다.
- 상위 지침에는 “어떤 세부 규칙을 어디서 찾는지”만 남기고, 작업 중 반복 확인이 필요한 상세 naming inventory는 하위 guideline이 소유한다.

---

## 4. 예외 처리

- 커스텀 예외: `app/exceptions.py`
  - `UnauthorizedError` → 401
  - `NotFoundError` → 404
  - `BusinessRuleError` → 403
  - `DuplicateError` → 409
  - `PermissionDeniedError` → 403
  - `ValidationError` → 422
- 서비스 함수는 `None`/`False` 반환 대신 예외를 발생시킨다.
- 서비스 함수는 `ValueError` 등 표준 예외 대신 커스텀 예외를 사용한다.
- 라우터는 예외를 직접 처리하지 않고 전역 핸들러에 위임한다.

---

## 5. 감사 로그

- MVP에서는 감사 로그를 필수 범위로 두지 않는다.
- 다만 변경 이력 확장을 위해 모든 주요 테이블에 `created_at`, `updated_at`를 둔다.
- 감사 로그를 추가할 경우 모델/서비스를 별도 모듈로 분리하고 호출자 트랜잭션에 종속되도록 설계한다.

---

## 6. 데이터 원칙

- `Project`는 상위 컨텍스트이고, 기술 인벤토리의 탐색 중심은 `Asset`이다.
- `Asset`을 중심으로 `AssetIP`, `PortMap`, `AssetContact`가 연결된다.
- 정책은 반드시 `PolicyDefinition`과 `PolicyAssignment`로 분리한다.
- IP 중복 검증은 최소한 프로젝트 범위 내에서 수행한다.
- 자산명은 프로젝트 내 unique를 기본 원칙으로 한다.
- 상태값은 문자열 하드코딩 대신 enum으로 통일한다.
- 포트맵은 자산 간 연결뿐 아니라 외부 구간 표현을 위해 `src_asset_id`, `dst_asset_id`를 nullable로 둘 수 있다.
- 정책 적용 상태는 `not_checked`, `compliant`, `non_compliant`, `exception`, `not_applicable` 범위를 기본값으로 사용한다.
- 연락처는 업체에 소속되고, 자산에는 매핑으로 연결한다.

---

## 7. 테스트·확장성

- 프레임워크: `pytest`
- MVP 필수 테스트 범위:
  - 프로젝트 CRUD
  - 단계/산출물 CRUD
  - 자산 CRUD
  - 프로젝트 내 IP 중복 검증
  - 포트맵 연결 검증
  - 정책 정의/적용 상태 CRUD
  - 권한 및 세션 인증
- DB 스키마 변경은 Alembic(`alembic/versions/`)으로 관리한다.
- 설정값과 enum 후보군 중 운영상 바뀔 수 있는 항목은 코드 하드코딩보다 설정/참조 테이블 확장을 우선 검토한다.
- API는 `/api/v1/` 버전 prefix를 유지한다.
- 미래 기능은 미리 구현하지 않되, 다음 확장이 막히지 않도록 스키마를 설계한다.
  - Excel Import/Export
  - 감사 로그
  - 정책 점검 리포트
  - 역할 세분화
  - 외부 시스템 연동

---

## 8. 완료 조건 (Definition of Done)

코드 변경이 "완료"되려면 다음을 모두 충족해야 한다:

1. 코드 변경 완료
2. 관련 테스트 통과 (새 기능은 테스트 추가)
3. 변경 유형을 식별하고 §2 매핑 표의 필수 문서를 갱신 완료
4. 해결된 KNOWN_ISSUES 항목이 있으면 삭제 완료
5. 문서에 적은 경로/엔드포인트/권한/초기화 절차가 코드와 일치함을 확인

### 문서 정합성 체크리스트

- [ ] KNOWN_ISSUES.md에 이번 변경으로 해소된 항목이 있는가? → 삭제
- [ ] 비즈니스 규칙을 변경했는가? → CLAUDE.md §6 확인
- [ ] 권한 로직을 변경했는가? → `docs/guidelines/auth.md` 확인
- [ ] 공개 엔드포인트/로그인 흐름을 변경했는가? → `docs/guidelines/auth.md`, 필요 시 `README.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? → `docs/guidelines/frontend.md` 확인
- [ ] Excel Import/Export 계약을 변경했는가? → `docs/guidelines/excel.md` 확인
- [ ] startup/bootstrap/migration/초기 설정 흐름을 변경했는가? → `docs/DECISIONS.md`, 필요 시 `README.md` 확인
- [ ] 외부 사용자가 알아야 하는 실행/운영 방법을 바꿨는가? → `README.md` 확인
- [ ] 핵심 데이터 흐름/API/화면 구조를 바꿨는가? → `docs/ARCHITECTURE.md` 확인
- [ ] 문서에 적은 경로/엔드포인트/권한명이 실제 코드와 일치하는가?
