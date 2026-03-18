# 인증/권한/보안 작업 지침

> 인증, 권한, 보안 관련 코드 작업 시 참조.

---

## 역할 (Role)

- 현재: `admin` / `user` (2단계)
- 향후 확장 예정: `editor` / `viewer`
- 역할 상수는 `app/auth/constants.py`에 정의한다.
- 백엔드 권한 판단 로직에서는 role 문자열 직접 비교보다 `ROLE_ADMIN`, `can_*()`, `require_admin` 같은 공용 경로를 우선 사용한다.

## 권한 체크 패턴

- 기능(Action) 권한: `app/auth/authorization.py`의 `can_*()` 함수 사용
  - 예: `can_manage_users(user)`, `can_manage_policies(user)`, `can_edit_inventory(user)`
- 데이터 가시 범위는 프로젝트 기준 helper로 통일한다.
  - 예: `apply_project_scope(query, user)`
- 서비스 레이어에서도 `current_user.role` 직접 비교 대신 공용 helper를 우선 사용한다.
- 단건 수정/삭제 엔드포인트는 서비스에서 대상 리소스가 속한 프로젝트를 역추적한 뒤 scope helper로 권한을 확인한다.
- 라우터 수준 보호: `dependencies=[Depends(require_admin)]`
- 엔드포인트 수준 보호: `_admin: User = Depends(require_admin)`

## 예외 처리

- 인증/권한 의존성도 `HTTPException` 직접 사용 대신 프로젝트 커스텀 예외를 사용한다.
- 인증/권한 실패 응답은 전역 예외 핸들러로 일관되게 반환한다.

## 초기 관리자

- 첫 관리자 계정은 UI에서 생성하지 않는다.
- `BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME` 환경변수로 bootstrap한다.
- bootstrap은 활성 관리자 계정이 하나도 없을 때만 사용한다.

## 프론트엔드 권한

- `/api/v1/auth/me` 응답에 `permissions` 딕셔너리를 포함한다.
- 템플릿에서는 `me.permissions.can_*` 기반으로 UI 요소를 표시/숨김한다.
- `me.role === 'admin'` 직접 비교는 피한다.

## 비밀번호 정책

- 최소 길이와 정책 값은 설정 또는 `app/config.py` 기본값으로 관리한다.
- 정책 검증은 인증 서비스 레이어에서 수행한다.
- 초기 비밀번호 정책은 운영 환경에 맞게 bootstrap 시점에만 사용한다.

## 보안 원칙

- 기본 전제는 사내 네트워크 전용이다.
- 공개 엔드포인트는 기본 금지한다.
- 예외적으로 로그인 부트스트랩에 필요한 엔드포인트와 페이지(`POST /api/v1/auth/login`, `/login`)만 공개를 허용한다.
- 새 공개 엔드포인트를 추가하면 이유와 보호 범위를 문서에 함께 기록한다.
- 민감한 연락처, 정책 예외 사유, 인프라 정보는 로그에 출력하지 않는다.
- SQL 인젝션 방지: ORM을 통한 쿼리만 허용하고, raw SQL 사용 시 파라미터 바인딩을 강제한다.
