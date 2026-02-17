"""add weekly STAMP columns

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7g8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weekly STAMP components columns
    op.add_column('stock_indicators', sa.Column('rsi_14_9days_ago_w', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('stamp_a_value_w', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('stamp_s9rsi_w', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('stamp_e45cfg_w', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('stamp_e45rsi_w', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('stamp_e20sma3_w', sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('stock_indicators', 'stamp_e20sma3_w')
    op.drop_column('stock_indicators', 'stamp_e45rsi_w')
    op.drop_column('stock_indicators', 'stamp_e45cfg_w')
    op.drop_column('stock_indicators', 'stamp_s9rsi_w')
    op.drop_column('stock_indicators', 'stamp_a_value_w')
    op.drop_column('stock_indicators', 'rsi_14_9days_ago_w')
