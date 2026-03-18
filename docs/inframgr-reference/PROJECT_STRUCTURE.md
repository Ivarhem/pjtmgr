# 프로젝트 구조

> 파일 단위 프로젝트 구조와 모듈별 역할.
> 디렉토리/파일 추가·삭제 시 이 문서도 함께 갱신한다.

---

## 앱 엔트리포인트

```text
app/
├── main.py                  # uvicorn 엔트리포인트
├── app_factory.py           # FastAPI 앱 생성, 전역 예외 핸들러 등록
├── config.py                # 환경변수·설정값 로드
├── database.py              # SQLAlchemy 엔진·세션 설정
└── exceptions.py            # 커스텀 예외 클래스
```

## 인증·인가

```text
app/auth/
├── authorization.py         # can_*() 권한 함수, project scope helper
├── constants.py             # 역할 상수 (ROLE_ADMIN 등)
├── dependencies.py          # get_current_user, require_admin
├── middleware.py            # 세션 인증 미들웨어
├── password.py              # 비밀번호 해싱
├── router.py                # /api/v1/auth 라우터
└── service.py               # 인증 서비스
```

## 모델 (ORM)

```text
app/models/
├── base.py                  # TimestampMixin, Base 클래스
├── project.py               # Project
├── project_phase.py         # ProjectPhase
├── project_deliverable.py   # ProjectDeliverable
├── asset.py                 # Asset
├── asset_ip.py              # AssetIP
├── ip_subnet.py             # IpSubnet (IP 대역 인벤토리)
├── port_map.py              # PortMap
├── policy_definition.py     # PolicyDefinition
├── policy_assignment.py     # PolicyAssignment
├── partner.py               # Partner
├── contact.py               # Contact
├── asset_contact.py         # AssetContact
├── user.py                  # User
├── login_failure.py         # LoginFailure
└── audit_log.py             # AuditLog (MVP 이후)
```

## 스키마 (Pydantic)

```text
app/schemas/
├── auth.py                  # LoginRequest, ChangePasswordRequest
├── project.py               # Project Create, Update, Read
├── project_phase.py         # ProjectPhase 스키마
├── project_deliverable.py   # ProjectDeliverable 스키마
├── asset.py                 # Asset 스키마
├── asset_ip.py              # AssetIP 스키마
├── ip_subnet.py             # IpSubnet 스키마
├── port_map.py              # PortMap 스키마
├── policy_definition.py     # PolicyDefinition 스키마
├── policy_assignment.py     # PolicyAssignment 스키마
├── partner.py               # Partner 스키마
├── contact.py               # Contact 스키마
├── asset_contact.py         # AssetContact 스키마
└── user.py                  # User 스키마
```

## 라우터 (API / Pages)

```text
app/routers/
├── pages.py                 # HTML 페이지 렌더링 (Jinja2)
├── projects.py              # /api/v1/projects
├── project_phases.py        # /api/v1/project-phases
├── project_deliverables.py  # /api/v1/project-deliverables
├── assets.py                # /api/v1/assets
├── asset_ips.py             # /api/v1/asset-ips
├── ip_subnets.py            # /api/v1/ip-subnets
├── port_maps.py             # /api/v1/port-maps
├── policies.py              # /api/v1/policies
├── policy_assignments.py    # /api/v1/policy-assignments
├── partners.py              # /api/v1/partners
├── contacts.py              # /api/v1/contacts
├── asset_contacts.py        # /api/v1/asset-contacts
└── users.py                 # /api/v1/users
```

## 서비스 (비즈니스 로직)

```text
app/services/
├── project_service.py       # 프로젝트 CRUD, 개요 조회
├── phase_service.py         # 프로젝트 단계 / 산출물
├── asset_service.py         # Asset CRUD
├── network_service.py       # AssetIP, IpSubnet, PortMap, IP 중복 검증
├── policy_service.py        # 정책 정의 / 적용 상태
├── partner_service.py       # Partner / Contact / AssetContact
├── user_service.py          # 사용자 관리
└── audit.py                 # 감사 로그 유틸 (MVP 이후)
```

## 초기화

```text
app/startup/
├── database_init.py         # 앱 시작 시 DB 연결 확인
└── bootstrap.py             # 초기 관리자 계정 생성
```

## 프론트엔드

```text
app/static/
├── js/
│   ├── utils.js             # 공통 유틸
│   ├── projects.js          # 프로젝트 목록 / 상세
│   ├── assets.js            # Asset 인벤토리
│   ├── ip_inventory.js      # IP 인벤토리
│   ├── port_maps.js         # PortMap 인벤토리
│   ├── policies.js          # 정책 현황
│   ├── partners.js          # 업체 / 담당자
│   └── users.js             # 사용자 관리
├── css/
│   ├── base.css             # 전역 스타일, CSS 변수
│   ├── components.css       # 재사용 컴포넌트
│   ├── projects.css         # 프로젝트 화면
│   ├── assets.css           # Asset 화면
│   ├── policies.css         # 정책 화면
│   ├── contacts.css         # 연락망 화면
│   ├── login.css            # 로그인 전용
│   └── change_password.css  # 비밀번호 변경 전용
└── img/                     # 이미지 리소스

app/templates/
├── base.html                # 공통 레이아웃
├── index.html               # 메인
├── login.html               # 로그인
├── change_password.html     # 비밀번호 변경
├── projects.html            # 프로젝트 목록
├── project_detail.html      # 프로젝트 상세
├── assets.html              # Asset 인벤토리
├── ip_inventory.html        # IP 인벤토리
├── port_maps.html           # PortMap 인벤토리
├── policies.html            # 정책 관리
├── partners.html            # 업체 / 담당자
└── users.html               # 사용자 관리
```

## 테스트

```text
tests/
├── conftest.py              # 테스트 DB, 세션, 픽스처
├── test_project_service.py  # 프로젝트 CRUD
├── test_phase_service.py    # 단계 / 산출물
├── test_asset_service.py    # Asset CRUD
├── test_network_service.py  # AssetIP / PortMap / 중복 검증
├── test_policy_service.py   # 정책 정의 / 적용 상태
├── test_partner_service.py  # 업체 / 담당자 / 자산 연결
├── test_auth_service.py     # 인증 서비스
├── test_database.py         # DB 스키마 테스트
└── test_startup.py          # bootstrap, lifespan 테스트
```

## DB 마이그레이션

```text
alembic/
├── env.py                   # Alembic 환경 설정
└── versions/
    ├── 20260317_1300_initial_inventory_schema.py
    └── 20260317_1400_add_ip_subnets_table.py
```

## 컨테이너 실행 파일

```text
docker/
└── entrypoint.sh            # DB 준비 대기 후 Alembic 적용, 앱 실행
```

## 루트 파일

```text
├── alembic.ini              # Alembic 설정
├── docker-compose.yml       # 로컬 컨테이너 오케스트레이션
├── Dockerfile               # FastAPI 앱 이미지 빌드
├── requirements.txt         # Python 의존성
├── pytest.ini               # pytest import path 설정
├── .dockerignore            # Docker 빌드 제외 대상
├── .env.example             # 환경변수 예시 템플릿
├── .env                     # 환경변수 (git 미추적)
├── CLAUDE.md                # 상위 개발 지침
└── README.md                # 프로젝트 소개
```
