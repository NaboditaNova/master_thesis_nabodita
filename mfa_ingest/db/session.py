from __future__ import annotations
from contextlib import contextmanager
from typing import Optional, Union, Literal, Any, Dict
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import sessionmaker, Session
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

import ssl as _ssl  # NEW
import certifi  # NEW

EchoT = Union[bool, Literal["debug", "trace"]]


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
    DB_DRIVER: str = Field(default="mariadb+pymysql")

    # ---- TLS/SSL controls ----  # NEW
    DB_SSL: bool = Field(default=False)  # enable TLS if True
    DB_SSL_VERIFY: bool = Field(default=True)  # verify server cert/hostname
    DB_SSL_CA: Optional[str] = None  # CA bundle path (optional; defaults to certifi)

    def build_url(self):
        # If a fully formed DATABASE_URL string is provided, use it as-is
        if self.DATABASE_URL:
            return self.DATABASE_URL

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

        return URL.create(
            self.DB_DRIVER,
            username=self.DB_USER or "",
            password=self.DB_PASSWORD or "",  # no manual quoting needed
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME or "",
            # If you need a charset: query={"charset": "utf8mb4"},
        )

    # def build_url(self) -> str:
    #     if self.DATABASE_URL:
    #         return self.DATABASE_URL

    #     missing = [
    #         k
    #         for k in ("DB_USER", "DB_PASSWORD", "DB_NAME")
    #         if getattr(self, k) in (None, "")
    #     ]
    #     if missing:
    #         raise ValueError(
    #             "DATABASE_URL not set and insufficient discrete DB_* vars. "
    #             f"Missing: {', '.join(missing)}. "
    #             "Either set DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME in .env"
    #         )

    #     user = self.DB_USER or ""
    #     pwd = self.DB_PASSWORD or ""
    #     host = self.DB_HOST
    #     port = self.DB_PORT
    #     name = self.DB_NAME or ""
    #     driver = self.DB_DRIVER

    #     return f"{driver}://{user}:{pwd}@{host}:{port}/{name}"


# NEW: build driver-specific TLS connect_args
def _make_connect_args(url: str, s: DBSettings) -> Dict[str, Any]:
    if not s.DB_SSL:
        return {}

    ca_path = s.DB_SSL_CA or certifi.where()
    scheme = url.split("://", 1)[
        0
    ]  # e.g. 'mariadb+pymysql' or 'mariadb+mariadbconnector'

    # PyMySQL
    if scheme.endswith("+pymysql"):
        # PyMySQL expects an 'ssl' dict
        if s.DB_SSL_VERIFY:
            return {"ssl": {"ca": ca_path}}
        else:
            # not recommended; keeps encryption without verification
            return {"ssl": {"cert_reqs": _ssl.CERT_NONE}}

    # MariaDB Connector/Python
    if scheme.endswith("+mariadbconnector") or scheme == "mariadb+mariadbconnector":
        # ssl_mode:
        #   - 'verify_ca' (verify cert using CA)
        #   - 'required' (TLS w/o verification)
        return {
            "ssl_mode": "verify_ca" if s.DB_SSL_VERIFY else "required",
            "ssl_ca": ca_path,
        }

    # Fallback: try PyMySQL style
    return (
        {"ssl": {"ca": ca_path}}
        if s.DB_SSL_VERIFY
        else {"ssl": {"cert_reqs": _ssl.CERT_NONE}}
    )


def get_engine(
    database_url_override: Optional[str] = None, echo: EchoT = False
) -> Engine:
    """
    Build a SQLAlchemy engine using:
      1) database_url_override (CLI), else
      2) .env DATABASE_URL, else
      3) composed from DB_* parts in .env
    """
    settings = DBSettings()
    url = database_url_override or settings.build_url()
    connect_args = _make_connect_args(url, settings)  # NEW
    engine = create_engine(
        url, pool_pre_ping=True, future=True, echo=echo, connect_args=connect_args
    )  # UPDATED
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
