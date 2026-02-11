from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.models.financial_metrics import CompanyFinancialMetric
from pydantic import BaseModel

router = APIRouter()

class MetricResponse(BaseModel):
    id: int
    year: int
    period: str
    metric_name: str
    metric_value: Optional[float]
    metric_text: Optional[str]
    label_en: Optional[str]
    source_file: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/compare", response_model=List[Dict[str, Any]])
def compare_companies(
    symbols: List[str] = Query(..., description="List of company symbols to compare"),
    metric_name: str = Query(..., description="Metric key to compare (e.g., net_profit)"),
    period: Optional[str] = Query('Annual', description="Period to filter (Default: Annual)"),
    years: Optional[List[int]] = Query(None, description="Specific years to compare"),
    db: Session = Depends(get_db)
):
    """
    Compare a specific metric across multiple companies.
    Returns a list of data points suitable for charting or tables.
    Example: Compare 'net_profit' for [1010, 1120] in 'Annual' reports.
    """
    query = db.query(CompanyFinancialMetric).filter(
        CompanyFinancialMetric.company_symbol.in_(symbols),
        CompanyFinancialMetric.metric_name == metric_name,
        CompanyFinancialMetric.period == period
    )
    
    if years:
        query = query.filter(CompanyFinancialMetric.year.in_(years))
        
    results = query.order_by(CompanyFinancialMetric.year).all()
    
    # Transform into a structured list
    comparison_data = []
    for r in results:
        comparison_data.append({
            "symbol": r.company_symbol,
            "year": r.year,
            "period": r.period,
            "value": r.metric_value,
            "label": r.label_en
        })
        
    return comparison_data
