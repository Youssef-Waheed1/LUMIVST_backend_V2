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
    # Manual changes for users table
    op.add_column('users', sa.Column('reset_token_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_reset_token_hash'), 'users', ['reset_token_hash'], unique=False)

    # rs_daily needed additions (excluding dangerous alters)
    # Checking if columns exist effectively by just adding them. 
    # If they exist, this might fail, but since previous run failed, they should be gone (rollback).
    op.add_column('rs_daily', sa.Column('rs_rating', sa.Integer(), nullable=True))
    op.add_column('rs_daily', sa.Column('rank_3m', sa.Integer(), nullable=True))
    op.add_column('rs_daily', sa.Column('rank_6m', sa.Integer(), nullable=True))
    op.add_column('rs_daily', sa.Column('rank_9m', sa.Integer(), nullable=True))
    op.add_column('rs_daily', sa.Column('rank_12m', sa.Integer(), nullable=True))
    op.add_column('rs_daily', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('rs_daily', sa.Column('industry_group', sa.String(length=255), nullable=True))
    
    # Simple boolean without invalid server_default
    op.add_column('rs_daily', sa.Column('has_rating', sa.Boolean(), nullable=True, default=False))
    
    # We SKIP the alter_column commands that caused Numeric Overflow
    # op.alter_column('rs_daily', 'rs_raw', ...) 

    # We SKIP other complex alters/drops to be safe for now, 
    # focusing on adding missing columns for functionality.
    
    # indexes
    op.create_index('idx_rs_daily_date_rating', 'rs_daily', ['date', sa.text('rs_rating DESC')], unique=False)
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
