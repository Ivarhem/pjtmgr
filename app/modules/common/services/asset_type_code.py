from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.schemas.asset_type_code import AssetTypeCodeRead


def to_read(at: AssetTypeCode) -> AssetTypeCodeRead:
    return AssetTypeCodeRead(
        type_key=at.type_key, code=at.code, label=at.label,
        sort_order=at.sort_order, is_active=at.is_active,
    )


_SEED = [
    {"type_key": "server", "code": "SVR", "label": "서버", "sort_order": 1},
    {"type_key": "network", "code": "NET", "label": "네트워크", "sort_order": 2},
    {"type_key": "security", "code": "SEC", "label": "보안장비", "sort_order": 3},
    {"type_key": "storage", "code": "STO", "label": "스토리지", "sort_order": 4},
    {"type_key": "middleware", "code": "MID", "label": "미들웨어", "sort_order": 5},
    {"type_key": "application", "code": "APP", "label": "응용", "sort_order": 6},
    {"type_key": "other", "code": "ETC", "label": "기타", "sort_order": 7},
]


def seed_defaults(db: Session) -> None:
    """테이블이 비어있으면 기본 자산유형을 삽입한다."""
    from sqlalchemy import inspect as sa_inspect

    tbl = AssetTypeCode.__table__
    engine = db.get_bind()
    insp = sa_inspect(engine)
    tbl_name = AssetTypeCode.__tablename__

    if insp.has_table(tbl_name):
        existing_cols = {c["name"] for c in insp.get_columns(tbl_name)}
        model_cols = {c.name for c in tbl.columns}
        if model_cols.issubset(existing_cols):
            cnt = db.query(AssetTypeCode).count()
            if cnt > 0:
                return
        else:
            common_cols = sorted(existing_cols & model_cols)
            col_attrs = [tbl.c[c] for c in common_cols]
            with engine.connect() as conn:
                rows = conn.execute(tbl.select().with_only_columns(*col_attrs)).fetchall()
                backup = [dict(zip(common_cols, r)) for r in rows]
            db.close()
            tbl.drop(engine)
            tbl.create(engine)
            if backup:
                with engine.connect() as conn:
                    conn.execute(tbl.insert(), backup)
                    conn.commit()
            return
    else:
        tbl.create(engine)

    with engine.connect() as conn:
        conn.execute(tbl.insert(), _SEED)
        conn.commit()


def list_asset_type_codes(db: Session, *, active_only: bool = True) -> list[AssetTypeCodeRead]:
    q = db.query(AssetTypeCode).order_by(AssetTypeCode.sort_order, AssetTypeCode.type_key)
    if active_only:
        q = q.filter(AssetTypeCode.is_active.is_(True))
    return [to_read(at) for at in q.all()]


def get_valid_type_keys(db: Session) -> set[str]:
    """활성 자산유형 type_key set 반환 (검증용)."""
    rows = db.query(AssetTypeCode.type_key).filter(AssetTypeCode.is_active.is_(True)).all()
    return {r[0] for r in rows}


def get_code_for_type_key(db: Session, type_key: str) -> str:
    """type_key에 대응하는 3자리 코드 반환. 없으면 NotFoundError."""
    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    return at.code


def create_asset_type_code(
    db: Session, type_key: str, code: str, label: str, sort_order: int = 0,
) -> AssetTypeCodeRead:
    if db.get(AssetTypeCode, type_key):
        raise DuplicateError(f"자산유형 '{type_key}'이(가) 이미 존재합니다.")
    existing_code = db.scalar(select(AssetTypeCode).where(AssetTypeCode.code == code))
    if existing_code:
        raise DuplicateError(f"유형코드 '{code}'이(가) 이미 사용 중입니다.")
    at = AssetTypeCode(type_key=type_key, code=code, label=label, sort_order=sort_order)
    db.add(at)
    db.commit()
    return to_read(at)


def update_asset_type_code(db: Session, type_key: str, *, updates: dict) -> AssetTypeCodeRead:
    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    updates.pop("code", None)
    updates.pop("type_key", None)
    for k, v in updates.items():
        if hasattr(at, k):
            setattr(at, k, v)
    db.commit()
    return to_read(at)


def delete_asset_type_code(db: Session, type_key: str) -> None:
    from app.modules.infra.models.asset import Asset

    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    count = db.query(Asset).filter(Asset.asset_type == type_key).count()
    if count > 0:
        raise DuplicateError(f"이 유형의 자산이 {count}건 존재하여 삭제할 수 없습니다. 비활성화를 사용하세요.")
    db.delete(at)
    db.commit()
