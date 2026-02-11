from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.financial_metrics import CompanyFinancialMetric
from collections import defaultdict

router = APIRouter()

@router.get("/{symbol}/xbrl", response_model=Dict[str, List[Dict[str, Any]]])
def get_company_xbrl_data(symbol: str, db: Session = Depends(get_db)):
    """
    Fetches detailed XBRL financial data from PostgreSQL for a specific company.
    Returns data grouped by period (e.g., '2023_Annual': [metrics...])
    to match the structure expected by the frontend.
    """
    # 1. Fetch all metrics for the symbol
    metrics = db.query(CompanyFinancialMetric)\
        .filter(CompanyFinancialMetric.company_symbol == symbol)\
        .order_by(CompanyFinancialMetric.year.desc())\
        .all()

    if not metrics:
        # Return empty structure instead of 404 to allow empty state handling
        return {}

    # 2. Group by "Year_Period" (e.g., 2023_Annual, 2024_Q1)
    # The frontend expects a dictionary where keys are time periods
    grouped_data = defaultdict(list)
    
    for m in metrics:
        # Create a unique key for the period (UPPERCASE for frontend consistency)
        period_key = f"{m.year} {m.period}".upper()
        
        # Structure the metric object similar to the old JSON format
        metric_obj = {
            "key": m.metric_name,
            "label": m.label_en if m.label_en else m.metric_name,
            "value": m.metric_value,
            "text": m.metric_text,
            "source": m.source_file
        }
        
        grouped_data[period_key].append(metric_obj)

    return grouped_data
