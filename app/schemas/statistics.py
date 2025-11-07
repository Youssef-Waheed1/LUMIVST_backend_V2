from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import date

class Meta(BaseModel):
    symbol: str
    name: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    mic_code: Optional[str] = None
    exchange_timezone: Optional[str] = None

class ValuationsMetrics(BaseModel):
    market_capitalization: Optional[float] = None
    enterprise_value: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_sales_ttm: Optional[float] = None
    price_to_book_mrq: Optional[float] = None
    enterprise_to_revenue: Optional[float] = None
    enterprise_to_ebitda: Optional[float] = None

class IncomeStatement(BaseModel):
    revenue_ttm: Optional[float] = None
    revenue_per_share_ttm: Optional[float] = None
    quarterly_revenue_growth: Optional[float] = None
    gross_profit_ttm: Optional[float] = None
    ebitda: Optional[float] = None
    net_income_to_common_ttm: Optional[float] = None
    diluted_eps_ttm: Optional[float] = None
    quarterly_earnings_growth_yoy: Optional[float] = None

class BalanceSheet(BaseModel):
    total_cash_mrq: Optional[float] = None
    total_cash_per_share_mrq: Optional[float] = None
    total_debt_mrq: Optional[float] = None
    total_debt_to_equity_mrq: Optional[float] = None
    current_ratio_mrq: Optional[float] = None
    book_value_per_share_mrq: Optional[float] = None

class CashFlow(BaseModel):
    operating_cash_flow_ttm: Optional[float] = None
    levered_free_cash_flow_ttm: Optional[float] = None

class Financials(BaseModel):
    fiscal_year_ends: Optional[str] = None
    most_recent_quarter: Optional[str] = None
    gross_margin: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    return_on_assets_ttm: Optional[float] = None
    return_on_equity_ttm: Optional[float] = None
    income_statement: Optional[IncomeStatement] = None
    balance_sheet: Optional[BalanceSheet] = None
    cash_flow: Optional[CashFlow] = None

class StockStatistics(BaseModel):
    shares_outstanding: Optional[float] = None
    float_shares: Optional[float] = None
    avg_10_volume: Optional[float] = None
    avg_90_volume: Optional[float] = None
    shares_short: Optional[float] = None
    short_ratio: Optional[float] = None
    short_percent_of_shares_outstanding: Optional[float] = None
    percent_held_by_insiders: Optional[float] = None
    percent_held_by_institutions: Optional[float] = None

class StockPriceSummary(BaseModel):
    fifty_two_week_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_change: Optional[float] = None
    beta: Optional[float] = None
    day_50_ma: Optional[float] = None
    day_200_ma: Optional[float] = None

class DividendsAndSplits(BaseModel):
    forward_annual_dividend_rate: Optional[float] = None
    forward_annual_dividend_yield: Optional[float] = None
    trailing_annual_dividend_rate: Optional[float] = None
    trailing_annual_dividend_yield: Optional[float] = None
    five_year_average_dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    dividend_frequency: Optional[str] = None
    dividend_date: Optional[str] = None
    ex_dividend_date: Optional[str] = None
    last_split_factor: Optional[str] = None
    last_split_date: Optional[str] = None

class StatisticsData(BaseModel):
    valuations_metrics: Optional[ValuationsMetrics] = None
    financials: Optional[Financials] = None
    stock_statistics: Optional[StockStatistics] = None
    stock_price_summary: Optional[StockPriceSummary] = None
    dividends_and_splits: Optional[DividendsAndSplits] = None

class StatisticsResponse(BaseModel):
    meta: Meta
    statistics: StatisticsData

    class Config:
        schema_extra = {
            "example": {
                "meta": {
                    "symbol": "1180",
                    "name": "شركة مثال",
                    "currency": "SAR",
                    "exchange": "TADAWUL",
                    "mic_code": "XSAU",
                    "exchange_timezone": "Asia/Riyadh"
                },
                "statistics": {
                    "valuations_metrics": {
                        "market_capitalization": 50000000000,
                        "enterprise_value": 52000000000,
                        "trailing_pe": 15.5,
                        "forward_pe": 14.2,
                        "price_to_sales_ttm": 3.2,
                        "price_to_book_mrq": 2.1
                    },
                    "financials": {
                        "fiscal_year_ends": "2023-12-31",
                        "profit_margin": 0.22,
                        "return_on_equity_ttm": 0.18
                    }
                }
            }
        }