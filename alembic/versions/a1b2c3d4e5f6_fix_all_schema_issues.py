"""fix_all_schema_issues

Revision ID: a1b2c3d4e5f6
Revises: 914cd0e7fbb8
Create Date: 2026-01-06 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '914cd0e7fbb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 1. USERS TABLE FIXES
    if 'users' in tables:
        cols = [c['name'] for c in inspector.get_columns('users')]
        
        if 'is_verified' not in cols:
             op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false')))
             
        if 'is_admin' not in cols:
             op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false')))
             
        if 'reset_token_hash' not in cols:
             op.add_column('users', sa.Column('reset_token_hash', sa.String(), nullable=True))
             op.create_index(op.f('ix_users_reset_token_hash'), 'users', ['reset_token_hash'], unique=False)
             
        if 'reset_token_expires_at' not in cols:
             op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))
             
    # 2. RS_DAILY TABLE FIXES (Just in case)
    if 'rs_daily' in tables:
        cols = [c['name'] for c in inspector.get_columns('rs_daily')]
        if 'has_rating' not in cols:
            op.add_column('rs_daily', sa.Column('has_rating', sa.Boolean(), server_default=sa.text('false')))
            
def downgrade() -> None:
    pass
