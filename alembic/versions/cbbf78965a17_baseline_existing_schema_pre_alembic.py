"""baseline existing schema (pre-alembic)

Revision ID: cbbf78965a17
Revises:
Create Date: 2025-10-22 00:47:21.583817

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "cbbf78965a17"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
