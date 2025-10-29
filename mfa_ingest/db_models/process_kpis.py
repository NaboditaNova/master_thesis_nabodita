from __future__ import annotations
from sqlalchemy import CheckConstraint, DECIMAL, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects import mysql

from .base import Base


class CollectionProcessKPI(Base):
    __tablename__ = "collection_process_kpi"

    process_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    collection_rate_amount: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "collection_rate_amount IS NOT NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL "
            "OR NULLIF(TRIM(reference_text), '') IS NOT NULL",
            name="chk_collection_kpi_one_present",
        ),
        CheckConstraint(
            "collection_rate_amount IS NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL",
            name="chk_collection_kpi_amount_pair",
        ),
        {"mysql_engine": "InnoDB"},
    )

    process = relationship("Process", back_populates="collection_kpi", uselist=False)


class SortingProcessKPI(Base):
    __tablename__ = "sorting_process_kpi"

    process_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    sorting_yield_amount: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "sorting_yield_amount IS NOT NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL "
            "OR NULLIF(TRIM(reference_text), '') IS NOT NULL",
            name="chk_sorting_kpi_one_present",
        ),
        CheckConstraint(
            "sorting_yield_amount IS NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL",
            name="chk_sorting_kpi_amount_pair",
        ),
        {"mysql_engine": "InnoDB"},
    )

    process = relationship("Process", back_populates="sorting_kpi", uselist=False)


class RecyclingProcessKPI(Base):
    __tablename__ = "recycling_process_kpi"

    process_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    recycling_yield_amount: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "recycling_yield_amount IS NOT NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL "
            "OR NULLIF(TRIM(reference_text), '') IS NOT NULL",
            name="chk_recycling_kpi_one_present",
        ),
        CheckConstraint(
            "recycling_yield_amount IS NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL",
            name="chk_recycling_kpi_amount_pair",
        ),
        {"mysql_engine": "InnoDB"},
    )

    process = relationship("Process", back_populates="recycling_kpi", uselist=False)


class CollectionFlowKPI(Base):
    __tablename__ = "collection_flow_kpi"

    flow_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    purity_amount: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    purity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attached_moisture_and_dirt_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    attached_moisture_and_dirt_amount_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    npp_share_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    npp_share_amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    residual_waste_share_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    residual_waste_share_amount_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    eps_items_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(6, 3), nullable=True
    )
    eps_items_amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        # at least one KPI present
        CheckConstraint(
            "purity_amount IS NOT NULL "
            "OR attached_moisture_and_dirt_amount_value IS NOT NULL "
            "OR npp_share_amount_value IS NOT NULL "
            "OR residual_waste_share_amount_value IS NOT NULL "
            "OR eps_items_amount_value IS NOT NULL",
            name="chk_kpi_at_least_one_value",
        ),
        # pairing constraints
        CheckConstraint(
            "(purity_amount IS NULL AND purity_unit IS NULL) "
            "OR (purity_amount IS NOT NULL AND purity_unit IS NOT NULL AND CHAR_LENGTH(TRIM(purity_unit))>0)",
            name="chk_pair_purity",
        ),
        CheckConstraint(
            "(attached_moisture_and_dirt_amount_value IS NULL AND attached_moisture_and_dirt_amount_unit IS NULL) "
            "OR (attached_moisture_and_dirt_amount_value IS NOT NULL AND attached_moisture_and_dirt_amount_unit IS NOT NULL "
            "AND CHAR_LENGTH(TRIM(attached_moisture_and_dirt_amount_unit))>0)",
            name="chk_pair_attached",
        ),
        CheckConstraint(
            "(npp_share_amount_value IS NULL AND npp_share_amount_unit IS NULL) "
            "OR (npp_share_amount_value IS NOT NULL AND npp_share_amount_unit IS NOT NULL "
            "AND CHAR_LENGTH(TRIM(npp_share_amount_unit))>0)",
            name="chk_pair_npp",
        ),
        CheckConstraint(
            "(residual_waste_share_amount_value IS NULL AND residual_waste_share_amount_unit IS NULL) "
            "OR (residual_waste_share_amount_value IS NOT NULL AND residual_waste_share_amount_unit IS NOT NULL "
            "AND CHAR_LENGTH(TRIM(residual_waste_share_amount_unit))>0)",
            name="chk_pair_residual",
        ),
        CheckConstraint(
            "(eps_items_amount_value IS NULL AND eps_items_amount_unit IS NULL) "
            "OR (eps_items_amount_value IS NOT NULL AND eps_items_amount_unit IS NOT NULL "
            "AND CHAR_LENGTH(TRIM(eps_items_amount_unit))>0)",
            name="chk_pair_eps",
        ),
        {"mysql_engine": "InnoDB"},
    )

    flow_samples = relationship("FlowSample", back_populates="collection_flow_kpi")
