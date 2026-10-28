import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = f"sqlite:///{os.path.join(DB_DIR, 'test.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_PATH)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

def get_db():
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from contextlib import contextmanager

@contextmanager
def get_db_context():
    """Context manager for standalone scripts and background tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates database tables if not already existing."""
    import models  # Ensure all models are registered
    Base.metadata.create_all(bind=engine)
