# 인증/권한/보안 작업 지침

> 인증, 권한, 보안 관련 코드 작업 시 참조.

---

## 역할 (Role) — RBAC

- Role 모델: `app/modules/common/models/role.py`
- `permissions` JSON 컬럼으로 모듈별 접근 수준 관리
- 기본 역할 (is_system=True, 삭제/수정 불가):

  | 역할명 | admin | accounting | infra |
  | ------ | ----- | ---------- | ----- |
  | 관리자 | true | full | full |
  | 영업담당자 | false | full | null |
  | 기술담당자 | false | null | full |
  | PM | false | full | full |

- 관리자가 커스텀 역할 생성 가능
- 권한 수준: `null`(접근 불가), `"read"`(조회만), `"full"`(CRUD 전체), `admin` 플래그(시스템 관리)
- 역할 상수 및 공통 권한 함수는 `app/core/auth/` 에 정의한다.
- 백엔드 권한 판단 로직에서는 `"admin"` 같은 role 문자열 직접 비교보다 `can_*()`, `require_admin`, `require_module_access()` 같은 공용 경로를 우선 사용한다.
- UI 선택값, API payload literal, 테스트 fixture처럼 role 값을 그대로 주고받는 경계에서는 문자열 literal 사용을 허용한다.

## 모듈 접근 제어

- `require_module_access(module, min_level)` 의존성으로 라우터 레벨에서 접근 제어:

```python
# app/core/auth/dependencies.py
def require_module_access(module: str, min_level: str = "read"):
    """라우터 Depends로 사용. read/full 수준 검사."""
    def checker(current_user: User = Depends(get_current_user)):
        level = get_module_access_level(current_user, module)
        if level is None:
            raise PermissionDeniedError("모듈 접근 권한 없음")
        if min_level == "full" and level == "read":
            raise PermissionDeniedError("읽기 전용 권한")
        return current_user
    return Depends(checker)

# 사용 예시
@router.get("/contracts")          # require_module_access("accounting", "read")
@router.post("/contracts")         # require_module_access("accounting", "full")
@router.delete("/contracts/{id}")  # require_module_access("accounting", "full") + can_delete_contract()
```

- 사용자 가시 모듈 = `ENABLED_MODULES` ∩ `user.role.permissions.modules`
- `read` 수준 사용자가 POST/PATCH/DELETE 엔드포인트에 접근하면 403 반환

## 권한 체크 패턴

- 공통 권한 함수 (`app/core/auth/authorization.py`):
  - `can_manage_users(user)`, `can_manage_settings(user)`, `require_admin(user)`
  - `can_access_module(user, module_name)`, `get_module_access_level(user, module_name)`
- 모듈 고유 권한 — 각 모듈 서비스 내부에 배치:
  - 회계: `can_delete_contract(user)`, `can_delete_transaction_line(user)`, `can_import(user)`, `apply_contract_scope(query, user)` 등
  - 인프라: `can_edit_inventory(user)`, `can_manage_policies(user)` 등
- 인증/권한 dependency(`require_admin` 등)도 가능하면 `authorization.py` helper를 통해 판단하고, dependency 내부에 직접 role 비교 로직을 중복하지 않는다.
- 서비스 레이어에서도 `current_user.role` 직접 비교 대신 authorization helper를 우선 사용한다.
- `DELETE` 같은 파괴적 action은 service가 scope 확인과 action helper(`can_delete_*`) 검증을 모두 수행한다. router의 `require_admin`은 보조 장치일 뿐 단독 source of truth가 아니다.
- `PATCH /.../{id}`, `DELETE /.../{id}`처럼 상위 계약 ID가 path에 없는 단건 엔드포인트는 서비스에서 대상 리소스가 속한 계약을 역추적한 뒤 scope helper 또는 `check_contract_access()`로 권한을 확인한다.
- 라우터 수준 보호: `dependencies=[Depends(require_admin)]` (users 라우터 등)
- 엔드포인트 수준 보호: `_admin: User = Depends(require_admin)` (개별 엔드포인트)

## 예외 처리

- 인증/권한 의존성(`get_current_user`, `require_admin`)도 `HTTPException` 직접 사용 대신 프로젝트 커스텀 예외(`UnauthorizedError`, `PermissionDeniedError`)를 사용한다.
- 커스텀 예외 위치: `app/core/exceptions.py`
- 인증/권한 실패 응답은 전역 예외 핸들러로 일관되게 반환한다.
- `AuthMiddleware`를 포함한 인증 경로도 직접 `Response`를 만들기보다 커스텀 예외를 통해 전역 핸들러 경로를 우선 사용한다.

## 초기 관리자

- 첫 관리자 계정은 UI에서 생성하지 않는다. `BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME` 환경변수로 bootstrap한다.
- bootstrap은 활성 관리자 계정이 하나도 없을 때만 사용한다.
- 운영 반영 후 bootstrap 계정 정보는 안전하게 관리하고, 필요 시 환경변수 제거 또는 교체 절차를 따른다.

## 프론트엔드 권한

- `/api/v1/auth/me` 응답에 `permissions` 딕셔너리 포함
- 템플릿에서 `me.permissions.can_*` 기반으로 UI 요소 표시/숨김
- `me.role === 'admin'` 직접 비교 금지 -> `me.permissions.can_manage_users` 등 사용

## 비밀번호 정책

- 최소 길이: `settings["auth.password_min_length"]` 우선, 미설정 시 `app/core/config.py`의 `PASSWORD_MIN_LENGTH` 기본값 사용
- 정책 검증 위치: `app/core/auth/service.py`가 현재 설정값을 조회해 검증. Pydantic 스키마에는 동적 길이 정책을 하드코딩하지 않는다.
- 해싱: bcrypt (`app/core/auth/password.py`)
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
