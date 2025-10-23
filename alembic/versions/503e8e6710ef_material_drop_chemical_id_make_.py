"""material: drop chemical_id; make standardized_sorting_number varchar

Revision ID: 503e8e6710ef
Revises: f41369d44069
Create Date: 2025-10-23 00:51:01.801900

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "503e8e6710ef"
down_revision: Union[str, Sequence[str], None] = "f41369d44069"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_check_material(conn):
    # MariaDB accepts either DROP CONSTRAINT or DROP CHECK depending on version
    try:
        op.execute(
            "ALTER TABLE material DROP CONSTRAINT chk_material_at_least_one_filled"
        )
    except Exception:
        op.execute("ALTER TABLE material DROP CHECK chk_material_at_least_one_filled")


def _add_check_material_without_chemical_id(conn):
    op.execute(
        """
        ALTER TABLE material
        ADD CONSTRAINT chk_material_at_least_one_filled
        CHECK (
             (description                 IS NOT NULL AND CHAR_LENGTH(TRIM(description)) > 0)
          OR (chemical_formula            IS NOT NULL AND CHAR_LENGTH(TRIM(chemical_formula)) > 0)
          OR (polymer_type                IS NOT NULL AND CHAR_LENGTH(TRIM(polymer_type)) > 0)
          OR (common_applications         IS NOT NULL AND CHAR_LENGTH(TRIM(common_applications)) > 0)
          OR (carbon_content              IS NOT NULL AND CHAR_LENGTH(TRIM(carbon_content)) > 0)
          OR (standard_density_kg_m3      IS NOT NULL AND CHAR_LENGTH(TRIM(standard_density_kg_m3)) > 0)
          OR (density_reference           IS NOT NULL AND CHAR_LENGTH(TRIM(density_reference)) > 0)
          OR (cas_number                  IS NOT NULL AND CHAR_LENGTH(TRIM(cas_number)) > 0)
          OR (color                       IS NOT NULL AND CHAR_LENGTH(TRIM(color)) > 0)
          OR (standardized_sorting_number IS NOT NULL)
          OR (sorting_guidelines          IS NOT NULL AND CHAR_LENGTH(TRIM(sorting_guidelines)) > 0)
          OR (din_spec_91446_comments     IS NOT NULL AND CHAR_LENGTH(TRIM(din_spec_91446_comments)) > 0)
        )
        """
    )


def _add_check_material_with_chemical_id(conn):
    # Only used on downgrade, adds chemical_id back into the OR list
    op.execute(
        """
        ALTER TABLE material
        ADD CONSTRAINT chk_material_at_least_one_filled
        CHECK (
             (description                 IS NOT NULL AND CHAR_LENGTH(TRIM(description)) > 0)
          OR (chemical_id                 IS NOT NULL AND CHAR_LENGTH(TRIM(chemical_id)) > 0)
          OR (chemical_formula            IS NOT NULL AND CHAR_LENGTH(TRIM(chemical_formula)) > 0)
          OR (polymer_type                IS NOT NULL AND CHAR_LENGTH(TRIM(polymer_type)) > 0)
          OR (common_applications         IS NOT NULL AND CHAR_LENGTH(TRIM(common_applications)) > 0)
          OR (carbon_content              IS NOT NULL AND CHAR_LENGTH(TRIM(carbon_content)) > 0)
          OR (standard_density_kg_m3      IS NOT NULL AND CHAR_LENGTH(TRIM(standard_density_kg_m3)) > 0)
          OR (density_reference           IS NOT NULL AND CHAR_LENGTH(TRIM(density_reference)) > 0)
          OR (cas_number                  IS NOT NULL AND CHAR_LENGTH(TRIM(cas_number)) > 0)
          OR (color                       IS NOT NULL AND CHAR_LENGTH(TRIM(color)) > 0)
          OR (standardized_sorting_number IS NOT NULL)
          OR (sorting_guidelines          IS NOT NULL AND CHAR_LENGTH(TRIM(sorting_guidelines)) > 0)
          OR (din_spec_91446_comments     IS NOT NULL AND CHAR_LENGTH(TRIM(din_spec_91446_comments)) > 0)
        )
        """
    )


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Drop the CHECK that still references chemical_id
    _drop_check_material(conn)

    # 2) Drop column chemical_id
    with op.batch_alter_table("material") as batch:
        batch.drop_column("chemical_id")

    # 3) INT -> VARCHAR(32) for standardized_sorting_number
    with op.batch_alter_table("material") as batch:
        batch.alter_column(
            "standardized_sorting_number",
            existing_type=sa.Integer(),
            type_=sa.String(length=32),
            existing_nullable=True,
            nullable=True,
        )

    # 4) Recreate the CHECK without chemical_id
    _add_check_material_without_chemical_id(conn)


def downgrade() -> None:
    conn = op.get_bind()

    # 1) Drop the current CHECK (without chemical_id)
    _drop_check_material(conn)

    # 2) Revert type: VARCHAR(32) -> INT
    with op.batch_alter_table("material") as batch:
        batch.alter_column(
            "standardized_sorting_number",
            existing_type=sa.String(length=32),
            type_=sa.Integer(),
            existing_nullable=True,
            nullable=True,
        )

    # 3) Re-add column chemical_id
    with op.batch_alter_table("material") as batch:
        batch.add_column(sa.Column("chemical_id", sa.String(length=100), nullable=True))

    # 4) Recreate the original CHECK with chemical_id
    _add_check_material_with_chemical_id(conn)
