# 영업부서 매입매출 관리 앱

영업부서의 사업(Contract)을 원장으로 관리하고, 사업별 매입/매출 내역을 월별로 입력·조회하며
필요한 형태의 Excel 파일로 Export하는 사내 전용 웹 애플리케이션.

> **현재 상태**: 파일럿 테스트 진행 (v0.3)
>
> **문서 안내** — 코딩 규칙은 `CLAUDE.md`, 작업 지침은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`,
> 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.
> 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델의 1차 기준은 소스 코드(`app/startup/`, `app/routers/`, `app/models/`)다.

---

## 핵심 흐름

```text
[앱에서 데이터 입력/관리]
       ↓
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

---

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 백엔드 | Python 3.11+, FastAPI |
| ORM | SQLAlchemy 2.0 (Mapped 방식) |
| DB | SQLite (향후 PostgreSQL 마이그레이션 예정) |
| 프론트엔드 | Jinja2 + HTMX + AG Grid Community |
| Excel 처리 | openpyxl, pandas |
| 인증 | 세션 기반 (쿠키) |
| 포매터/린터 | black, ruff |
| 테스트 | pytest |

---

## 실행 방법

### 사전 요구사항

- Python 3.11 이상
- pip

### 설치 및 실행

```bash
# 1. 의존성 설치
python -m pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일 생성)
# SESSION_SECRET_KEY=<운영 환경 필수, 충분히 긴 랜덤 세션 비밀키>
# DATABASE_URL=sqlite:///./sales.db  (기본값, 환경별 DB 교체 가능)
# BOOTSTRAP_ADMIN_LOGIN_ID=admin
# BOOTSTRAP_ADMIN_PASSWORD=<초기 관리자 비밀번호>
# BOOTSTRAP_ADMIN_NAME=관리자

# 3. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 브라우저 접속
# http://localhost:8000
```

- 비개발 환경에서는 `SESSION_SECRET_KEY`가 없으면 앱이 시작되지 않는다.
- `DATABASE_URL`을 PostgreSQL 등으로 변경할 경우 해당 드라이버 설치와 backend별 연결 설정이 추가로 필요하다.

### Docker 배포

```bash
# 1. .env 파일 작성 (.env.example 참고)
cp .env.example .env
# SESSION_SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD 등 필수값 설정

# 2. 빌드 및 실행
docker compose up -d

# 3. 상태 확인
curl http://localhost:8000/api/v1/health
```

- `docker-compose.yml`이 persistent volume(`app-data`)을 설정하므로 컨테이너 재시작 시 DB 유지
- Gunicorn + UvicornWorker 구성으로 워커 크래시 시 자동 재생성
- `/api/v1/health`는 공개 헬스체크용 엔드포인트이며, 외부에는 단순 상태만 반환
- 환경변수 상세는 `.env.example` 참조

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
  ├─ API 라우터 (/api/v1/...)
  ├─ 템플릿 렌더러
  ├─ 서비스 레이어 (비즈니스 로직)
  └─ DB 레이어 (ORM)
       │
    [SQLite / PostgreSQL]
```

- API와 템플릿 렌더링을 같은 FastAPI 인스턴스에서 처리
- LLM은 개발(코드 생성) 단계에서만 사용, 런타임에는 포함하지 않음

---

## 프로젝트 구조

```text
sales/
├── app/
│   ├── auth/           # 인증·인가 (세션, 권한 체크, 비밀번호)
│   ├── models/         # SQLAlchemy ORM 모델
│   ├── schemas/        # Pydantic 입출력 스키마
│   ├── routers/        # FastAPI 라우터 (API 엔드포인트)
│   ├── services/       # 비즈니스 로직 (도메인별 분리, _ 접두사 헬퍼)
│   ├── startup/        # 앱 초기화 (DB, bootstrap, lifespan)
│   ├── static/         # JS, CSS, 이미지
│   └── templates/      # Jinja2 HTML 템플릿
├── tests/              # pytest 테스트
├── alembic/            # DB 마이그레이션
└── docs/               # 지침, 결정 기록, 이슈
```

> 파일 단위 상세 구조와 모듈별 역할은 [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) 참조.

## 문서 구조

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태
- `CLAUDE.md`: 상위 개발 지침, 문서 갱신 규칙, 완료 조건
- `docs/guidelines/`: 백엔드, 인증/권한, 프론트엔드, Excel 작업별 상세 규칙
- `docs/DECISIONS.md`: 구조/정책 결정 기록
- `docs/KNOWN_ISSUES.md`: 아직 해소되지 않은 제약과 우회
- `docs/PROJECT_CONTEXT.md`: 프로젝트 배경, 사용자, 문제 정의
- `docs/PROJECT_STRUCTURE.md`: 파일 단위 프로젝트 구조와 모듈별 역할
- `app/startup/`: startup/bootstrap/migration 초기화 흐름
- `app/routers/`: API 엔드포인트의 1차 기준
- `app/models/`: 데이터 모델의 1차 기준
- `tests/`: 회귀 범위와 검증 기준의 1차 기준

---

## 핵심 데이터 개요

- `Contract`: 사업 원장 단위
- `ContractPeriod`: 사업의 연도별 기간 버전
- `MonthlyForecast`: 기간별 월 예상 매출/GP
- `TransactionLine`: 월별 매출/매입 실적
- `Receipt`: 입금 내역
- `ReceiptMatch`: 입금과 매출 실적의 배분 관계
- `Customer`, `CustomerContact`, `ContractContact`: 거래처와 담당자 구조
- 상세 필드와 관계의 1차 기준은 `app/models/` 소스 코드다.

---

## 구현 완료 기능

| 영역 | 주요 기능 |
| ---- | -------- |
| **사업 관리** | 사업/기간 CRUD, 담당자 매핑, 검수일/발행일 규칙 |
| **Forecast / 실적 / 입금** | 월별 Forecast, 실적 원장, 입금과 배분, 미수금/선수금 계산 |
| **거래처 / 사용자** | 거래처와 담당자 관리, 사용자 관리, 권한 범위, CSV 일괄 등록 |
| **Excel / 보고** | 3단계 Import, 대시보드/보고서 조회, Excel Export |
| **시스템** | 전역 예외 처리, 설정 관리, 감사 로그 인프라 |

---

## 현재 제한사항 / 알려진 이슈

> 상세 내용은 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) 참조.

- 감사 로그 서비스 연동 미완료, 조회 UI placeholder
- admin/user 2단계 권한만 구현 (manager/viewer 미구현)
- 동시 편집 충돌 방지(낙관적 잠금) 미구현
- 발행일 휴일 조정 미적용
- 대량 데이터(1000행 이상) Excel Import 성능 미검증
- SQLite 단일 파일 — WAL 모드 적용, 동시 쓰기는 단일 워커로 제한

---

## 인터페이스 개요

- 인증: 로그인, 로그아웃, 현재 사용자, 비밀번호 변경
- 사업 관리: 사업/기간 CRUD, 원장 조회, 내 사업 요약
- 거래처 관리: 거래처/담당자 CRUD 및 관련 조회
- Forecast/실적/입금/배분: 월별 입력과 집계
- 대시보드/보고서: KPI, 목표 대비 실적, 미수 현황, Excel Export
- 시스템 관리: 사용자, 설정, 사업유형, 용어 설정
- 세부 엔드포인트와 권한의 1차 기준은 `app/routers/`와 `docs/guidelines/auth.md`다.
