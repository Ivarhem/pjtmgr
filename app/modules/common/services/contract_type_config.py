from sqlalchemy.orm import Session
from app.modules.common.models.contract_type_config import ContractTypeConfig
from app.modules.common.schemas.contract_type_config import ContractTypeRead
from app.core.exceptions import NotFoundError, DuplicateError


def to_read(dt: ContractTypeConfig) -> ContractTypeRead:
    """ORM 모델 → 응답 스키마 변환."""
    return ContractTypeRead(
        code=dt.code, label=dt.label, sort_order=dt.sort_order, is_active=dt.is_active,
        default_gp_pct=dt.default_gp_pct,
        default_inspection_day=dt.default_inspection_day,
        default_invoice_month_offset=dt.default_invoice_month_offset,
        default_invoice_day_type=dt.default_invoice_day_type,
        default_invoice_day=dt.default_invoice_day,
        default_invoice_holiday_adjust=dt.default_invoice_holiday_adjust,
    )

# 초기 시드 데이터 (테이블이 비어있을 때 자동 삽입)
_SEED = [
    {"code": "MA", "label": "MA", "sort_order": 1},
    {"code": "SI", "label": "SI", "sort_order": 2},
    {"code": "HW", "label": "HW", "sort_order": 3},
    {"code": "TS", "label": "TS", "sort_order": 4},
    {"code": "Prod", "label": "Prod", "sort_order": 5},
    {"code": "ETC", "label": "ETC", "sort_order": 6},
]


def seed_defaults(db: Session) -> None:
    """테이블이 비어있으면 기본 사업유형을 삽입한다.
    스키마 변경이 감지되면 테이블을 재생성한다(Alembic 미사용 환경)."""
    from sqlalchemy import inspect as sa_inspect

    tbl = ContractTypeConfig.__table__
    engine = db.get_bind()
    insp = sa_inspect(engine)
    tbl_name = ContractTypeConfig.__tablename__

    if insp.has_table(tbl_name):
        existing_cols = {c["name"] for c in insp.get_columns(tbl_name)}
        model_cols = {c.name for c in tbl.columns}

        if model_cols.issubset(existing_cols):
            # 스키마 일치 → 데이터 존재 확인만
            cnt = db.query(ContractTypeConfig).count()
            if cnt > 0:
                return
        else:
            # 스키마 불일치 → 기존 데이터 백업 후 테이블 재생성
            common_cols = sorted(existing_cols & model_cols)
            # ORM select로 공통 컬럼만 조회
            col_attrs = [tbl.c[c] for c in common_cols]
            with engine.connect() as conn:
                rows = conn.execute(tbl.select().with_only_columns(*col_attrs)).fetchall()
                backup = [dict(zip(common_cols, r)) for r in rows]
            db.close()  # ORM 세션 해제 (DDL 충돌 방지)
            tbl.drop(engine)
            tbl.create(engine)
            if backup:
                with engine.connect() as conn:
                    conn.execute(tbl.insert(), backup)
                    conn.commit()
            return
    else:
        # 테이블 자체가 없음 → 생성
        tbl.create(engine)

    # 시드 데이터 삽입
    with engine.connect() as conn:
        conn.execute(tbl.insert(), _SEED)
        conn.commit()


def list_contract_types(db: Session, *, active_only: bool = True) -> list[ContractTypeRead]:
    """사업유형 목록 조회. active_only=True이면 활성 항목만."""
    q = db.query(ContractTypeConfig).order_by(ContractTypeConfig.sort_order, ContractTypeConfig.code)
    if active_only:
        q = q.filter(ContractTypeConfig.is_active.is_(True))
    return [to_read(dt) for dt in q.all()]


def get_valid_codes(db: Session) -> set[str]:
    """활성 사업유형 코드 set 반환 (검증용)."""
    rows = db.query(ContractTypeConfig.code).filter(ContractTypeConfig.is_active.is_(True)).all()
    return {r[0] for r in rows}


def create_contract_type(
    db: Session, code: str, label: str, sort_order: int = 0, *, defaults: dict | None = None
) -> ContractTypeRead:
    existing = db.get(ContractTypeConfig, code)
    if existing:
        raise DuplicateError(f"사업유형 '{code}'이(가) 이미 존재합니다.")
    dt = ContractTypeConfig(code=code, label=label, sort_order=sort_order, is_active=True)
    if defaults:
        for k, v in defaults.items():
            if v is not None and hasattr(dt, k):
                setattr(dt, k, v)
    db.add(dt)
    db.commit()
    return to_read(dt)


def update_contract_type(db: Session, code: str, *, updates: dict) -> ContractTypeRead:
    dt = db.get(ContractTypeConfig, code)
    if not dt:
        raise NotFoundError(f"사업유형 '{code}'을(를) 찾을 수 없습니다.")
    for k, v in updates.items():
        if hasattr(dt, k):
            setattr(dt, k, v)
    db.commit()
    return to_read(dt)


def delete_contract_type(db: Session, code: str) -> None:
    """사업유형 삭제 (사용 중인 경우 비활성화 권장)."""
    dt = db.get(ContractTypeConfig, code)
    if not dt:
        raise NotFoundError(f"사업유형 '{code}'을(를) 찾을 수 없습니다.")
    db.delete(dt)
    db.commit()
