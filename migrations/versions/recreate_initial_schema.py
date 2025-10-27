"""Recreate initial schema with all columns"""

# revision identifiers, used by Alembic.
revision = 'recreate_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Create companies table with all columns
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('name_ar', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('previous_close', sa.Float(), nullable=True),
        sa.Column('change', sa.Float(), nullable=True),
        sa.Column('change_percent', sa.Float(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_price_update', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol'),
        sa.Index('ix_companies_symbol', 'symbol')
    )

    # Create financial_statements table
    op.create_table(
        'financial_statements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.String(length=32), nullable=False),
        sa.Column('period', sa.String(length=64), nullable=False),
        sa.Column('period_ending', sa.Date(), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('operating_income', sa.Float(), nullable=True),
        sa.Column('net_income', sa.Float(), nullable=True),
        sa.Column('gross_profit', sa.Float(), nullable=True),
        sa.Column('operating_expenses', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_financial_statements_company_id', 'company_id'),
        sa.Index('ix_financial_statements_period', 'period')
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('financial_statements')
    op.drop_table('companies')