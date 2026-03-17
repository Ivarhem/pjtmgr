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

### 초기 설정

- 최초 실행 시 DB 테이블이 자동 생성됨
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

## 문서 구조

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태
- `CLAUDE.md`: 상위 개발 지침, 문서 갱신 규칙, 완료 조건
- `docs/guidelines/`: 인증/권한, 프론트엔드, Excel 작업별 상세 규칙
- `docs/DECISIONS.md`: 구조/정책 결정 기록
- `docs/KNOWN_ISSUES.md`: 아직 해소되지 않은 제약과 우회
- `docs/PROJECT_CONTEXT.md`: 프로젝트 배경, 사용자, 문제 정의
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
| **사업 관리** | CRUD (소프트 삭제·복구), 내 사업 필터 + 요약 바, Period 관리 (계획/수시·실주), 담당자 매핑, 검수일/발행일 규칙 |
| **Forecast** | 월별 예상 매출/GP, Forecast→실적 동기화 (발행일·매출처 자동 계산) |
| **매출/매입 원장** | 실적 CRUD, 반복행·행복제, 일괄 삭제·확정, Ledger 뷰, 완료 기간 읽기전용 보호, 입금 배분 매출 삭제 방지 |
| **입금** | 입금 CRUD, 미수 매출 기반 기본값 자동설정 |
| **입금 배분** | FIFO 자동 배분 (귀속기간 격리), 수동 배분, 자동 재배분, 미수금/선수금 계산 |
| **거래처** | CRUD, 담당자 N명 (다역할), 탭 대시보드 (사업현황/담당자/매출·매입/입금), 담당자 피벗 뷰 |
| **인증/사용자** | 세션 기반 인증, admin/user 권한, 데이터 가시 범위, bootstrap 관리자, 로그인 잠금, CSV 일괄 등록 |
| **Excel** | 3단계 Import (검증→사업→Forecast→실적), 값 정규화, 4종 보고서 Excel Export |
| **대시보드** | KPI 요약, 사업유형별 매출, 추이 차트 (막대/선형/영역), 목표 vs 실적, 집계 단위 전환 |
| **보고서** | 요약 현황, Forecast vs Actual, 미수 현황, 매입매출관리 + Excel Export |
| **시스템** | 전역 예외 핸들러, 감사 로그 인프라, 컬럼/필터 상태 localStorage 저장, 사업유형·용어 설정 관리 |

---

## 현재 제한사항 / 알려진 이슈

> 상세 내용은 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) 참조.

- 감사 로그 서비스 연동 미완료, 조회 UI placeholder
- admin/user 2단계 권한만 구현 (manager/viewer 미구현)
- 동시 편집 충돌 방지(낙관적 잠금) 미구현
- 발행일 휴일 조정 미적용

---

## 인터페이스 개요

- 인증: 로그인, 로그아웃, 현재 사용자, 비밀번호 변경
- 사업 관리: 사업/기간 CRUD, 원장 조회, 내 사업 요약
- 거래처 관리: 거래처/담당자 CRUD 및 관련 조회
- Forecast/실적/입금/배분: 월별 입력과 집계
- 대시보드/보고서: KPI, 목표 대비 실적, 미수 현황, Excel Export
- 시스템 관리: 사용자, 설정, 사업유형, 용어 설정
- 세부 엔드포인트와 권한의 1차 기준은 `app/routers/`와 `docs/guidelines/auth.md`다.

## 화면 구조

### 네비게이션

내 사업 / 사업 관리 / 거래처 관리 / 대시보드 / 보고서 / 로그(준비 중) / 설정

### 사업 상세 화면

```text
사업 기본정보 (수정 가능)
├── 검수일/발행일 규칙 설정
└── Period 탭 버튼 [ Y25 ] [ Y26 ] [ Y27 ]
    ├── Forecast 그리드 (월별 예상 매출/GP)
    ├── 매출/매입 원장 그리드 (TransactionLine, 필터, 행추가/삭제/복제/확정/저장)
    ├── 입금 내역 그리드 (Receipt, 행추가/삭제/저장)
    ├── 배분 현황 그리드 (ReceiptMatch, 자동/수동 배분 조회)
    └── GP 요약 (매출/매입/GP/GP%/입금/미수)
```
