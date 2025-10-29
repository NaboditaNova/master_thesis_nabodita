# mypy: ignore-errors
from __future__ import annotations
import os
from mfa_ingest.db_models.base import Base
from logging.config import fileConfig
from alembic import context  # type: ignore[attr-defined]
from dotenv import load_dotenv, find_dotenv
from mfa_ingest.db.session import get_engine, DBSettings

load_dotenv(find_dotenv())


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url():
    """
    Prefer DATABASE_URL; else compose from DB_* via DBSettings; else fallback to alembic.ini.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    try:
        return DBSettings().build_url()
    except Exception:
        pass

    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("%("):
        raise RuntimeError(
            "DATABASE_URL not set and sqlalchemy.url unresolved. "
            "Set env vars (.env) or alembic.ini."
        )

    return url


def run_migrations_offline():
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    url = _get_url()
    engine = get_engine(database_url_override=url, echo=False)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            version_table="alembic_version",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
