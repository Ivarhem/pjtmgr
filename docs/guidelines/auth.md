# 인증/권한/보안 작업 지침

> 인증, 권한, 보안 관련 코드 작업 시 참조.

---

## 역할 (Role)

- 현재: `admin` / `user` (2단계)
- 향후 확장 예정: `manager` / `viewer` 추가
- 역할 상수는 `app/auth/constants.py`에 정의한다.
- 백엔드 권한 판단 로직에서는 `"admin"` 같은 role 문자열 직접 비교보다 `ROLE_ADMIN`, `can_*()`, `require_admin` 같은 공용 경로를 우선 사용한다.
- UI 선택값, API payload literal, 테스트 fixture처럼 role 값을 그대로 주고받는 경계에서는 문자열 literal 사용을 허용한다.

## 권한 체크 패턴

- 기능(Action) 권한: `app/auth/authorization.py`의 `can_*()` 함수 사용
  - 예: `can_delete_contract(user)`, `can_manage_users(user)`, `can_import(user)`
- 데이터 가시 범위: `apply_contract_scope(query, user)` — admin은 전체, user는 본인 담당만
- 인증/권한 dependency(`require_admin` 등)도 가능하면 `authorization.py` helper 또는 역할 helper를 통해 판단하고, dependency 내부에 직접 role 비교 로직을 중복하지 않는다.
- 서비스 레이어에서도 `current_user.role` 직접 비교 대신 `authorization.py`의 helper(`can_*`, `has_full_contract_scope`, `apply_contract_scope`, `list_accessible_contract_ids`)를 우선 사용한다.
- `PATCH /.../{id}`, `DELETE /.../{id}`처럼 상위 계약 ID가 path에 없는 단건 엔드포인트는 서비스에서 대상 리소스가 속한 계약을 역추적한 뒤 scope helper 또는 `check_contract_access()`로 권한을 확인한다.
- 라우터 수준 보호: `dependencies=[Depends(require_admin)]` (users 라우터 등)
- 엔드포인트 수준 보호: `_admin: User = Depends(require_admin)` (개별 엔드포인트)

## 예외 처리

- 인증/권한 의존성(`get_current_user`, `require_admin`)도 `HTTPException` 직접 사용 대신 프로젝트 커스텀 예외(`UnauthorizedError`, `PermissionDeniedError`)를 사용한다.
- 인증/권한 실패 응답은 전역 예외 핸들러로 일관되게 반환한다.
- `AuthMiddleware`를 포함한 인증 경로도 직접 `Response`를 만들기보다 커스텀 예외를 통해 전역 핸들러 경로를 우선 사용한다.

## 초기 관리자

- 첫 관리자 계정은 UI에서 생성하지 않는다. `BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME` 환경변수로 bootstrap한다.
- bootstrap은 활성 관리자 계정이 하나도 없을 때만 사용한다.
- 운영 반영 후 bootstrap 계정 정보는 안전하게 관리하고, 필요 시 환경변수 제거 또는 교체 절차를 따른다.

## 프론트엔드 권한

- `/api/v1/auth/me` 응답에 `permissions` 딕셔너리 포함
- 템플릿에서 `me.permissions.can_*` 기반으로 UI 요소 표시/숨김
- `me.role === 'admin'` 직접 비교 금지 → `me.permissions.can_manage_users` 등 사용

## 비밀번호 정책

- 최소 길이: `settings["auth.password_min_length"]` 우선, 미설정 시 `app/config.py`의 `PASSWORD_MIN_LENGTH` 기본값 사용
- 정책 검증 위치: `app/auth/service.py`가 현재 설정값을 조회해 검증. Pydantic 스키마에는 동적 길이 정책을 하드코딩하지 않는다.
- 해싱: PBKDF2-SHA256, 260,000 iterations (`app/auth/password.py`)
- 초기 비밀번호: 사용자 생성 시 `login_id` 값으로 설정, 첫 로그인 시 변경 강제 (`must_change_password=True`)
- 관리자 초기화: 비밀번호를 `login_id`로 리셋 + 변경 강제
- 시스템 관리 화면에서 최소 길이를 바꿀 수 있어도 초기 비밀번호는 기존 `login_id` 정책을 유지하므로, 운영 시 login_id 길이와 정책 길이의 차이를 고려한다.

## 보안 원칙

- 사내 네트워크에서만 접근 가능하도록 네트워크 레벨에서 차단한다.
- 공개 엔드포인트는 기본 금지한다.
- 예외적으로 인증 부트스트랩에 필요한 엔드포인트와 페이지(`POST /api/v1/auth/login`, `/login`)는 공개를 허용한다.
- `GET /api/v1/health`는 컨테이너 헬스체크용으로 공개 허용 (인증 불요, DB 연결 상태만 반환).
- `GET /api/v1/health` 응답에는 내부 예외 문자열이나 민감한 진단 정보를 포함하지 않고, `ok` / `degraded` 수준의 상태만 외부에 노출한다.
- 새 공개 엔드포인트를 추가하면 이유, 보호 범위, 관련 UI 흐름을 이 문서에 함께 기록한다.
- Excel Import는 관리자 전용 (`require_admin` 의존성 적용)
- Receipt, TransactionLine, ReceiptMatch처럼 계약 하위 리소스를 조합하는 작업은 입력된 ID들이 같은 계약 범위에 속하는지도 함께 검증한다.
- 금액, 거래처 정보 등 민감 데이터를 로그에 출력하지 않는다.
- SQL 인젝션 방지: ORM을 통한 쿼리만 허용, raw SQL 사용 시 파라미터 바인딩 필수.
