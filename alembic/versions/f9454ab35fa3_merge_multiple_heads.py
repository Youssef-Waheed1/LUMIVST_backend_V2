"""Merge multiple heads

Revision ID: f9454ab35fa3
Revises: 607fb515736b, a2b3c4d5e6f7
Create Date: 2026-02-12 22:59:24.461107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9454ab35fa3'
down_revision: Union[str, Sequence[str], None] = ('607fb515736b', 'a2b3c4d5e6f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
