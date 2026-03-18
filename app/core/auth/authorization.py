"""권한 판단 헬퍼.

라우터/서비스에서 직접 role 비교하지 않고 이 모듈을 통해 판단한다.
RBAC: user.role_obj.permissions (JSON) 기반으로 판단한다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_

if TYPE_CHECKING:
    from sqlalchemy.orm import Query, Session

    from app.modules.common.models.user import User
    from app.modules.accounting.models.contract import Contract


# ── 헬퍼: permissions 접근 ─────────────────────────────────────

def _is_admin(user: User) -> bool:
    """user.role_obj.permissions의 admin 플래그 확인."""
    perms = getattr(user, "role_obj", None)
    if perms is None:
        return False
    return bool(user.role_obj.permissions.get("admin", False))


def can_access_module(user: User, module_name: str) -> bool:
    """사용자가 특정 모듈에 접근 가능한지 반환."""
    if _is_admin(user):
        return True
    perms = getattr(user, "role_obj", None)
    if perms is None:
        return False
    modules = user.role_obj.permissions.get("modules", {})
    return modules.get(module_name) in ("read", "full")


def get_module_access_level(user: User, module_name: str) -> str | None:
    """사용자의 모듈 접근 수준 반환. None/read/full."""
    if _is_admin(user):
        return "full"
    perms = getattr(user, "role_obj", None)
    if perms is None:
        return None
    modules = user.role_obj.permissions.get("modules", {})
    level = modules.get(module_name)
    if level in ("read", "full"):
        return level
    return None


def check_resource_permission(user: User, resource: str, action: str) -> None:
    """리소스-행위 단위 권한 검사 (향후 풀 RBAC 확장용).

    TODO: permissions["resources"] 구조가 추가되면 구현.
    현재는 호출 시 NotImplementedError를 발생시킨다.
    """
    raise NotImplementedError(
        "Full resource-level RBAC is not yet implemented. "
        "Use module-level access control (can_access_module / get_module_access_level)."
    )


# ── 기능(Action) 권한 ────────────────────────────────────────

def can_delete_contract(user: User) -> bool:
    return _is_admin(user)


def can_delete_customer(user: User) -> bool:
    return _is_admin(user)


def can_manage_users(user: User) -> bool:
    return _is_admin(user)


def can_manage_settings(user: User) -> bool:
    return _is_admin(user)


def can_delete_transaction_line(user: User) -> bool:
    return _is_admin(user)


def can_delete_receipt(user: User) -> bool:
    return _is_admin(user)


def can_import(user: User) -> bool:
    return _is_admin(user)


def has_full_contract_scope(user: User) -> bool:
    """전체 사업 범위를 조회할 수 있는지 반환."""
    return _is_admin(user)


def can_admin_create_contract(user: User) -> bool:
    """사업관리 화면에서 신규 등록 — 개발/정비용, 실 서비스 배포 시 비활성화."""
    from app.core.config import ENABLE_ADMIN_CONTRACT_CREATE

    return _is_admin(user) and ENABLE_ADMIN_CONTRACT_CREATE


def can_edit_inventory(user: User) -> bool:
    """인프라 인벤토리 편집 권한. admin 또는 infra 모듈 full 접근."""
    if _is_admin(user):
        return True
    return get_module_access_level(user, "infra") == "full"


def can_manage_policies(user: User) -> bool:
    """보안 정책 관리 권한. admin만 가능."""
    return _is_admin(user)


def can_export(user: User) -> bool:
    """현재는 전체 허용. 향후 role별 제한 가능."""
    return True


def can_view_reports(user: User) -> bool:
    """현재는 전체 허용. 향후 manager 이상만 가능하도록 확장 가능."""
    return True


# ── 단건 접근 권한 검증 ──────────────────────────────────────

def check_contract_access(db: "Session", contract_id: int, user: "User") -> None:
    """단건 사업 접근 권한 확인. admin은 전체, user는 본인 담당만."""
    if has_full_contract_scope(user):
        return
    from app.modules.accounting.models.contract import Contract

    contract = (
        db.query(Contract.id)
        .filter(Contract.id == contract_id)
        .filter(_contract_visibility_clause(user))
        .first()
    )
    if not contract:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("사업을 찾을 수 없습니다.")


def check_period_access(db: "Session", period_id: int, user: "User") -> None:
    """기간(period_id) 기반 사업 접근 권한 확인."""
    if has_full_contract_scope(user):
        return
    from app.modules.accounting.models.contract_period import ContractPeriod

    period = db.get(ContractPeriod, period_id)
    if not period:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("기간을 찾을 수 없습니다.")
    check_contract_access(db, period.contract_id, user)


# ── 데이터 행위 권한 ─────────────────────────────────────────

def can_view_contract(user: User, contract: Contract) -> bool:
    """현재: 전체 허용. 향후: owner/department 기반 제한."""
    return True


def can_edit_contract(user: User, contract: Contract) -> bool:
    """현재: 전체 허용. 향후: owner만 수정 가능."""
    return True


# ── 데이터 가시 범위(Scope) ──────────────────────────────────

def apply_contract_scope(query: Query, user: User) -> Query:
    """사용자 역할에 따라 Contract 조회 범위를 필터링.

    현재:
    - admin: 전체 데이터
    - user: 본인 담당 사업만
    """
    if has_full_contract_scope(user):
        return query
    return query.filter(_contract_visibility_clause(user))


def get_owner_filter(user: User) -> int | None:
    """owner_id 필터값 반환. None이면 전체 조회 (admin)."""
    if has_full_contract_scope(user):
        return None
    return user.id


def list_accessible_contract_ids(db: "Session", user: "User") -> list[int]:
    """현재 사용자가 접근 가능한 사업 ID 목록."""
    from app.modules.accounting.models.contract import Contract

    q = db.query(Contract.id)
    q = apply_contract_scope(q, user)
    return [row[0] for row in q.all()]


def _contract_visibility_clause(user: User):
    """Contract owner 또는 Period owner 기준의 가시 범위 조건."""
    from app.modules.accounting.models.contract import Contract
    from app.modules.accounting.models.contract_period import ContractPeriod

    return or_(
        Contract.owner_user_id == user.id,
        Contract.periods.any(ContractPeriod.owner_user_id == user.id),
    )


# ── 권한 컨텍스트 (프론트엔드용) ──────────────────────────────

def get_permissions(user: User) -> dict[str, bool]:
    """현재 사용자의 권한 플래그를 딕셔너리로 반환.

    프론트엔드에서 버튼 표시/숨김에 사용.
    역할 추가 시 이 함수만 수정하면 프론트엔드 코드 변경 불필요.
    """
    return {
        "can_delete_contract": can_delete_contract(user),
        "can_delete_customer": can_delete_customer(user),
        "can_manage_users": can_manage_users(user),
        "can_manage_settings": can_manage_settings(user),
        "can_delete_transaction_line": can_delete_transaction_line(user),
        "can_delete_receipt": can_delete_receipt(user),
        "can_import": can_import(user),
        "can_export": can_export(user),
        "can_view_reports": can_view_reports(user),
        "can_admin_create_contract": can_admin_create_contract(user),
    }
