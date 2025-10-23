from __future__ import annotations
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

# Use pydantic-settings to read .env and env vars without touching the global env
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class DBSettings(BaseSettings):
    """
    Reads from:
      - .env (at project root) and env vars
      - Either provide DATABASE_URL directly, or discrete fields below to compose it.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: Optional[str] = None

    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: Optional[str] = None
    DB_DRIVER: str = Field(default="mariadb+pymysql")  # keep overridable

    def build_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Compose URL if all required parts are present
        missing = [
            k
            for k in ("DB_USER", "DB_PASSWORD", "DB_NAME")
            if getattr(self, k) in (None, "")
        ]
        if missing:
            raise ValueError(
                "DATABASE_URL not set and insufficient discrete DB_* vars. "
                f"Missing: {', '.join(missing)}. "
                "Either set DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME in .env"
            )

        user = self.DB_USER or ""
        pwd = self.DB_PASSWORD or ""
        host = self.DB_HOST
        port = self.DB_PORT
        name = self.DB_NAME or ""
        driver = self.DB_DRIVER

        # If password contains special chars, users should prefer DATABASE_URL.
        return f"{driver}://{user}:{pwd}@{host}:{port}/{name}"


def get_engine(
    database_url_override: Optional[str] = None, echo: bool = False
) -> Engine:
    """
    Build a SQLAlchemy engine using:
      1) database_url_override (CLI), else
      2) .env DATABASE_URL, else
      3) composed from DB_* parts in .env
    """
    settings = DBSettings()
    url = database_url_override or settings.build_url()
    engine = create_engine(url, pool_pre_ping=True, future=True, echo=echo)
    return engine


@contextmanager
def get_session(engine: Engine):
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, future=True
    )
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
