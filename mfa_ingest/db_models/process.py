from __future__ import annotations
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects import mysql
from .base import Base


class Process(Base):
    __tablename__ = "process"

    process_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    process_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    process_type: Mapped[str] = mapped_column(
        Enum("Collection", "Sorting", "Recycling", name="process_type"),
        nullable=False,
    )

    collection_process_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "collection_process_kpi.process_kpi_id",
            name="fk_process__collection_kpi__ref_collection_process_kpi",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    sorting_process_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "sorting_process_kpi.process_kpi_id",
            name="fk_process__sorting_kpi__ref_sorting_process_kpi",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    recycling_process_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "recycling_process_kpi.process_kpi_id",
            name="fk_process__recycling_kpi__ref_recycling_process_kpi",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    collection_kpi = relationship("CollectionProcessKPI", back_populates="process")
    sorting_kpi = relationship("SortingProcessKPI", back_populates="process")
    recycling_kpi = relationship("RecyclingProcessKPI", back_populates="process")
    material_flows = relationship(
        "ProcessMaterialFlow", back_populates="process", cascade="all, delete-orphan"
    )
