"""baseline schema

Revision ID: 001_nabodita
Revises:
Create Date: 2025-10-28 15:43:29.102635

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
from mfa_ingest.db_models.base import Base
from mfa_ingest.db_models import process, flows, process_kpis, material  # noqa: F401


revision: str = "001_nabodita"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)

    op.execute("DROP TRIGGER IF EXISTS bi_process_enforce")
    op.execute("DROP TRIGGER IF EXISTS bu_process_enforce")

    op.execute(
        """
    CREATE TRIGGER bi_process_enforce
    BEFORE INSERT ON process
    FOR EACH ROW
    BEGIN
      DECLARE n_nonnull INT DEFAULT
        (NEW.collection_process_kpi_id IS NOT NULL) +
        (NEW.sorting_process_kpi_id    IS NOT NULL) +
        (NEW.recycling_process_kpi_id  IS NOT NULL);

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

    op.execute(
        """
    CREATE TRIGGER bu_process_enforce
    BEFORE UPDATE ON process
    FOR EACH ROW
    BEGIN
      DECLARE n_nonnull INT DEFAULT
        (NEW.collection_process_kpi_id IS NOT NULL) +
        (NEW.sorting_process_kpi_id    IS NOT NULL) +
        (NEW.recycling_process_kpi_id  IS NOT NULL);

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


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS bi_process_enforce")
    op.execute("DROP TRIGGER IF EXISTS bu_process_enforce")

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
