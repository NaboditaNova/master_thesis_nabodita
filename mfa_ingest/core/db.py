from __future__ import annotations
from typing import Optional, Union, Literal
from sqlalchemy.engine import Engine
from sqlalchemy import MetaData
from ..db_models.base import Base
from ..db.session import get_engine as _get_engine

EchoT = Union[bool, Literal["debug", "trace"]]


def make_engine(
    database_url_override: Optional[str] = None,
    echo: EchoT = False,
) -> Engine:
    """
    Thin wrapper that routes all engine creation through the TLS-aware session.get_engine.
    """
    return _get_engine(database_url_override=database_url_override, echo=echo)


def reflect_sanity_check(engine: Engine) -> None:
    """
    Simple live-vs-model table presence check.
    Raises if any model tables are missing in the live DB.
    """
    live = MetaData()
    live.reflect(bind=engine)
    missing = [t for t in Base.metadata.tables if t not in live.tables]
    if missing:
        raise RuntimeError(f"Live DB missing tables: {', '.join(missing)}")
