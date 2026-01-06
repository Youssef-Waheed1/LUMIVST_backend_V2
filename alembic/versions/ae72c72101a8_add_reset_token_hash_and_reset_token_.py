"""Add reset_token_hash and reset_token_expires_at to users

Revision ID: ae72c72101a8
Revises: d478e0dda599
Create Date: 2026-01-06 14:10:47.744677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ae72c72101a8'
down_revision: Union[str, Sequence[str], None] = 'd478e0dda599'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Update USERS table safely
    columns_users = [c['name'] for c in inspector.get_columns('users')]
    
    if 'reset_token_hash' not in columns_users:
        op.add_column('users', sa.Column('reset_token_hash', sa.String(), nullable=True))
        op.create_index(op.f('ix_users_reset_token_hash'), 'users', ['reset_token_hash'], unique=False)
        
    if 'reset_token_expires_at' not in columns_users:
        op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))

    # 2. Update RS_DAILY table safely
    columns_rs = [c['name'] for c in inspector.get_columns('rs_daily')]
    
    new_cols = [
        ('rs_rating', sa.Integer()),
        ('rank_3m', sa.Integer()),
        ('rank_6m', sa.Integer()),
        ('rank_9m', sa.Integer()),
        ('rank_12m', sa.Integer()),
        ('company_name', sa.String(length=255)),
        ('industry_group', sa.String(length=255)),
        ('has_rating', sa.Boolean())
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns_rs:
            # For has_rating, we want a default
            if col_name == 'has_rating':
                op.add_column('rs_daily', sa.Column(col_name, col_type, nullable=True, server_default=sa.text('false')))
            else:
                op.add_column('rs_daily', sa.Column(col_name, col_type, nullable=True))
    
    # Indexes (Check by name exception handling is messier, but creating IF NOT EXISTS is standard PG, 
    # but Alembic op.create_index doesn't support IF NOT EXISTS easily without raw SQL.
    # We'll wrap in try/except block equivalent or check indexes.)
    indexes_rs = [i['name'] for i in inspector.get_indexes('rs_daily')]
    
    if 'idx_rs_daily_date_rating' not in indexes_rs:
        op.create_index('idx_rs_daily_date_rating', 'rs_daily', ['date', sa.text('rs_rating DESC')], unique=False)
        
    if 'idx_rs_daily_symbol_date' not in indexes_rs:
        # Note: existing idx_rs_symbol_date might conflict if we are replacing it.
        # But for now let's just add the one we want if missing.
        op.create_index('idx_rs_daily_symbol_date', 'rs_daily', ['symbol', 'date'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert users changes
    op.drop_index(op.f('ix_users_reset_token_hash'), table_name='users')
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token_hash')
    
    # Revert rs_daily changes
    op.drop_index('idx_rs_daily_symbol_date', table_name='rs_daily')
    op.drop_index('idx_rs_daily_date_rating', table_name='rs_daily')
    
    op.drop_column('rs_daily', 'has_rating')
    op.drop_column('rs_daily', 'industry_group')
    op.drop_column('rs_daily', 'company_name')
    op.drop_column('rs_daily', 'rank_12m')
    op.drop_column('rs_daily', 'rank_9m')
    op.drop_column('rs_daily', 'rank_6m')
    op.drop_column('rs_daily', 'rank_3m')
    op.drop_column('rs_daily', 'rs_rating')
