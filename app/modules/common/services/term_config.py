"""용어 설정 서비스 (TermConfig) - CRUD + 시드 데이터"""
from sqlalchemy.orm import Session
from app.modules.common.models.term_config import TermConfig
from app.modules.common.schemas.term_config import TermConfigRead
from app.core.exceptions import NotFoundError, DuplicateError


def to_read(t: TermConfig) -> TermConfigRead:
    """ORM 모델 → 응답 스키마 변환."""
    return TermConfigRead(
        term_key=t.term_key,
        category=t.category,
        standard_label_en=t.standard_label_en,
        standard_label_ko=t.standard_label_ko,
        definition=t.definition,
        default_ui_label=t.default_ui_label,
        custom_ui_label=t.custom_ui_label,
        ui_label=t.ui_label,
        is_customized=t.is_customized,
        is_active=t.is_active,
        sort_order=t.sort_order,
    )

# 초기 시드 데이터 (테이블이 비어있을 때 자동 삽입)
_SEED = [
    {
        "term_key": "contract",
        "category": "entity",
        "standard_label_en": "Contract",
        "standard_label_ko": "계약",
        "definition": "고객과 체결된 서비스 또는 프로젝트 단위의 계약",
        "default_ui_label": "계약",
        "sort_order": 1,
    },
    {
        "term_key": "customer",
        "category": "entity",
        "standard_label_en": "Customer",
        "standard_label_ko": "고객",
        "definition": "서비스 또는 계약의 거래 상대방",
        "default_ui_label": "고객",
        "sort_order": 2,
    },
    {
        "term_key": "recognized_revenue",
        "category": "metric",
        "standard_label_en": "Recognized Revenue",
        "standard_label_ko": "인식매출",
        "definition": "계약 또는 서비스 수행 기준에 따라 해당 기간에 귀속되어 인식되는 매출 금액",
        "default_ui_label": "매출",
        "sort_order": 10,
    },
    {
        "term_key": "accounts_receivable",
        "category": "metric",
        "standard_label_en": "Accounts Receivable",
        "standard_label_ko": "미수채권",
        "definition": "인식된 매출 중 아직 수납되지 않은 금액",
        "default_ui_label": "미수",
        "sort_order": 11,
    },
    {
        "term_key": "receipt",
        "category": "entity",
        "standard_label_en": "Cash Receipt",
        "standard_label_ko": "현금수취",
        "definition": "고객으로부터 실제로 수취한 현금 또는 현금성 자금",
        "default_ui_label": "수납",
        "sort_order": 3,
    },
    {
        "term_key": "receipt_match",
        "category": "entity",
        "standard_label_en": "Receipt Allocation",
        "standard_label_ko": "수납배분",
        "definition": "수납 금액을 특정 매출 귀속 일정에 매핑하는 행위",
        "default_ui_label": "수납 배분",
        "sort_order": 4,
    },
    {
        "term_key": "period_year",
        "category": "entity",
        "standard_label_en": "Contract Period Year",
        "standard_label_ko": "계약 귀속 연도",
        "definition": "계약 주기 단위의 귀속 연도 (Y25, Y26 등)",
        "default_ui_label": "귀속연도",
        "sort_order": 5,
    },
]


def seed_defaults(db: Session) -> None:
    """테이블이 비어있으면 기본 용어를 삽입한다."""
    from sqlalchemy import inspect as sa_inspect

    tbl = TermConfig.__table__
    engine = db.get_bind()
    insp = sa_inspect(engine)
    tbl_name = TermConfig.__tablename__

    if insp.has_table(tbl_name):
        existing_cols = {c["name"] for c in insp.get_columns(tbl_name)}
        model_cols = {c.name for c in tbl.columns}

        if model_cols.issubset(existing_cols):
            cnt = db.query(TermConfig).count()
            if cnt > 0:
                # 기존 데이터가 있으면 누락된 시드 항목만 보충
                _upsert_missing_seeds(db)
                return
        else:
            # 스키마 불일치 → 기존 데이터 백업 후 테이블 재생성
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

    # 시드 데이터 삽입
    with engine.connect() as conn:
        conn.execute(tbl.insert(), _SEED)
        conn.commit()


def _upsert_missing_seeds(db: Session) -> None:
    """시드 데이터 중 DB에 없는 항목만 추가한다."""
    existing_keys = {t.term_key for t in db.query(TermConfig.term_key).all()}
    missing = [s for s in _SEED if s["term_key"] not in existing_keys]
    if missing:
        for item in missing:
            db.add(TermConfig(**item))
        db.commit()


def list_terms(db: Session, *, active_only: bool = True, category: str | None = None) -> list[TermConfigRead]:
    """용어 목록 조회."""
    q = db.query(TermConfig).order_by(TermConfig.category, TermConfig.sort_order, TermConfig.term_key)
    if active_only:
        q = q.filter(TermConfig.is_active.is_(True))
    if category:
        q = q.filter(TermConfig.category == category)
    return [to_read(t) for t in q.all()]


def get_term(db: Session, term_key: str) -> TermConfigRead:
    """단일 용어 조회."""
    term = db.get(TermConfig, term_key)
    if not term:
        raise NotFoundError(f"용어 '{term_key}'을(를) 찾을 수 없습니다.")
    return to_read(term)


def get_ui_label(db: Session, term_key: str) -> str:
    """UI 표시 라벨 반환. 커스텀 > 기본값 우선."""
    term = db.get(TermConfig, term_key)
    if not term:
        return term_key  # fallback
    return term.ui_label


def list_ui_labels(db: Session) -> dict[str, str]:
    """모든 활성 용어의 {term_key: ui_label} 딕셔너리 반환."""
    terms = db.query(TermConfig).filter(TermConfig.is_active.is_(True)).all()
    return {t.term_key: t.ui_label for t in terms}


def create_term(db: Session, *, data: dict) -> TermConfigRead:
    """용어 추가."""
    existing = db.get(TermConfig, data["term_key"])
    if existing:
        raise DuplicateError(f"용어 '{data['term_key']}'이(가) 이미 존재합니다.")
    term = TermConfig(**data)
    db.add(term)
    db.commit()
    return to_read(term)


def update_term(db: Session, term_key: str, *, updates: dict) -> TermConfigRead:
    """용어 수정. custom_ui_label 설정 시 is_customized 자동 처리."""
    term = db.get(TermConfig, term_key)
    if not term:
        raise NotFoundError(f"용어 '{term_key}'을(를) 찾을 수 없습니다.")
    for k, v in updates.items():
        if hasattr(term, k):
            setattr(term, k, v)
    # custom_ui_label이 설정되면 is_customized 자동 true, 비우면 false
    if "custom_ui_label" in updates:
        term.is_customized = bool(updates["custom_ui_label"])
    db.commit()
    return to_read(term)


def reset_term(db: Session, term_key: str) -> TermConfigRead:
    """커스텀 라벨 초기화 → 기본값으로 복원."""
    term = db.get(TermConfig, term_key)
    if not term:
        raise NotFoundError(f"용어 '{term_key}'을(를) 찾을 수 없습니다.")
    term.custom_ui_label = None
    term.is_customized = False
    db.commit()
    return to_read(term)


def delete_term(db: Session, term_key: str) -> None:
    """용어 삭제."""
    term = db.get(TermConfig, term_key)
    if not term:
        raise NotFoundError(f"용어 '{term_key}'을(를) 찾을 수 없습니다.")
    db.delete(term)
    db.commit()
