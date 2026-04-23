import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def _init_db() -> None:
    global _engine, _SessionLocal
    if _engine is None:
        url = os.getenv("DATABASE_URL", "")
        if not url:
            raise ValueError("DATABASE_URL is not set")
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        _engine = create_engine(url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db():
    _init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
