import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Ensure current APIDoc directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import Base, DATABASE_URL
import models  # Register all models on Base.metadata

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    return DATABASE_URL

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    if url.startswith("sqlite"):
        connectable = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=pool.NullPool,
        )
    else:
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
