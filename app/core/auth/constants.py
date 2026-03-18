"""역할(Role) 및 행위(Action) 상수 정의.

RBAC 전환 후: 역할은 Role 테이블(permissions JSON)로 관리한다.
ROLE_ADMIN / ROLE_USER 상수는 하위 호환 및 편의를 위해 유지하되,
실제 권한 판단은 user.role_obj.permissions를 통해 수행한다.
"""

# ── 역할 (레거시 호환 상수) ──
# 실제 권한 판단은 user.role_obj.permissions["admin"] 등으로 수행.
ROLE_ADMIN = "admin"
ROLE_USER = "user"


# ── 행위(Action) — Phase 4 authorization에서 활용 ──
class Action:
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    IMPORT = "import"
    EXPORT = "export"
    REPORT_VIEW = "report_view"
