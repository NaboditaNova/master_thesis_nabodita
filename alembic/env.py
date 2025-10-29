# mypy: ignore-errors
from __future__ import annotations
import os
from mfa_ingest.db_models.base import Base  # <- your Declarative metadata
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context  # type: ignore[attr-defined]

# NEW: load .env so DATABASE_URL is available
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url():
    # prefer env var; fallback to alembic.ini sqlalchemy.url
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("%("):  # still unresolved interpolation
        raise RuntimeError(
            "DATABASE_URL not set and sqlalchemy.url unresolved. Set env or alembic.ini."
        )
    return url


def run_migrations_offline():
    url = _get_url()
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        url=_get_url(),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
