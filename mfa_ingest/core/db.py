from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from .settings import settings
from ..db_models.base import Base


def make_engine():
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


Session = sessionmaker(future=True)


def reflect_sanity_check(engine):
    live = MetaData()
    live.reflect(bind=engine)
    missing = [t for t in Base.metadata.tables if t not in live.tables]
    if missing:
        raise RuntimeError(f"Live DB missing tables: {missing}")
