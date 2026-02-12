"""Merge multiple heads

Revision ID: 436e1b914d38
Revises: a8190fe95ea6, add_missing_rsi_fields
Create Date: 2026-02-12 00:10:45.960747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '436e1b914d38'
down_revision: Union[str, Sequence[str], None] = ('a8190fe95ea6', 'add_missing_rsi_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
