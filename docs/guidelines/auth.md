# 인증/권한/보안 작업 지침

> 인증, 권한, 보안 관련 코드 작업 시 참조.

---

## 역할 (Role)

- 현재: `admin` / `user` (2단계)
- 향후 확장 예정: `manager` / `viewer` 추가
- 역할 상수는 `app/auth/constants.py`에 정의 — 코드에서 `"admin"` 문자열 직접 사용 금지

## 권한 체크 패턴

- 기능(Action) 권한: `app/auth/authorization.py`의 `can_*()` 함수 사용
  - 예: `can_delete_contract(user)`, `can_manage_users(user)`, `can_import(user)`
- 데이터 가시 범위: `apply_contract_scope(query, user)` — admin은 전체, user는 본인 담당만
- 라우터 수준 보호: `dependencies=[Depends(require_admin)]` (users 라우터 등)
- 엔드포인트 수준 보호: `_admin: User = Depends(require_admin)` (개별 엔드포인트)

## 예외 처리

- 인증/권한 의존성(`get_current_user`, `require_admin`)도 `HTTPException` 직접 사용 대신 프로젝트 커스텀 예외(`UnauthorizedError`, `PermissionDeniedError`)를 사용한다.
- 인증/권한 실패 응답은 전역 예외 핸들러로 일관되게 반환한다.

## 초기 관리자

- 첫 관리자 계정은 UI에서 생성하지 않는다. `BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME` 환경변수로 bootstrap한다.
- bootstrap은 활성 관리자 계정이 하나도 없을 때만 사용한다.
- 운영 반영 후 bootstrap 계정 정보는 안전하게 관리하고, 필요 시 환경변수 제거 또는 교체 절차를 따른다.

## 프론트엔드 권한

- `/api/v1/auth/me` 응답에 `permissions` 딕셔너리 포함
- 템플릿에서 `me.permissions.can_*` 기반으로 UI 요소 표시/숨김
- `me.role === 'admin'` 직접 비교 금지 → `me.permissions.can_manage_users` 등 사용

## 보안 원칙

- 사내 네트워크에서만 접근 가능하도록 네트워크 레벨에서 차단한다.
- 인증 없이 접근 가능한 엔드포인트를 두지 않는다.
- Excel Import는 관리자 전용 (`require_admin` 의존성 적용)
- 금액, 거래처 정보 등 민감 데이터를 로그에 출력하지 않는다.
- SQL 인젝션 방지: ORM을 통한 쿼리만 허용, raw SQL 사용 시 파라미터 바인딩 필수.
