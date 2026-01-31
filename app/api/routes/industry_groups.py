from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from app.core.database import get_db
from app.models.industry_group import IndustryGroupHistory

router = APIRouter()

class IndustryGroupResponse(BaseModel):
    id: int
    date: date
    industry_group: str
    sector: Optional[str]
    number_of_stocks: int
    market_value: Optional[float]
    rs_score: Optional[float]
    rank: Optional[int]
    rank_1_week_ago: Optional[int]
    rank_3_months_ago: Optional[int]
    rank_6_months_ago: Optional[int]
    ytd_change_percent: Optional[float]

    class Config:
        orm_mode = True

@router.get("/latest", response_model=List[IndustryGroupResponse])
def get_latest_industry_groups(
    db: Session = Depends(get_db)
):
    """
    Get industry group rankings for the latest available date.
    """
    # Find latest date
    latest_date = db.query(func.max(IndustryGroupHistory.date)).scalar()
    
    if not latest_date:
        return []
        
    # Get all groups for that date, ordered by Rank
    # Handle NULL ranks by putting them last
    groups = db.query(IndustryGroupHistory).filter(
        IndustryGroupHistory.date == latest_date
    ).order_by(
        IndustryGroupHistory.rank.asc().nullslast()
    ).all()
    
    return groups
