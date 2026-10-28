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

Base = declarative_base()