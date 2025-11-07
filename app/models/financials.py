# backend/app/models/financial_models.py
from sqlalchemy import Column, Integer, String, Float, Date, JSON, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class IncomeStatement(Base):
    __tablename__ = "income_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    country = Column(String(50), index=True, nullable=False, default="Saudi Arabia")
    fiscal_date = Column(Date, nullable=True)
    quarter = Column(String(10), nullable=True)
    year = Column(Integer, nullable=True)
    
    # الحقول الأساسية
    revenue = Column(Float, nullable=True)
    sales = Column(Float, nullable=True)
    cost_of_goods = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    operating_expense = Column(JSONB, nullable=True)
    operating_income = Column(Float, nullable=True)
    non_operating_interest = Column(JSONB, nullable=True)
    other_income_expense = Column(Float, nullable=True)
    pretax_income = Column(Float, nullable=True)
    income_tax = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    
    # الحقول الجديدة المطلوبة بناءً على الـ logs
    net_income_continuous_operations = Column(Float, nullable=True)
    
    eps_basic = Column(Float, nullable=True)
    eps_diluted = Column(Float, nullable=True)
    basic_shares_outstanding = Column(Float, nullable=True)
    diluted_shares_outstanding = Column(Float, nullable=True)
    ebit = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    
    # حقل إضافي لاستيعاب أي بيانات أخرى
    additional_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<IncomeStatement(symbol='{self.symbol}', country='{self.country}', year='{self.year}')>"

class BalanceSheet(Base):
    __tablename__ = "balance_sheets"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    country = Column(String(50), index=True, nullable=False, default="Saudi Arabia")
    fiscal_date = Column(Date, nullable=True)
    
    # إضافة quarter لـ BalanceSheet
    quarter = Column(String(10), nullable=True)
    
    year = Column(Integer, nullable=True)
    assets = Column(JSONB, nullable=True)
    liabilities = Column(JSONB, nullable=True)
    shareholders_equity = Column(JSONB, nullable=True)
    
    # حقل إضافي لاستيعاب أي بيانات أخرى
    additional_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<BalanceSheet(symbol='{self.symbol}', country='{self.country}', year='{self.year}')>"

class CashFlow(Base):
    __tablename__ = "cash_flows"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    country = Column(String(50), index=True, nullable=False, default="Saudi Arabia")
    fiscal_date = Column(Date, nullable=True)
    quarter = Column(String(10), nullable=True)
    year = Column(Integer, nullable=True)
    
    operating_activities = Column(JSONB, nullable=True)
    investing_activities = Column(JSONB, nullable=True)
    financing_activities = Column(JSONB, nullable=True)
    net_cash_change = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)
    end_cash_position = Column(Float, nullable=True)
    
    # الحقول الجديدة المطلوبة بناءً على الـ logs
    income_tax_paid = Column(Float, nullable=True)
    
    # حقل إضافي لاستيعاب أي بيانات أخرى
    additional_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
        
    def __repr__(self):
        return f"<CashFlow(symbol='{self.symbol}', country='{self.country}', year='{self.year}')>"