from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import date, datetime

# Income Statement Schemas
class OperatingExpense(BaseModel):
    research_and_development: Optional[float] = None
    selling_general_and_administrative: Optional[float] = None
    other_operating_expenses: Optional[float] = None

class NonOperatingInterest(BaseModel):
    income: Optional[float] = None
    expense: Optional[float] = None

class IncomeStatementBase(BaseModel):
    fiscal_date: date
    quarter: Optional[str] = None  # اجعله نص زي المودل    year: int
    sales: Optional[float] = None
    cost_of_goods: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expense: Optional[OperatingExpense] = None
    operating_income: Optional[float] = None
    non_operating_interest: Optional[NonOperatingInterest] = None
    other_income_expense: Optional[float] = None
    pretax_income: Optional[float] = None
    income_tax: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    basic_shares_outstanding: Optional[float] = None
    diluted_shares_outstanding: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None
    net_income_continuous_operations: Optional[float] = None
    minority_interests: Optional[float] = None
    preferred_stock_dividends: Optional[float] = None

class IncomeStatement(IncomeStatementBase):
    id: int
    symbol: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class IncomeStatementMeta(BaseModel):
    symbol: str
    name: str
    currency: str
    exchange: str
    mic_code: str
    exchange_timezone: str
    period: str

class IncomeStatementResponse(BaseModel):
    meta: IncomeStatementMeta
    income_statement: List[IncomeStatement]

# Balance Sheet Schemas
class CurrentAssets(BaseModel):
    cash: Optional[float] = None
    cash_equivalents: Optional[float] = None
    cash_and_cash_equivalents: Optional[float] = None
    other_short_term_investments: Optional[float] = None
    accounts_receivable: Optional[float] = None
    other_receivables: Optional[float] = None
    inventory: Optional[float] = None
    prepaid_assets: Optional[float] = None
    restricted_cash: Optional[float] = None
    assets_held_for_sale: Optional[float] = None
    hedging_assets: Optional[float] = None
    other_current_assets: Optional[float] = None
    total_current_assets: Optional[float] = None

class NonCurrentAssets(BaseModel):
    properties: Optional[float] = None
    land_and_improvements: Optional[float] = None
    machinery_furniture_equipment: Optional[float] = None
    construction_in_progress: Optional[float] = None
    leases: Optional[float] = None
    accumulated_depreciation: Optional[float] = None
    goodwill: Optional[float] = None
    investment_properties: Optional[float] = None
    financial_assets: Optional[float] = None
    intangible_assets: Optional[float] = None
    investments_and_advances: Optional[float] = None
    other_non_current_assets: Optional[float] = None
    total_non_current_assets: Optional[float] = None

class Assets(BaseModel):
    current_assets: Optional[CurrentAssets] = None
    non_current_assets: Optional[NonCurrentAssets] = None
    total_assets: Optional[float] = None

class CurrentLiabilities(BaseModel):
    accounts_payable: Optional[float] = None
    accrued_expenses: Optional[float] = None
    short_term_debt: Optional[float] = None
    deferred_revenue: Optional[float] = None
    tax_payable: Optional[float] = None
    pensions: Optional[float] = None
    other_current_liabilities: Optional[float] = None
    total_current_liabilities: Optional[float] = None

class NonCurrentLiabilities(BaseModel):
    long_term_provisions: Optional[float] = None
    long_term_debt: Optional[float] = None
    provision_for_risks_and_charges: Optional[float] = None
    deferred_liabilities: Optional[float] = None
    derivative_product_liabilities: Optional[float] = None
    other_non_current_liabilities: Optional[float] = None
    total_non_current_liabilities: Optional[float] = None

class Liabilities(BaseModel):
    current_liabilities: Optional[CurrentLiabilities] = None
    non_current_liabilities: Optional[NonCurrentLiabilities] = None
    total_liabilities: Optional[float] = None

class ShareholdersEquity(BaseModel):
    common_stock: Optional[float] = None
    retained_earnings: Optional[float] = None
    other_shareholders_equity: Optional[float] = None
    total_shareholders_equity: Optional[float] = None
    additional_paid_in_capital: Optional[float] = None
    treasury_stock: Optional[float] = None
    minority_interest: Optional[float] = None

class BalanceSheetBase(BaseModel):
    fiscal_date: date
    quarter: Optional[str] = None
    year: int
    assets: Optional[Assets] = None
    liabilities: Optional[Liabilities] = None
    shareholders_equity: Optional[ShareholdersEquity] = None

class BalanceSheet(BalanceSheetBase):
    id: int
    symbol: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BalanceSheetResponse(BaseModel):
    meta: IncomeStatementMeta
    balance_sheet: List[BalanceSheet]

# Cash Flow Schemas
class OperatingActivities(BaseModel):
    net_income: Optional[float] = None
    depreciation: Optional[float] = None
    deferred_taxes: Optional[float] = None
    stock_based_compensation: Optional[float] = None
    other_non_cash_items: Optional[float] = None
    accounts_receivable: Optional[float] = None
    accounts_payable: Optional[float] = None
    other_assets_liabilities: Optional[float] = None
    operating_cash_flow: Optional[float] = None

class InvestingActivities(BaseModel):
    capital_expenditures: Optional[float] = None
    net_intangibles: Optional[float] = None
    net_acquisitions: Optional[float] = None
    purchase_of_investments: Optional[float] = None
    sale_of_investments: Optional[float] = None
    other_investing_activity: Optional[float] = None
    investing_cash_flow: Optional[float] = None

class FinancingActivities(BaseModel):
    long_term_debt_issuance: Optional[float] = None
    long_term_debt_payments: Optional[float] = None
    short_term_debt_issuance: Optional[float] = None
    common_stock_issuance: Optional[float] = None
    common_stock_repurchase: Optional[float] = None
    common_dividends: Optional[float] = None
    other_financing_charges: Optional[float] = None
    financing_cash_flow: Optional[float] = None

class CashFlowBase(BaseModel):
    fiscal_date: date
    quarter: Optional[str] = None
    year: int
    operating_activities: Optional[OperatingActivities] = None
    investing_activities: Optional[InvestingActivities] = None
    financing_activities: Optional[FinancingActivities] = None
    end_cash_position: Optional[float] = None
    income_tax_paid: Optional[float] = None
    interest_paid: Optional[float] = None
    free_cash_flow: Optional[float] = None

class CashFlow(CashFlowBase):
    id: int
    symbol: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CashFlowResponse(BaseModel):
    meta: IncomeStatementMeta
    cash_flow: List[CashFlow]