# 사업 관리 통합 플랫폼

영업부서의 매입매출 관리(회계모듈)와 SI 프로젝트 기술 인벤토리 관리(인프라모듈)를
하나의 웹 애플리케이션에서 통합 운영하는 사내 전용 플랫폼.

> **현재 상태**: 모듈화 마이그레이션 진행 중 (v0.4)
>
> **문서 안내** — 코딩 규칙은 `CLAUDE.md`, 작업 지침은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`,
> 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.
> 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델의 1차 기준은 소스 코드(`app/core/startup/`, `app/modules/*/routers/`, `app/modules/*/models/`)다.

---

## 모듈 구성

| 모듈 | 설명 | 상태 |
| ---- | ---- | ---- |
| **공통 (common)** | 사용자, 거래처, 인증, 시스템 설정 | 구현 완료 |
| **회계 (accounting)** | 사업 원장, 매입매출 실적, 입금/배분, 대시보드, 보고서, Excel | 구현 완료 |
| **인프라 (infra)** | 프로젝트, 자산, IP 인벤토리, 포트맵, 정책, 현황판, Excel Import/Export | 구현 완료 |

---

## 핵심 흐름

### 회계모듈

```text
사업 원장 (마스터)
├── 사업 기본정보 (사업유형, 담당, 거래처, 진행단계 등)
├── 사업기간 (ContractPeriod: Y25, Y26 등 연도 단위)
├── Forecast (ContractPeriod별 월별 예상 매출/GP)
├── TransactionLine (매출/매입 실적 라인)
└── Receipt (입금 내역)
     ↓
[Export]
├── [매입매출관리] Excel - 사업 단위
└── [영업관리] Excel - 전체 원장 (월별 집계)
```

### 인프라모듈

```text
프로젝트 생성 / Pin 프로젝트 (사용자별 고정)
├── 프로젝트 기본정보 / 단계 / 산출물
├── 프로젝트-업체 연결 (고객사/수행사/유지보수사/통신사/벤더)
│   └── 프로젝트-담당자 역할 매핑
├── Asset 등록 (N:M 프로젝트 연결, 자산 간 관계)
│   ├── IP 인벤토리 연결
│   ├── PortMap 연결
│   ├── 정책 적용 상태 연결
│   └── 담당자 연결
├── 프로젝트 단위 Excel Export (자산/IP/포트맵 3시트)
├── 감사 로그 (CRUD 변경이력 기록 + 변경이력 탭)
└── 현황판 (프로젝트별 자산/IP/정책/산출물 요약)
```

---

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 백엔드 | Python 3.11+, FastAPI |
| ORM | SQLAlchemy 2.0 (Mapped 방식) |
| DB | PostgreSQL 16 |
| 프론트엔드 | Jinja2 + HTMX + AG Grid Community |
| Excel 처리 | openpyxl, pandas |
| 인증 | 세션 기반 (쿠키), bcrypt 해싱 |
| RBAC | 역할 기반 모듈 접근 제어 (Role.permissions JSON) |
| 포매터/린터 | black, ruff |
| 테스트 | pytest |

---

## 실행 방법

### 사전 요구사항

- Docker Desktop (WSL2 backend)
- Docker Compose

또는

- Python 3.11 이상
- PostgreSQL 16
- pip

### Docker Compose 실행 (권장)

```bash
# 1. 환경변수 파일 생성
cp .env.example .env
# SESSION_SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD 등 필수값 설정

# 2. 컨테이너 빌드 및 기동
docker compose up --build

# 3. 앱 접속
# http://localhost:9000
```

- `app` 컨테이너는 PostgreSQL 준비 상태를 기다린 뒤 `alembic upgrade head`를 실행하고 서버를 시작한다.
- 기본 compose 구성은 PostgreSQL 서비스와 FastAPI 앱 서비스로 동작한다.
- `app`, `db` 서비스 모두 `restart: unless-stopped`로 설정되어 자동 재기동된다.
- 운영형 값은 `docker-compose.yml`에 하드코딩하지 않고 루트 `.env`에서 주입한다.
- 운영 환경에서는 `APP_ENV`, `SESSION_SECRET_KEY`, DB 계정, bootstrap 관리자 비밀번호를 안전한 값으로 변경해야 한다.
- 호스트 공개 포트는 앱 `9000`, DB `5432` 기준이다.

### 로컬 Python 실행

```bash
# 1. 의존성 설치
python -m pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일 생성)
# DATABASE_URL=postgresql://projmgr:projmgr@localhost:5432/projmgr
# SESSION_SECRET_KEY=<운영 환경 필수, 충분히 긴 랜덤 세션 비밀키>
# BOOTSTRAP_ADMIN_LOGIN_ID=admin
# BOOTSTRAP_ADMIN_PASSWORD=<초기 관리자 비밀번호>
# BOOTSTRAP_ADMIN_NAME=관리자
# ENABLED_MODULES=common,accounting,infra

# 3. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# 4. 브라우저 접속
# http://localhost:9000
```

- 비개발 환경에서는 `SESSION_SECRET_KEY`가 없으면 앱이 시작되지 않는다.
- 로컬 실행 시 PostgreSQL이 미리 기동되어 있어야 한다.

### 모듈 활성화

`ENABLED_MODULES` 환경변수로 활성 모듈을 제어한다:

```bash
ENABLED_MODULES=common,accounting,infra   # 본사 전체 (기본값)
ENABLED_MODULES=common,infra              # 현장 standalone (인프라만)
ENABLED_MODULES=common,accounting         # 영업 전용
```

- `common` 모듈은 항상 활성 (사용자, 거래처, 인증 등 기반 기능)
- 비활성 모듈의 테이블은 DB에 존재하되 라우터가 등록되지 않아 접근 불가

### 초기 설정

- startup 시 Alembic migration이 자동 적용되어 신규 DB도 스키마가 준비됨
- 활성 관리자 계정이 없으면 bootstrap 환경변수(`BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME`)로 첫 관리자 계정을 생성
- Excel Import를 통해 기존 데이터 일괄 등록 가능 (관리자 전용)

---

## 아키텍처

```text
[브라우저]
  └─ HTML (Jinja2) + HTMX + AG Grid
       │  HTTP / JSON
[FastAPI 서버] ── [사내 네트워크 전용, 외부 차단]
  ├─ app/core/           # 앱 팩토리, 설정, DB, 예외, 인증, startup
  ├─ app/modules/
  │   ├─ common/         # 사용자, 거래처, 설정, 감사로그
  │   ├─ accounting/     # 사업, 매출/매입, 입금, 대시보드, 보고서
  │   └─ infra/          # 프로젝트, 자산, IP, 포트맵, 정책, Excel, 현황판
  └─ Alembic (단일 migration 체인)
       │
   [PostgreSQL 16]
```

- API와 템플릿 렌더링을 같은 FastAPI 인스턴스에서 처리
- 모듈 간 의존성: `core <- common <- {accounting, infra}` 단방향만 허용
- `accounting <-> infra` 직접 참조 금지
- LLM은 개발(코드 생성) 단계에서만 사용, 런타임에는 포함하지 않음

---

## 문서 구조

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태
- `CLAUDE.md`: 상위 개발 지침, 문서 갱신 규칙, 완료 조건
- `docs/guidelines/`: 백엔드, 인증/권한, 프론트엔드, Excel 작업별 상세 규칙
- `docs/DECISIONS.md`: 구조/정책 결정 기록
- `docs/KNOWN_ISSUES.md`: 아직 해소되지 않은 제약과 우회
- `docs/PROJECT_CONTEXT.md`: 프로젝트 배경, 사용자, 문제 정의
- `docs/PROJECT_STRUCTURE.md`: 파일 단위 프로젝트 구조와 모듈별 역할
- 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델, 테스트 범위의 1차 기준은 소스 코드다
- 파일 단위 상세 구조와 모듈별 역할은 [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) 참조

---

## 구현 완료 기능

| 영역 | 주요 기능 | 모듈 |
| ---- | -------- | ---- |
| **사업 관리** | 사업/기간 CRUD, 담당자 매핑, 검수일/발행일 규칙 | accounting |
| **Forecast / 실적 / 입금** | 월별 Forecast, 실적 원장, 입금과 배분, 미수금/선수금 계산 | accounting |
| **거래처 / 사용자** | 거래처와 담당자 관리, 사용자 관리, 권한 범위, CSV 일괄 등록 | common |
| **Excel / 보고** | 3단계 Import, 대시보드/보고서 조회, Excel Export | accounting |
| **시스템** | 전역 예외 처리, 설정 관리, 감사 로그 인프라 | common |
| **프로젝트 관리** | 프로젝트 CRUD, 단계, 산출물, Pin 프로젝트, 업체/담당자 연결 | infra |
| **기술 자산** | Asset CRUD, N:M 프로젝트 연결, 자산 간 관계, 횡단 검색 | infra |
| **네트워크** | IP 인벤토리, 포트맵 CRUD, Excel Import | infra |
| **정책** | 정책 정의, 프로젝트/자산별 적용 상태 | infra |
| **인프라 공통** | Excel Export, 현황판, 감사 로그 연동, 변경이력 탭 | infra |

---

## 현재 제한사항 / 알려진 이슈

> 상세 내용은 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) 참조.

- 회계모듈 감사 로그 서비스 연동 미완료 (인프라모듈은 연동 완료)
- 동시 편집 충돌 방지(낙관적 잠금) 미구현
- 발행일 휴일 조정 미적용
- 대량 데이터(1000행 이상) Excel Import 성능 미검증
