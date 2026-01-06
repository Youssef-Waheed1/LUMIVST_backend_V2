"""repair_users_add_reset_token_hash

Revision ID: 914cd0e7fbb8
Revises: ae72c72101a8
Create Date: 2026-01-06 14:32:07.240998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '914cd0e7fbb8'
down_revision: Union[str, Sequence[str], None] = 'ae72c72101a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check users table columns
    columns_users = [c['name'] for c in inspector.get_columns('users')]
    
    if 'reset_token_hash' not in columns_users:
        op.add_column('users', sa.Column('reset_token_hash', sa.String(), nullable=True))
        op.create_index(op.f('ix_users_reset_token_hash'), 'users', ['reset_token_hash'], unique=False)
        
    if 'reset_token_expires_at' not in columns_users:
        op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    pass
