from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.models.price import Price
from app.schemas.price import PriceResponse, LatestPricesResponse

router = APIRouter(prefix="/prices", tags=["Prices"])

@router.get("/latest", response_model=LatestPricesResponse)
async def get_latest_prices(
    db: Session = Depends(get_db),
    limit: int = Query(500, le=1000)
):
    """
    Get the latest prices for all stocks.
    Finds the most recent date in the prices table and returns all records for that date.
    """
    try:
        # 1. Find the latest date
        latest_date_row = db.query(Price.date).order_by(desc(Price.date)).first()
        
        if not latest_date_row:
            return LatestPricesResponse(date=date.today(), count=0, data=[])
        
        latest_date = latest_date_row[0]
        
        # 2. Query data for that date
        results = db.query(Price).filter(Price.date == latest_date).limit(limit).all()
        
        return LatestPricesResponse(
            date=latest_date,
            count=len(results),
            data=results
        )
    except Exception as e:
        print(f"Error fetching latest prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
