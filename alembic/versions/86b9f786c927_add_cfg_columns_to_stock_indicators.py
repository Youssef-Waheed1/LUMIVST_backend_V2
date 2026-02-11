"""add_cfg_columns_to_stock_indicators

Revision ID: 86b9f786c927
Revises: e8905d5da169
Create Date: 2026-02-10 23:07:34.069451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86b9f786c927'
down_revision: Union[str, Sequence[str], None] = 'e8905d5da169'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    import sqlalchemy as sa
    from sqlalchemy.engine import reflection

    inspect_obj = reflection.Inspector.from_engine(conn)
    existing_columns = [c['name'] for c in inspect_obj.get_columns('stock_indicators')]

    # Add CFG Daily Indicators if not exist
    cfg_cols = [
        ('cfg_daily', sa.Numeric(5, 2)),
        ('cfg_sma9', sa.Numeric(5, 2)),
        ('cfg_sma20', sa.Numeric(5, 2)),
        ('cfg_ema20', sa.Numeric(5, 2)),
        ('cfg_ema45', sa.Numeric(5, 2)),
        ('cfg_gt_50_daily', sa.Boolean()),
        ('cfg_ema45_gt_50', sa.Boolean()),
        ('cfg_ema20_gt_50', sa.Boolean()),
        # CFG Weekly
        ('cfg_w', sa.Numeric(5, 2)),
        ('cfg_sma9_w', sa.Numeric(5, 2)),
        ('cfg_ema20_w', sa.Numeric(5, 2)),
        ('cfg_ema45_w', sa.Numeric(5, 2)),
        ('cfg_gt_50_w', sa.Boolean()),
        ('cfg_ema45_gt_50_w', sa.Boolean()),
        ('cfg_ema20_gt_50_w', sa.Boolean()),
        # Components
        ('rsi_3', sa.Numeric(5, 2)),
        ('rsi_3_w', sa.Numeric(5, 2)),
        ('sma3_rsi3', sa.Numeric(5, 2)),
        ('sma3_rsi3_w', sa.Numeric(5, 2)),
        ('rsi_14_minus_9', sa.Numeric(5, 2)),
        ('rsi_14_minus_9_w', sa.Numeric(5, 2)),
    ]

    for col_name, col_type in cfg_cols:
        if col_name not in existing_columns:
            op.add_column('stock_indicators', sa.Column(col_name, col_type, nullable=True))

    # Add Indexes if they don't exist
    existing_indexes = [idx['name'] for idx in inspect_obj.get_indexes('stock_indicators')]
    
    if 'idx_stock_indicators_cfg_ema45_gt_50' not in existing_indexes:
        op.create_index('idx_stock_indicators_cfg_ema45_gt_50', 'stock_indicators', ['cfg_ema45_gt_50'])
    if 'idx_stock_indicators_cfg_gt_50_daily' not in existing_indexes:
        op.create_index('idx_stock_indicators_cfg_gt_50_daily', 'stock_indicators', ['cfg_gt_50_daily'])


def downgrade() -> None:
    # We only drop what we added
    cols_to_drop = [
        'cfg_daily', 'cfg_sma9', 'cfg_sma20', 'cfg_ema20', 'cfg_ema45',
        'cfg_gt_50_daily', 'cfg_ema45_gt_50', 'cfg_ema20_gt_50',
        'cfg_w', 'cfg_sma9_w', 'cfg_ema20_w', 'cfg_ema45_w',
        'cfg_gt_50_w', 'cfg_ema45_gt_50_w', 'cfg_ema20_gt_50_w',
        'rsi_3', 'rsi_3_w', 'sma3_rsi3', 'sma3_rsi3_w', 
        'rsi_14_minus_9', 'rsi_14_minus_9_w'
    ]
    for col in cols_to_drop:
        op.drop_column('stock_indicators', col)
    
    op.drop_index('idx_stock_indicators_cfg_gt_50_daily')
    op.drop_index('idx_stock_indicators_cfg_ema45_gt_50')
