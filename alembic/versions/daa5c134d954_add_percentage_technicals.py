"""Add percentage technicals

Revision ID: daa5c134d954
Revises: 8ba798504be3
Create Date: 2026-01-21 21:10:52.059489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'daa5c134d954'
down_revision: Union[str, Sequence[str], None] = '8ba798504be3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prices', sa.Column('price_vs_sma_10_percent', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('price_vs_sma_21_percent', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('price_vs_sma_50_percent', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('price_vs_sma_150_percent', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('price_vs_sma_200_percent', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('percent_off_52w_high', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('percent_off_52w_low', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('prices', sa.Column('vol_diff_50_percent', sa.Numeric(precision=8, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('prices', 'vol_diff_50_percent')
    op.drop_column('prices', 'percent_off_52w_low')
    op.drop_column('prices', 'percent_off_52w_high')
    op.drop_column('prices', 'price_vs_sma_200_percent')
    op.drop_column('prices', 'price_vs_sma_150_percent')
    op.drop_column('prices', 'price_vs_sma_50_percent')
    op.drop_column('prices', 'price_vs_sma_21_percent')
    op.drop_column('prices', 'price_vs_sma_10_percent')
