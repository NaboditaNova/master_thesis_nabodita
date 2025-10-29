"""baseline: create process triggers

Revision ID: f41369d44069
Revises: cbbf78965a17
Create Date: 2025-10-22 01:05:42.263981

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]


# revision identifiers, used by Alembic.
revision: str = "f41369d44069"
down_revision: Union[str, Sequence[str], None] = "cbbf78965a17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop first (safe if they already exist on this DB)
    op.execute("DROP TRIGGER IF EXISTS bu_process_enforce")
    op.execute("DROP TRIGGER IF EXISTS bi_process_enforce")

    # BEFORE INSERT trigger
    op.execute(
        """
        CREATE TRIGGER bi_process_enforce
        BEFORE INSERT ON process
        FOR EACH ROW
        BEGIN
        DECLARE n_nonnull INT DEFAULT
            (NEW.collection_process_kpi_id IS NOT NULL)
            + (NEW.sorting_process_kpi_id    IS NOT NULL)
            + (NEW.recycling_process_kpi_id  IS NOT NULL);

        -- At most one KPI FK may be non-NULL (0 or 1 allowed)
        IF n_nonnull > 1 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'At most one of {collection, sorting, recycling}_process_kpi_id may be non-NULL';
        END IF;

        -- If a KPI is set, it must match process_type
        IF (NEW.collection_process_kpi_id IS NOT NULL AND NEW.process_type <> 'Collection')
            OR (NEW.sorting_process_kpi_id  IS NOT NULL AND NEW.process_type <> 'Sorting')
            OR (NEW.recycling_process_kpi_id IS NOT NULL AND NEW.process_type <> 'Recycling') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'If a KPI id is set, process_type must match the non-NULL KPI id';
        END IF;
        END
        """
    )

    # BEFORE UPDATE trigger
    op.execute(
        """
        CREATE TRIGGER bu_process_enforce
        BEFORE UPDATE ON process
        FOR EACH ROW
        BEGIN
        DECLARE n_nonnull INT DEFAULT
            (NEW.collection_process_kpi_id IS NOT NULL)
            + (NEW.sorting_process_kpi_id    IS NOT NULL)
            + (NEW.recycling_process_kpi_id  IS NOT NULL);

        IF n_nonnull > 1 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'At most one of {collection, sorting, recycling}_process_kpi_id may be non-NULL';
        END IF;

        IF (NEW.collection_process_kpi_id IS NOT NULL AND NEW.process_type <> 'Collection')
            OR (NEW.sorting_process_kpi_id  IS NOT NULL AND NEW.process_type <> 'Sorting')
            OR (NEW.recycling_process_kpi_id IS NOT NULL AND NEW.process_type <> 'Recycling') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'If a KPI id is set, process_type must match the non-NULL KPI id';
        END IF;
        END
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS bu_process_enforce")
    op.execute("DROP TRIGGER IF EXISTS bi_process_enforce")
    pass
