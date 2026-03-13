from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (  # noqa: F401
    AuditLog,
    Contract,
    ContractContact,
    ContractPeriod,
    ContractTypeConfig,
    Customer,
    CustomerContact,
    CustomerContactRole,
    MonthlyForecast,
    Receipt,
    ReceiptMatch,
    Setting,
    TermConfig,
    TransactionLine,
    User,
    UserPreference,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
