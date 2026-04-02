import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.common.models import (  # noqa: F401
    AuditLog,
    Contract,
    ContractPeriod,
    ContractTypeConfig,
    Partner,
    PartnerContact,
    PartnerContactRole,
    LoginFailure,
    Role,
    Setting,
    TermConfig,
    User,
    UserPreference,
)
from app.modules.accounting.models import (  # noqa: F401
    ContractSalesDetail,
    ContractContact,
    MonthlyForecast,
    Receipt,
    ReceiptMatch,
    TransactionLine,
)
from app.modules.infra.models import (  # noqa: F401
    Asset,
    AssetEvent,
    AssetRelatedPartner,
    AssetRole,
    AssetRoleAssignment,
    AssetContact,
    AssetIP,
    AssetRelation,
    AssetSoftware,
    HardwareInterface,
    HardwareSpec,
    IpSubnet,
    PeriodAsset,
    PeriodPartner,
    PeriodPartnerContact,
    PeriodDeliverable,
    PeriodPhase,
    PolicyAssignment,
    PolicyDefinition,
    PortMap,
    ProductCatalog,
)
from app.modules.common.services.contract_type_config import seed_defaults as seed_contract_type_defaults

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://projmgr:projmgr@localhost:5432/projmgr_test",
)


def _normalize_test_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return db_url


def _ensure_test_database_exists(db_url: str) -> None:
    url = make_url(db_url)
    database_name = url.database
    if not database_name or not url.drivername.startswith("postgresql"):
        return

    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()
            if not exists:
                try:
                    conn.execute(text(f'CREATE DATABASE "{database_name}"'))
                except IntegrityError:
                    pass
    finally:
        admin_engine.dispose()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    test_db_url = _normalize_test_db_url(TEST_DATABASE_URL)
    _ensure_test_database_exists(test_db_url)

    engine = create_engine(test_db_url, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        seed_contract_type_defaults(session)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_system_roles(db: Session) -> dict[str, int]:
    """테스트용 시스템 역할 시딩. 역할명 -> role_id 매핑 반환."""
    from app.modules.common.models.role import Role

    roles_data = [
        {
            "name": "관리자",
            "is_system": True,
            "permissions": {"admin": True, "modules": {"accounting": "full", "infra": "full"}},
        },
        {
            "name": "영업담당자",
            "is_system": True,
            "permissions": {"admin": False, "modules": {"accounting": "full"}},
        },
    ]
    result = {}
    for rd in roles_data:
        existing = db.query(Role).filter(Role.name == rd["name"]).first()
        if not existing:
            role = Role(**rd)
            db.add(role)
            db.flush()
            result[rd["name"]] = role.id
        else:
            result[rd["name"]] = existing.id
    db.commit()
    return result


@pytest.fixture
def seed_roles(db_session: Session) -> dict[str, int]:
    """시스템 역할을 시딩하고 역할명 -> ID 매핑을 반환하는 fixture."""
    return _seed_system_roles(db_session)


@pytest.fixture
def user_role_id(seed_roles: dict[str, int]) -> int:
    """일반 사용자(영업담당자) role_id."""
    return seed_roles["영업담당자"]


@pytest.fixture
def admin_role_id(seed_roles: dict[str, int]) -> int:
    """관리자 role_id."""
    return seed_roles["관리자"]


@pytest.fixture
def sample_partner(db_session: Session) -> Partner:
    """테스트용 거래처 생성."""
    partner = Partner(name="테스트고객사")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)
    return partner
