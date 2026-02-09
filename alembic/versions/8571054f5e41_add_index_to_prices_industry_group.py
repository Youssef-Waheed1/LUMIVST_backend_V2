"""Add index to prices.industry_group

Revision ID: 8571054f5e41
Revises: 435c4faa7110
Create Date: 2026-02-08 13:54:52.251619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8571054f5e41'
down_revision: Union[str, Sequence[str], None] = '435c4faa7110'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_prices_industry_group', 'prices', ['industry_group'], unique=False)
    op.create_index('ix_prices_sector', 'prices', ['sector'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_prices_sector', table_name='prices')
    op.drop_index('ix_prices_industry_group', table_name='prices')
