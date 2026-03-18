"""역할(Role) 및 행위(Action) 상수 정의.

현재는 admin / user 두 역할만 활성 사용.
향후 manager / viewer 등 확장 시 Role Literal에 추가하면
스키마 검증·authorization 로직이 자동 확장됨.
"""
from typing import Literal

# ── 역할 ──
Role = Literal["admin", "user"]
# 향후 확장: Role = Literal["admin", "manager", "user", "viewer"]

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
