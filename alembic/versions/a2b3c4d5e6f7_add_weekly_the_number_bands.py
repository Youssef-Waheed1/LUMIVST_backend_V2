"""add weekly the number bands

Revision ID: a2b3c4d5e6f7
Revises: 
Create Date: 2026-02-12 22:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weekly The Number bands columns
    op.add_column('stock_indicators', sa.Column('the_number_hl_w', sa.Numeric(10, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('the_number_ll_w', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('stock_indicators', 'the_number_ll_w')
    op.drop_column('stock_indicators', 'the_number_hl_w')
