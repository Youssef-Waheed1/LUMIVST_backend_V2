"""add_language_to_official_filings

Revision ID: g1a2b3c4d5e6
Revises: f9454ab35fa3
Create Date: 2026-02-17 15:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'g1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'f9454ab35fa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add language column to company_official_filings."""
    # Drop any broken enum from previous failed attempts
    op.execute("DROP TYPE IF EXISTS filing_language_enum CASCADE")
    
    # Create the enum type fresh
    filing_language_enum = ENUM('en', 'ar', name='filing_language_enum', create_type=False)
    filing_language_enum.create(op.get_bind(), checkfirst=False)
    
    # Add the column with default 'en' -- existing English records will be auto-tagged
    op.add_column('company_official_filings', 
        sa.Column('language', filing_language_enum, nullable=False, server_default='en')
    )


def downgrade() -> None:
    """Remove language column from company_official_filings."""
    op.drop_column('company_official_filings', 'language')
    
    # Drop the enum type
    ENUM(name='filing_language_enum').drop(op.get_bind(), checkfirst=True)
