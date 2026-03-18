import csv
import io
import logging

from sqlalchemy.orm import Session

from app.core.config import PASSWORD_MIN_LENGTH
from app.modules.common.models.user import User
from app.modules.common.schemas.user import UserCreate, UserUpdate
from app.core.auth.constants import ROLE_ADMIN, ROLE_USER
from app.core.auth.password import hash_password
from app.core.exceptions import NotFoundError, BusinessRuleError

logger = logging.getLogger(__name__)


def _warn_short_initial_password(login_id: str) -> None:
    """초기 비밀번호(login_id)가 최소 길이 미만이면 경고 로그 기록."""
    if login_id and len(login_id) < PASSWORD_MIN_LENGTH:
        logger.warning(
            "사용자 '%s'의 초기 비밀번호(login_id)가 최소 길이(%d)보다 짧습니다.",
            login_id,
            PASSWORD_MIN_LENGTH,
        )


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.department, User.name).all()


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: UserCreate) -> User:
    obj = User(**data.model_dump())
    # 초기 비밀번호: login_id 값 사용 (로그인 후 변경 강제)
    if obj.login_id:
        obj.hashed_password = hash_password(obj.login_id)
        obj.must_change_password = True
        _warn_short_initial_password(obj.login_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == ROLE_ADMIN, User.is_active.is_(True)).count()


def ensure_bootstrap_admin(
    db: Session,
    *,
    login_id: str | None,
    password: str | None,
    name: str,
) -> User | None:
    """초기 관리자 1명을 환경변수 기반으로 생성한다."""
    if _active_admin_count(db) > 0:
        return None
    if not login_id or not password:
        return None

    if len(password) < PASSWORD_MIN_LENGTH:
        raise BusinessRuleError(
            f"BOOTSTRAP_ADMIN_PASSWORD는 {PASSWORD_MIN_LENGTH}자 이상이어야 합니다."
        )

    existing = db.query(User).filter(User.login_id == login_id).first()
    if existing:
        existing.name = name or existing.name
        existing.role = ROLE_ADMIN
        existing.is_active = True
        existing.hashed_password = hash_password(password)
        existing.must_change_password = True
        db.commit()
        db.refresh(existing)
        return existing

    user = User(
        login_id=login_id,
        name=name,
        role=ROLE_ADMIN,
        is_active=True,
        hashed_password=hash_password(password),
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """사용자 삭제. 미존재 시 NotFoundError, 관리자 삭제 시 BusinessRuleError."""
    from app.modules.accounting.models.contract import Contract

    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("사용자를 찾을 수 없습니다.")
    if obj.role == ROLE_ADMIN:
        raise BusinessRuleError("관리자 계정은 삭제할 수 없습니다. 비활성화만 가능합니다.")
    # 담당 사업의 owner를 해제하여 고아 FK 방지
    db.query(Contract).filter(Contract.owner_user_id == user_id).update(
        {"owner_user_id": None}, synchronize_session="fetch"
    )
    db.delete(obj)
    db.commit()


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    """사용자 수정. 미존재 시 NotFoundError, 비즈니스 규칙 위반 시 BusinessRuleError."""
    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("사용자를 찾을 수 없습니다.")
    changes = data.model_dump(exclude_unset=True)
    # 관리자 비활성화 시 다른 활성 관리자 존재 여부 확인
    if obj.role == ROLE_ADMIN and changes.get("is_active") is False:
        other_active_admins = (
            db.query(User)
            .filter(User.role == ROLE_ADMIN, User.is_active.is_(True), User.id != user_id)
            .count()
        )
        if other_active_admins == 0:
            raise BusinessRuleError("마지막 활성 관리자 계정은 비활성화할 수 없습니다.")
    for field, value in changes.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def reset_password(db: Session, user_id: int) -> None:
    """관리자가 사용자 비밀번호를 login_id로 초기화. 다음 로그인 시 변경 강제."""
    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("사용자를 찾을 수 없습니다.")
    if not obj.login_id:
        raise BusinessRuleError("로그인 ID가 설정되지 않은 사용자는 비밀번호를 초기화할 수 없습니다.")
    _warn_short_initial_password(obj.login_id)
    obj.hashed_password = hash_password(obj.login_id)
    obj.must_change_password = True
    db.commit()


_CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]


def _decode_csv(file_bytes: bytes) -> str:
    for enc in _CSV_ENCODINGS:
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise BusinessRuleError(f"지원되지 않는 인코딩입니다. 지원 형식: {', '.join(_CSV_ENCODINGS)}", status_code=422)


def import_contacts_csv(db: Session, file_bytes: bytes) -> dict:
    """아웃룩 연락처 CSV → users 테이블 임포트.
    중복 기준: login_id(이메일).
    - 신규: 사용자 생성
    - 기존: 부서·직급 등 추가 정보가 있으면 업데이트
    인코딩 자동 감지: utf-8-sig → utf-8 → cp949 → euc-kr 순서로 시도.
    """
    text = _decode_csv(file_bytes)
    reader = csv.DictReader(io.StringIO(text))

    existing_users: dict[str, User] = {
        u.login_id: u
        for u in db.query(User).filter(User.login_id.isnot(None)).all()
    }

    created = updated = skipped = 0
    for row in reader:
        last = (row.get("성") or "").strip()
        first = (row.get("이름") or "").strip()
        name = (last + first).strip()
        if not name:
            skipped += 1
            continue

        login_id = (row.get("전자 메일 주소") or "").strip() or None
        department = (row.get("부서") or "").strip() or None
        position = (row.get("직함") or "").strip() or None

        if login_id and login_id in existing_users:
            # 기존 사용자: CSV에 값이 있으면 덮어쓰기
            user = existing_users[login_id]
            changed = False
            for attr, val in [("department", department), ("position", position)]:
                if val and getattr(user, attr) != val:
                    setattr(user, attr, val)
                    changed = True
            if changed:
                updated += 1
            else:
                skipped += 1
            continue

        user = User(
            name=name,
            department=department,
            position=position,
            login_id=login_id,
            role=ROLE_USER,
            is_active=True,
        )
        if login_id:
            user.hashed_password = hash_password(login_id)
            user.must_change_password = True
            _warn_short_initial_password(login_id)
        db.add(user)
        if login_id:
            existing_users[login_id] = user
        created += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
