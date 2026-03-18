from app.core.config import DATABASE_URL

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# psycopg (v3) 드라이버 사용을 위해 postgresql:// → postgresql+psycopg:// 변환
_db_url = DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
