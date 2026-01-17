"""Add scraper integration tables

Revision ID: 202601131300
Revises:
Create Date: 2026-01-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202601131300'
down_revision = 'e5093b7e096c'  # Points to add_approval_fields migration
branch_labels = None
depends_on = None


def upgrade():
    # Create period_type_enum safely
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'period_type_enum') THEN
                CREATE TYPE period_type_enum AS ENUM ('Annually', 'Quarterly');
            END IF;
        END$$;
    """)
    
    # Create report_type_enum safely
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_type_enum') THEN
                CREATE TYPE report_type_enum AS ENUM ('Balance_Sheet', 'Income_Statement', 'Cash_Flows');
            END IF;
        END$$;
    """)
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('name_en', sa.String(255), nullable=True),
        sa.Column('name_ar', sa.String(255), nullable=True),
        sa.Column('sector', sa.String(255), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_symbol'), 'companies', ['symbol'], unique=True)
    
    # Create financial_reports table
    op.create_table(
        'financial_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_symbol', sa.String(20), nullable=False),
        sa.Column('period_type', postgresql.ENUM('Annually', 'Quarterly', name='period_type_enum', create_type=False), nullable=False),
        sa.Column('report_type', postgresql.ENUM('Balance_Sheet', 'Income_Statement', 'Cash_Flows', name='report_type_enum', create_type=False), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_symbol', 'period_type', 'report_type', 'period_end_date', name='uq_financial_report')
    )
    op.create_index(op.f('ix_financial_reports_id'), 'financial_reports', ['id'], unique=False)
    op.create_index(op.f('ix_financial_reports_company_symbol'), 'financial_reports', ['company_symbol'], unique=False)
    
    # Create excel_reports table
    op.create_table(
        'excel_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_symbol', sa.String(20), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_excel_reports_id'), 'excel_reports', ['id'], unique=False)
    op.create_index(op.f('ix_excel_reports_company_symbol'), 'excel_reports', ['company_symbol'], unique=False)


def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_excel_reports_company_symbol'), table_name='excel_reports')
    op.drop_index(op.f('ix_excel_reports_id'), table_name='excel_reports')
    op.drop_table('excel_reports')
    
    op.drop_index(op.f('ix_financial_reports_company_symbol'), table_name='financial_reports')
    op.drop_index(op.f('ix_financial_reports_id'), table_name='financial_reports')
    op.drop_table('financial_reports')
    
    op.drop_index(op.f('ix_companies_symbol'), table_name='companies')
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS period_type_enum')
    op.execute('DROP TYPE IF EXISTS report_type_enum')
