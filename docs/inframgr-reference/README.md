# SI 프로젝트 인벤토리 관리 시스템

대형 SI 프로젝트 수행 중 분산 관리되던 기술 자산, IP, 포트맵, 정책 현황, 업체/담당자 정보를
하나의 웹앱에서 관리하기 위한 사내 전용 프로젝트 인벤토리 시스템.

> **현재 상태**: 설계 및 MVP 구현 준비 단계
>
> **문서 안내** — 코딩 규칙은 `CLAUDE.md`, 작업 지침은 `docs/guidelines/`, 아키텍처는 `docs/ARCHITECTURE.md`,
> 결정 기록은 `docs/DECISIONS.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.
> 엔트리포인트/초기화 구조, API 엔드포인트, 데이터 모델의 1차 기준은 소스 코드(`app/startup/`, `app/routers/`, `app/models/`)다.

---

## 프로젝트 목표

본 시스템은 PM Tool이 아니다.

목표는 다음과 같다.

- 프로젝트 단계 및 산출물 현황 관리
- Asset 중심 기술 인벤토리 관리
- IP 인벤토리와 포트맵의 단일 원장화
- 정책 기준과 적용 상태 분리 관리
- 업체 및 담당자 연락망의 중앙화

다음 기능은 MVP 범위에서 제외한다.

- 태스크 관리
- 간트 차트
- 메시징
- 알림
- 일정 관리
- 외부 시스템 연동

---

## 핵심 흐름

```text
[프로젝트 생성]
      ↓
프로젝트 기본정보 / 단계 / 산출물 등록
      ↓
Asset 등록
  ├─ IP 인벤토리 연결
  ├─ PortMap 연결
  ├─ 정책 적용 상태 연결
  └─ 담당자 연결
      ↓
[프로젝트 단위 조회]
  ├─ 프로젝트 개요
  ├─ 기술 자산 목록
  ├─ IP 인벤토리
  ├─ 포트맵
  ├─ 정책 현황
  └─ 업체 / 담당자 연락처
```

---

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 백엔드 | Python 3.11+, FastAPI |
| ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL |
| 프론트엔드 | Jinja2 + HTMX + AG Grid Community |
| 인증 | 세션 기반 |
| 포매터/린터 | black, ruff |
| 테스트 | pytest |

---

## 실행 방법

### 사전 요구사항

- Python 3.11 이상
- PostgreSQL
- pip

또는

- Docker Desktop (WSL2 backend)
- Docker Compose

### 설치 및 실행

```bash
# 1. 의존성 설치
python -m pip install -r requirements.txt

# 2. 환경변수 파일 생성
copy .env.example .env

# 3. 마이그레이션 적용
alembic upgrade head

# 4. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- 비개발 환경에서는 `SESSION_SECRET_KEY`가 없으면 앱이 시작되지 않아야 한다.
- 로컬 Python 실행도 루트 `.env` 파일을 읽는다.
- 스키마 변경 기준은 SQLAlchemy `create_all()`이 아니라 Alembic migration이다.
- 최초 실행 시 활성 관리자 계정이 없으면 bootstrap 환경변수로 첫 관리자 계정을 생성한다.

### Docker Compose 실행

```bash
# 1. 컨테이너 빌드 및 기동
copy .env.example .env
docker compose up --build

# 2. 앱 접속
# http://localhost:9000
```

- `app` 컨테이너는 PostgreSQL 준비 상태를 기다린 뒤 `alembic upgrade head`를 실행하고 서버를 시작한다.
- 기본 compose 구성은 `pjtmgr-db` PostgreSQL 서비스와 FastAPI 앱 서비스로 동작한다.
- `app`, `pjtmgr-db` 서비스 모두 `restart: unless-stopped`로 설정되어 있어 Docker 엔진과 Docker Desktop이 올라오면 자동 재기동된다.
- 운영형 값은 `docker-compose.yml`에 하드코딩하지 않고 루트 `.env`에서 주입한다. 배포 전에는 `.env.example` 복사 후 실제 값으로 치환해야 한다.
- 운영 환경에서는 `APP_ENV`, `SESSION_SECRET_KEY`, DB 계정, bootstrap 관리자 비밀번호를 안전한 값으로 변경해야 한다.
- Windows + WSL2 환경에서는 성능을 위해 가능하면 저장소를 WSL 내부 경로에서 다루는 편이 낫다.
- 호스트 공개 포트는 앱 `9000`, DB `5432` 기준이다.

---

## 아키텍처 개요

```text
[브라우저]
  └─ HTML (Jinja2) + HTMX + AG Grid
       │
[FastAPI 서버]
  ├─ 페이지 라우터
  ├─ API 라우터 (/api/v1/...)
  ├─ 서비스 레이어
  ├─ 인증/세션 레이어
  └─ SQLAlchemy ORM
       │
   [PostgreSQL]
```

- API와 템플릿 렌더링을 같은 FastAPI 인스턴스에서 처리한다.
- 화면은 프로젝트 상세와 인벤토리 그리드 중심으로 구성한다.
- 구조 설계 상세는 `docs/ARCHITECTURE.md`를 따른다.

---

## MVP 범위

| 영역 | 주요 기능 |
| ---- | -------- |
| 프로젝트 관리 | 프로젝트 기본정보, 단계, 산출물 제출 현황 |
| 기술 자산 | Asset CRUD, 유형/역할/환경/상태 관리 |
| 네트워크 | IP 인벤토리, 포트맵 CRUD |
| 정책 | 정책 정의, 프로젝트/자산별 적용 상태 |
| 연락망 | Partner / Contact / AssetContact 관리 |
| 시스템 | 로그인, 세션 기반 인증, 관리자 bootstrap |

---

## 문서 구조

- `README.md`: 프로젝트 소개, 실행 방법, 현재 상태
- `CLAUDE.md`: 상위 개발 지침, 문서 갱신 규칙, 완료 조건
- `docs/ARCHITECTURE.md`: 전체 구조, DB 스키마, API, MVP 단계
- `docs/guidelines/`: 백엔드, 인증/권한, 프론트엔드, Excel 작업별 상세 규칙
- `docs/DECISIONS.md`: 구조/정책 결정 기록
- `docs/KNOWN_ISSUES.md`: 아직 해소되지 않은 제약과 우회
- `docs/PROJECT_CONTEXT.md`: 프로젝트 배경, 사용자, 문제 정의
- `docs/PROJECT_STRUCTURE.md`: 파일 단위 프로젝트 구조와 모듈별 역할

---

## 향후 확장

- Excel Import/Export
- 감사 로그
- 정책 점검 리포트
- 역할 세분화
- 외부 시스템 연동

다만 이들은 MVP 이후 단계에서 검토한다.
