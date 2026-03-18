import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.common.models import (  # noqa: F401
    AuditLog,
    Customer,
    CustomerContact,
    CustomerContactRole,
    LoginFailure,
    Setting,
    TermConfig,
    User,
    UserPreference,
)
from app.modules.accounting.models import (  # noqa: F401
    Contract,
    ContractContact,
    ContractPeriod,
    ContractTypeConfig,
    MonthlyForecast,
    Receipt,
    ReceiptMatch,
    TransactionLine,
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
