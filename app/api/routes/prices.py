from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.models.price import Price
from app.schemas.price import PriceResponse, LatestPricesResponse

router = APIRouter(prefix="/prices", tags=["Prices"])

import csv
from pathlib import Path

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

        # 3. Load TradingView Symbols Mapping
        tv_mapping = {}
        try:
            # Assuming company_symbols.csv is in backend/company_symbols.csv
            # Current file is backend/app/api/routes/prices.py
            csv_path = Path(__file__).resolve().parent.parent.parent.parent / "company_symbols.csv"
            
            if csv_path.exists():
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # CSV Header: Symbol,Company,symbol on tradingView
                        sym = str(row.get('Symbol', '')).strip()
                        tv_sym = str(row.get('symbol on tradingView', '')).strip()
                        if sym and tv_sym:
                            tv_mapping[sym] = tv_sym
        except Exception as e:
            print(f"Error loading company_symbols.csv: {e}")

        # 4. Attach TradingView Symbol to results
        # We need to convert SQLAlchemy objects to Pydantic models to add the field
        # because the SQLAlchemy model doesn't have this field.
        # But wait, Pydantic's from_attributes=True might try to read it from the object.
        # If we just attach it to the object instances, python allows it.
        
        for price in results:
            price.trading_view_symbol = tv_mapping.get(str(price.symbol))

        return LatestPricesResponse(
            date=latest_date,
            count=len(results),
            data=results
        )
    except Exception as e:
        print(f"Error fetching latest prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
