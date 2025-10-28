from __future__ import annotations
from sqlalchemy import CheckConstraint, DECIMAL, String, Text, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects import mysql

from .base import Base


class ProcessMaterialFlow(Base):
    __tablename__ = "process_material_flow"

    material_flow_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    process_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "process.process_id",
            name="fk_process_material_flow__process",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        Enum("Input", "Output", name="direction"), nullable=False
    )
    material_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_value: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "amount_value IS NULL OR (amount_unit IS NOT NULL AND TRIM(amount_unit) <> '')",
            name="chk_process_material_flow_amount_pair",
        ),
        {"mysql_engine": "InnoDB"},
    )

    process = relationship("Process", back_populates="material_flows")
    samples = relationship(
        "FlowSample", back_populates="material_flow", cascade="all, delete-orphan"
    )


class FlowSample(Base):
    __tablename__ = "flow_sample"

    sample_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    material_flow_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "process_material_flow.material_flow_id",
            name="fk_flow_sample__material_flow",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    collection_flow_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "collection_flow_kpi.flow_kpi_id",
            name="fk_flow_sample__collection_kpi",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    sorting_flow_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "sorting_flow_kpi.flow_kpi_id", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    recycling_flow_kpi_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "recycling_flow_kpi.flow_kpi_id", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        nullable=True,
    )

    stakeholder_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sample_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    contamination: Mapped[float | None] = mapped_column(DECIMAL(9, 3), nullable=True)
    contamination_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    moisture_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    density: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    density_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    carbon_content_pct: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    nitrogen_content_pct: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    hydrogen_content_pct: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    phosphorus_content_pct: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    oxygen_content_pct: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_value: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "contamination IS NULL OR (contamination_unit IS NOT NULL AND TRIM(contamination_unit) <> '')",
            name="chk_flow_contamination_pair",
        ),
        CheckConstraint(
            "density IS NULL OR (density_unit IS NOT NULL AND TRIM(density_unit) <> '')",
            name="chk_flow_density_pair",
        ),
        CheckConstraint(
            "amount_value IS NULL OR (amount_unit IS NOT NULL AND TRIM(amount_unit) <> '')",
            name="chk_flow_amount_pair",
        ),
        CheckConstraint(
            "amount_value IS NULL OR amount_value >= 0", name="chk_flow_amount_nonneg"
        ),
        CheckConstraint(
            "(carbon_content_pct IS NULL OR (carbon_content_pct BETWEEN 0 AND 100)) "
            "AND (nitrogen_content_pct IS NULL OR (nitrogen_content_pct BETWEEN 0 AND 100)) "
            "AND (hydrogen_content_pct IS NULL OR (hydrogen_content_pct BETWEEN 0 AND 100)) "
            "AND (phosphorus_content_pct IS NULL OR (phosphorus_content_pct BETWEEN 0 AND 100)) "
            "AND (oxygen_content_pct IS NULL OR (oxygen_content_pct BETWEEN 0 AND 100))",
            name="chk_flow_pct_ranges",
        ),
        CheckConstraint(
            "(stakeholder_name IS NOT NULL AND CHAR_LENGTH(TRIM(stakeholder_name)) > 0) "
            "OR (sample_date IS NOT NULL) "
            "OR (contamination IS NOT NULL) "
            "OR (contamination_unit IS NOT NULL AND CHAR_LENGTH(TRIM(contamination_unit)) > 0) "
            "OR (moisture_condition IS NOT NULL AND CHAR_LENGTH(TRIM(moisture_condition)) > 0) "
            "OR (density IS NOT NULL) "
            "OR (density_unit IS NOT NULL AND CHAR_LENGTH(TRIM(density_unit)) > 0) "
            "OR (carbon_content_pct IS NOT NULL) "
            "OR (nitrogen_content_pct IS NOT NULL) "
            "OR (hydrogen_content_pct IS NOT NULL) "
            "OR (phosphorus_content_pct IS NOT NULL) "
            "OR (oxygen_content_pct IS NOT NULL) "
            "OR (color IS NOT NULL AND CHAR_LENGTH(TRIM(color)) > 0) "
            "OR (amount_value IS NOT NULL) "
            "OR (amount_unit IS NOT NULL AND CHAR_LENGTH(TRIM(amount_unit)) > 0)",
            name="chk_flow_at_least_one_data",
        ),
        {"mysql_engine": "InnoDB"},
    )

    material_flow = relationship("ProcessMaterialFlow", back_populates="samples")
    collection_flow_kpi = relationship(
        "CollectionFlowKPI", back_populates="flow_samples"
    )
    sorting_flow_kpi = relationship("SortingFlowKPI", back_populates="flow_samples")
    recycling_flow_kpi = relationship("RecyclingFlowKPI", back_populates="flow_samples")
    components = relationship(
        "FlowSampleComponent", back_populates="sample", cascade="all, delete-orphan"
    )


class FlowSampleComponent(Base):
    __tablename__ = "flow_sample_component"

    sample_component_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    sample_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "flow_sample.sample_id",
            name="fk_fsc__sample",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    material_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "material.material_id",
            name="fk_fsc__material",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    polymer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_value: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "NULLIF(TRIM(amount_value), '') IS NULL "
            "OR NULLIF(TRIM(amount_unit),  '') IS NOT NULL",
            name="chk_fsc_amount_pair",
        ),
        CheckConstraint(
            "NULLIF(TRIM(polymer_name), '') IS NOT NULL "
            "OR NULLIF(TRIM(description), '') IS NOT NULL "
            "OR NULLIF(TRIM(amount_value), '') IS NOT NULL "
            "OR NULLIF(TRIM(amount_unit), '') IS NOT NULL",
            name="chk_fsc_at_least_one_data",
        ),
        {"mysql_engine": "InnoDB"},
    )

    sample = relationship("FlowSample", back_populates="components")
    material = relationship("Material")
