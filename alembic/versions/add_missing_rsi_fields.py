"""Add missing RSI and EMA20 fields to stock_indicators

Revision ID: add_missing_rsi_fields
Revises: previous_revision
Create Date: 2026-02-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_missing_rsi_fields'
down_revision = None  # Set to the previous revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to stock_indicators table
    op.add_column('stock_indicators', sa.Column('rsi_14_9_days_ago', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('rsi_w_9_weeks_ago', sa.Numeric(5, 2), nullable=True))
    op.add_column('stock_indicators', sa.Column('ema20_sma3_rsi3_w', sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('stock_indicators', 'rsi_14_9_days_ago')
    op.drop_column('stock_indicators', 'rsi_w_9_weeks_ago')
    op.drop_column('stock_indicators', 'ema20_sma3_rsi3_w')
