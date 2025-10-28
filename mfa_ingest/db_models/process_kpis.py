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
        DECIMAL(9, 3), nullable=True
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
        DECIMAL(9, 3), nullable=True
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
        DECIMAL(9, 3), nullable=True
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
        DECIMAL(9, 3), nullable=True
    )
    attached_moisture_and_dirt_amount_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    npp_share_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    npp_share_amount_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    residual_waste_share_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    residual_waste_share_amount_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    eps_items_amount_value: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
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


class SortingFlowKPI(Base):
    __tablename__ = "sorting_flow_kpi"

    flow_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    maximum_total_amount_of_impurities_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    maximum_total_amount_of_impurities_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    purity_amount: Mapped[float | None] = mapped_column(DECIMAL(9, 3), nullable=True)
    purity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    other_metal_items_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    other_metal_items_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    other_plastics_items_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    other_plastics_items_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    ppk_amount: Mapped[float | None] = mapped_column(DECIMAL(9, 3), nullable=True)
    ppk_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    eps_items_amount: Mapped[float | None] = mapped_column(DECIMAL(9, 3), nullable=True)
    eps_items_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    pvc_items_amount: Mapped[float | None] = mapped_column(DECIMAL(9, 3), nullable=True)
    pvc_items_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    colourless_transparent_foils_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    colourless_transparent_foils_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    yield_of_ds_from_input_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    yield_of_ds_from_input_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    __table_args__ = (
        # At least one amount must be provided
        CheckConstraint(
            "maximum_total_amount_of_impurities_amount IS NOT NULL "
            "OR purity_amount IS NOT NULL "
            "OR other_metal_items_amount IS NOT NULL "
            "OR other_plastics_items_amount IS NOT NULL "
            "OR ppk_amount IS NOT NULL "
            "OR eps_items_amount IS NOT NULL "
            "OR pvc_items_amount IS NOT NULL "
            "OR colourless_transparent_foils_amount IS NOT NULL "
            "OR yield_of_ds_from_input_amount IS NOT NULL",
            name="chk_sort_flow_kpi_one_present",
        ),
        # Pairing rules (amount -> non-blank unit)
        CheckConstraint(
            "maximum_total_amount_of_impurities_amount IS NULL "
            "OR NULLIF(TRIM(maximum_total_amount_of_impurities_unit), '') IS NOT NULL",
            name="chk_pair_max_impur",
        ),
        CheckConstraint(
            "purity_amount IS NULL OR NULLIF(TRIM(purity_unit), '') IS NOT NULL",
            name="chk_pair_purity_spec",
        ),
        CheckConstraint(
            "other_metal_items_amount IS NULL OR NULLIF(TRIM(other_metal_items_unit), '') IS NOT NULL",
            name="chk_pair_other_metal",
        ),
        CheckConstraint(
            "other_plastics_items_amount IS NULL OR NULLIF(TRIM(other_plastics_items_unit), '') IS NOT NULL",
            name="chk_pair_other_plastics",
        ),
        CheckConstraint(
            "ppk_amount IS NULL OR NULLIF(TRIM(ppk_unit), '') IS NOT NULL",
            name="chk_pair_ppk",
        ),
        CheckConstraint(
            "eps_items_amount IS NULL OR NULLIF(TRIM(eps_items_unit), '') IS NOT NULL",
            name="chk_pair_eps",
        ),
        CheckConstraint(
            "pvc_items_amount IS NULL OR NULLIF(TRIM(pvc_items_unit), '') IS NOT NULL",
            name="chk_pair_pvc",
        ),
        CheckConstraint(
            "colourless_transparent_foils_amount IS NULL "
            "OR NULLIF(TRIM(colourless_transparent_foils_unit), '') IS NOT NULL",
            name="chk_pair_colourless_foils",
        ),
        CheckConstraint(
            "yield_of_ds_from_input_amount IS NULL "
            "OR NULLIF(TRIM(yield_of_ds_from_input_unit), '') IS NOT NULL",
            name="chk_pair_yield_ds",
        ),
        {"mysql_engine": "InnoDB"},
    )

    flow_samples = relationship("FlowSample", back_populates="sorting_flow_kpi")


class RecyclingFlowKPI(Base):
    __tablename__ = "recycling_flow_kpi"

    flow_kpi_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )

    filtration_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    filtration_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    recyclate_polymer_purity_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    recyclate_polymer_purity_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    pcr_content_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    pcr_content_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    melt_flow_rate_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    melt_flow_rate_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    ash_content_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    ash_content_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    tensile_modulus_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    tensile_modulus_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    tensile_strength_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    tensile_strength_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    chapry_notch_impact_strength_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    chapry_notch_impact_strength_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    yield_flow_sample_amount: Mapped[float | None] = mapped_column(
        DECIMAL(9, 3), nullable=True
    )
    yield_flow_sample_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    __table_args__ = (
        # at least one amount present
        CheckConstraint(
            "filtration_amount IS NOT NULL "
            "OR recyclate_polymer_purity_amount IS NOT NULL "
            "OR pcr_content_amount IS NOT NULL "
            "OR melt_flow_rate_amount IS NOT NULL "
            "OR ash_content_amount IS NOT NULL "
            "OR tensile_modulus_amount IS NOT NULL "
            "OR tensile_strength_amount IS NOT NULL "
            "OR chapry_notch_impact_strength_amount IS NOT NULL "
            "OR yield_flow_sample_amount IS NOT NULL",
            name="chk_recycling_flow_kpi_one_present",
        ),
        # pairing constraints (amount ↔ unit)
        CheckConstraint(
            "(filtration_amount IS NULL) "
            "OR (NULLIF(TRIM(filtration_unit), '') IS NOT NULL)",
            name="chk_pair_filtration",
        ),
        CheckConstraint(
            "(recyclate_polymer_purity_amount IS NULL) "
            "OR (NULLIF(TRIM(recyclate_polymer_purity_unit), '') IS NOT NULL)",
            name="chk_pair_purity",
        ),
        CheckConstraint(
            "(pcr_content_amount IS NULL) "
            "OR (NULLIF(TRIM(pcr_content_unit), '') IS NOT NULL)",
            name="chk_pair_pcr",
        ),
        CheckConstraint(
            "(melt_flow_rate_amount IS NULL) "
            "OR (NULLIF(TRIM(melt_flow_rate_unit), '') IS NOT NULL)",
            name="chk_pair_mfr",
        ),
        CheckConstraint(
            "(ash_content_amount IS NULL) "
            "OR (NULLIF(TRIM(ash_content_unit), '') IS NOT NULL)",
            name="chk_pair_ash",
        ),
        CheckConstraint(
            "(tensile_modulus_amount IS NULL) "
            "OR (NULLIF(TRIM(tensile_modulus_unit), '') IS NOT NULL)",
            name="chk_pair_tensile_modulus",
        ),
        CheckConstraint(
            "(tensile_strength_amount IS NULL) "
            "OR (NULLIF(TRIM(tensile_strength_unit), '') IS NOT NULL)",
            name="chk_pair_tensile_strength",
        ),
        CheckConstraint(
            "(chapry_notch_impact_strength_amount IS NULL) "
            "OR (NULLIF(TRIM(chapry_notch_impact_strength_unit), '') IS NOT NULL)",
            name="chk_pair_charpy",
        ),
        CheckConstraint(
            "(yield_flow_sample_amount IS NULL) "
            "OR (NULLIF(TRIM(yield_flow_sample_unit), '') IS NOT NULL)",
            name="chk_pair_yield_sample",
        ),
        {"mysql_engine": "InnoDB"},
    )

    # backref: many FlowSample rows may point to one RecyclingFlowKPI
    flow_samples = relationship("FlowSample", back_populates="recycling_flow_kpi")
