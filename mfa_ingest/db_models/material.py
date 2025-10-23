from __future__ import annotations
from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects import mysql

from .base import Base


class Material(Base):
    __tablename__ = "material"

    material_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    chemical_formula: Mapped[str | None] = mapped_column(String(100), nullable=True)
    polymer_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    common_applications: Mapped[str | None] = mapped_column(Text, nullable=True)
    carbon_content: Mapped[str | None] = mapped_column(String(50), nullable=True)
    standard_density_kg_m3: Mapped[str | None] = mapped_column(Text, nullable=True)
    density_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    cas_number: Mapped[str | None] = mapped_column(String(12), nullable=True)
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    standardized_sorting_number: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    sorting_guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    din_spec_91446_comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(description IS NOT NULL AND CHAR_LENGTH(TRIM(description)) > 0) "
            "OR (chemical_formula IS NOT NULL AND CHAR_LENGTH(TRIM(chemical_formula)) > 0) "
            "OR (polymer_type IS NOT NULL AND CHAR_LENGTH(TRIM(polymer_type)) > 0) "
            "OR (common_applications IS NOT NULL AND CHAR_LENGTH(TRIM(common_applications)) > 0) "
            "OR (carbon_content IS NOT NULL AND CHAR_LENGTH(TRIM(carbon_content)) > 0) "
            "OR (standard_density_kg_m3 IS NOT NULL AND CHAR_LENGTH(TRIM(standard_density_kg_m3)) > 0) "
            "OR (density_reference IS NOT NULL AND CHAR_LENGTH(TRIM(density_reference)) > 0) "
            "OR (cas_number IS NOT NULL AND CHAR_LENGTH(TRIM(cas_number)) > 0) "
            "OR (color IS NOT NULL AND CHAR_LENGTH(TRIM(color)) > 0) "
            "OR (standardized_sorting_number IS NOT NULL) "
            "OR (sorting_guidelines IS NOT NULL AND CHAR_LENGTH(TRIM(sorting_guidelines)) > 0) "
            "OR (din_spec_91446_comments IS NOT NULL AND CHAR_LENGTH(TRIM(din_spec_91446_comments)) > 0)",
            name="chk_material_at_least_one_filled",
        ),
        {"mysql_engine": "InnoDB"},
    )
