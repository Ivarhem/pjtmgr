import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.common.models import (  # noqa: F401
    AuditLog,
    Contract,
    ContractPeriod,
    ContractTypeConfig,
    Customer,
    CustomerContact,
    CustomerContactRole,
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
    AssetContact,
    AssetIP,
    AssetRelation,
    AssetSoftware,
    HardwareInterface,
    HardwareSpec,
    IpSubnet,
    PeriodAsset,
    PeriodCustomer,
    PeriodCustomerContact,
    PeriodDeliverable,
    PeriodPhase,
    PolicyAssignment,
    PolicyDefinition,
    PortMap,
    ProductCatalog,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://projmgr:projmgr@localhost:5432/projmgr_test",
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
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
def sample_customer(db_session: Session) -> Customer:
    """테스트용 고객사 생성."""
    customer = Customer(name="테스트고객사")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer
