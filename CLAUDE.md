# 프로젝트 개발 지침

> 항상 읽는 상위 지침. 사업 관리 통합 플랫폼 (공통 + 회계 + 인프라 모듈).
> 실행 방법/프로젝트 개요는 `README.md`, 작업별 세부 규칙은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`, 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.

---

## 작업별 상세 지침 (필요 시 참조)

- 백엔드(Python/FastAPI/SQLAlchemy) 작업 → `docs/guidelines/backend.md`
- 프론트엔드(JS/CSS/HTML) 작업 → `docs/guidelines/frontend.md`
- 인증/권한/보안 작업 → `docs/guidelines/auth.md`
- Excel Import/Export 작업 → `docs/guidelines/excel.md`
- 회계모듈 작업 → `docs/guidelines/accounting.md`
- 인프라모듈 작업 → `docs/guidelines/infra.md`

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

---

## 1. 공통 도메인 용어

| 용어 | 설명 |
| --- | --- |
| 거래처 (Customer) | 고객사, 공급사, 유지보수사, 통신사 등. 회계/인프라 모듈이 공유 |
| 거래처 담당자 (CustomerContact) | 거래처 소속 담당자 |
| 역할 (Role) | RBAC 역할. permissions JSON으로 모듈별 접근 수준 관리 |

> 모듈별 용어는 `docs/guidelines/accounting.md`, `docs/guidelines/infra.md` 참조.

---

## 2. 핵심 코드 규칙

- **코드 일관성을 기능 추가 속도보다 우선한다.** 동일 문제 해결 시 기존 패턴을 우선 사용한다.
- Python 3.11+, PostgreSQL 16, 포매터 `black`, 린터 `ruff`
- 타입 힌트를 모든 함수에 명시한다.
- 서비스 레이어에 비즈니스 로직을 집중시키고, 라우터는 얇게 유지한다.
- 생성일시/수정일시는 `TimestampMixin`으로 공통 적용.
- `created_by`는 라우터에서 `get_current_user`를 통해 서비스로 전달.
- 설정값(세율, 날짜 형식 등)은 코드가 아닌 설정 파일에서 관리.
- API는 `/api/v1/` 버전 prefix를 유지.

> 레이어 분리, 예외 처리, 감사 로그, 명명 규칙, 환경변수/보안 상세는 `docs/guidelines/backend.md` 참조.

### 모듈 구조

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

**모듈 간 import 규칙:** `core ← common ← {accounting, infra}`. **accounting ↔ infra 절대 금지.**

### 모듈 활성화

`ENABLED_MODULES` 환경변수로 활성 모듈을 제어한다.

- 모든 모델은 항상 import (Alembic 정합성). 라우터는 활성 모듈만 등록. 템플릿 로더에 활성 모듈 경로만 추가.

### 코드 변경 시 문서 갱신 규칙

| 변경 유형 | 갱신 대상 |
| --------- | --------- |
| 회계 비즈니스 규칙 변경 | `docs/guidelines/accounting.md` |
| 인프라 비즈니스 규칙 변경 | `docs/guidelines/infra.md` |
| 코딩 패턴/규칙 변경 | `docs/guidelines/backend.md` |
| 테스트 전략/회귀 범위 변경 | CLAUDE.md SS3 테스트/확장성 |
| 권한 변경 | `docs/guidelines/auth.md` |
| 프론트엔드 패턴 변경 | `docs/guidelines/frontend.md` |
| Excel Import/Export 변경 | `docs/guidelines/excel.md` |
| startup/bootstrap/migration 변경 | `docs/DECISIONS.md`, 필요 시 `README.md` |
| 공개 엔드포인트/인증 흐름 변경 | `docs/guidelines/auth.md`, 필요 시 `README.md` |
| 아키텍처 결정 | `docs/DECISIONS.md` (추가 전용) |
| 임시 우회/제약 추가 | `docs/KNOWN_ISSUES.md` |
| 임시 우회 해소 | `docs/KNOWN_ISSUES.md` (항목 삭제) |
| 외부 사용자가 알아야 하는 실행/운영 변경 | `README.md` |
| 파일/디렉토리 추가/삭제 | `docs/PROJECT_STRUCTURE.md` |
| 모델/API/파일 구조 세부 변경 | 문서 갱신 기본 불필요 (코드가 source of truth) |

---

## 3. 테스트/확장성

- GP/GP%/미수금 계산, CRUD 플로우, Excel Import: 단위/통합 테스트 필수. 프레임워크: `pytest`.
- DB fixture: PostgreSQL 테스트 컨테이너 (`testcontainers-python` 또는 테스트용 별도 DB).
- 테스트 디렉토리는 모듈별로 구성한다 (`tests/{common,accounting,infra}/`).
- 기본 회귀 범위: metrics, contract, importer, dashboard, receipt_match, report, auth, database, startup, transaction safety, 모듈 격리, 모듈 등록, RBAC. 세부 파일 목록은 `tests/`가 1차 기준.
- CRUD/설정 변경 회귀에는 삭제 경로, 다중 필드 업데이트, 원자성 시나리오를 포함한다.
- 권한 회귀 테스트는 router 응답뿐 아니라 service 직접 호출 경로의 action 권한과 scope 차단도 포함한다.
- DB 스키마 변경은 Alembic(`alembic/versions/`)으로 관리한다. startup 시 자동 `alembic upgrade head` 실행. 단일 migration 체인 유지.

---

## 4. 완료 조건 (Definition of Done)

코드 변경이 "완료"되려면 다음을 모두 충족해야 한다:

1. 코드 변경 완료
2. 관련 테스트 통과 (새 기능은 테스트 추가)
   - 테스트가 로컬 환경 의존성 부족이나 실행 정책 때문에 막히면, 누락 의존성/차단 원인/미실행 범위를 작업 결과에 명시한다.
3. 변경 유형을 식별하고 SS2 매핑 표의 필수 문서를 갱신 완료
4. 해결된 KNOWN_ISSUES 항목이 있으면 삭제 완료
5. 문서에 적은 경로/엔드포인트/권한/초기화 절차가 코드와 일치함을 확인

### 문서 정합성 체크리스트

변경 커밋 전 아래를 확인한다:

- [ ] KNOWN_ISSUES.md에 이번 변경으로 해소된 항목이 있는가? → 삭제
- [ ] 비즈니스 규칙을 변경했는가? → 해당 모듈 guideline 확인
- [ ] 권한 로직을 변경했는가? → `docs/guidelines/auth.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? → `docs/guidelines/frontend.md` 확인
- [ ] Excel Import/Export를 변경했는가? → `docs/guidelines/excel.md` 확인
- [ ] startup/bootstrap/migration을 변경했는가? → `docs/DECISIONS.md`, 필요 시 `README.md` 확인
- [ ] 문서에 적은 경로/엔드포인트/권한명이 실제 코드와 일치하는가?

### 세션 컨텍스트 관리

장시간 작업 시 대화 컨텍스트가 커져 API 과부하(529 에러)나 성능 저하가 발생할 수 있다. 다음 규칙을 적용한다:

- **API 529 에러가 2회 연속 발생하면** 즉시 작업을 중단하고 세션 전환을 제안한다.
- **에이전트는 항상 1개씩 순차 파견**한다. 병렬 파견은 API 부하를 가중시킨다.
- **단순 HTML/JS/CSS 수정은 에이전트 파견 대신 직접 처리**한다.
- **대규모 Task 3개 이상 완료 후** 에이전트 파견 전에 컨텍스트 크기를 고려하고, 필요 시 세션 전환을 제안한다.
- 세션 전환 시: memory에 진행 상태(`project_active_plan.md`)를 저장하고, 사용자에게 새 세션 시작을 안내한다. 새 세션에서는 plan 파일과 memory를 읽어 이어서 진행한다.

### 마이그레이션 기간 예외 (런타임 E2E 검증 완료 후 삭제)

코드 구조 마이그레이션은 완료되었다 (common/accounting/infra 모듈 분리, 인프라모듈 전체 구현 완료). 런타임 E2E 통합 테스트(실제 서버 기동, 브라우저 검증)가 미수행이므로 이 예외 섹션을 유지한다.

- 코드-문서 경로 불일치가 있더라도, 마이그레이션 계획에 따른 의도적 불일치이면 문서를 되돌리지 않는다.
- 미구현/부분구현 코드를 근거로 지침을 수정하지 않는다. 단, 지침 간 상호 모순 또는 지침이 구현을 차단하는 경우에 한해 충돌을 보고하고 사용자 확인을 요청할 수 있다.
- 런타임 E2E 검증 완료 후 이 섹션을 삭제한다.
