"""
Database setup for Architect.AI
Uses SQLite (outputs/app.db) via SQLAlchemy ORM
"""

from pathlib import Path
from typing import Generator
from contextlib import contextmanager

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, declarative_base, Session
except Exception as e:
    create_engine = None  # type: ignore
    sessionmaker = None  # type: ignore
    declarative_base = None  # type: ignore
    Session = None  # type: ignore

DB_PATH = Path("outputs/app.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

if create_engine is not None:
    engine = create_engine(
        f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    engine = None  # type: ignore
    SessionLocal = None  # type: ignore
    Base = None  # type: ignore


@contextmanager
def get_session() -> Generator["Session", None, None]:  # type: ignore
    if SessionLocal is None:
        raise RuntimeError("SQLAlchemy not installed. Please `pip install sqlalchemy`." )
    session = SessionLocal()  # type: ignore
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all tables"""
    if Base is None:
        return
    from .models import User, Workspace, Job, PrototypeVariant, SecretToken  # noqa: F401
    Base.metadata.create_all(bind=engine)  # type: ignore
