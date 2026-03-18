"""Role CRUD 서비스 (관리자 전용)."""
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.role import Role
from app.modules.common.schemas.role import RoleCreate, RoleUpdate


def list_roles(db: Session) -> list[Role]:
    """전체 역할 목록 반환."""
    return db.query(Role).order_by(Role.is_system.desc(), Role.name).all()


def get_role(db: Session, role_id: int) -> Role:
    """역할 단건 조회. 미존재 시 NotFoundError."""
    role = db.get(Role, role_id)
    if not role:
        raise NotFoundError("역할을 찾을 수 없습니다.")
    return role


def create_role(db: Session, data: RoleCreate) -> Role:
    """커스텀 역할 생성."""
    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise DuplicateError(f"이미 존재하는 역할명입니다: {data.name}")
    role = Role(
        name=data.name,
        is_system=False,
        permissions=data.permissions,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role_id: int, data: RoleUpdate) -> Role:
    """역할 수정. 시스템 역할은 permissions만 수정 가능."""
    role = get_role(db, role_id)
    changes = data.model_dump(exclude_unset=True)
    if role.is_system and "name" in changes:
        raise BusinessRuleError("시스템 역할의 이름은 변경할 수 없습니다.")
    if "name" in changes:
        dup = db.query(Role).filter(Role.name == changes["name"], Role.id != role_id).first()
        if dup:
            raise DuplicateError(f"이미 존재하는 역할명입니다: {changes['name']}")
    for field, value in changes.items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> None:
    """역할 삭제. 시스템 역할은 삭제 불가."""
    role = get_role(db, role_id)
    if role.is_system:
        raise BusinessRuleError("시스템 역할은 삭제할 수 없습니다.")
    # 해당 역할을 사용 중인 사용자가 있는지 확인
    from app.modules.common.models.user import User

    user_count = db.query(User).filter(User.role_id == role_id).count()
    if user_count > 0:
        raise BusinessRuleError(
            f"이 역할을 사용 중인 사용자가 {user_count}명 있습니다. 먼저 역할을 변경해 주세요."
        )
    db.delete(role)
    db.commit()
