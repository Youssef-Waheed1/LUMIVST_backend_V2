from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.corporate import Dividend, StockSplit
from app.schemas.corporate import Dividend as DividendSchema, StockSplit as StockSplitSchema
from app.services.twelve_data.corporate import CorporateService
from app.utils.logger import logger
from app.utils.parser import safe_float, safe_string
from app.utils.parser import normalize_saudi_symbol

router = APIRouter()
corporate_service = CorporateService()

@router.get("/corporate/dividends/{symbol}", response_model=List[DividendSchema])
async def get_dividends(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get dividend data for a symbol"""
    try:
        # نظف الرمز من .SR إذا موجود
        normalized_symbol = normalize_saudi_symbol(symbol)
        
        # Try to get from database first
        dividends = db.query(Dividend).filter(
            Dividend.symbol == normalized_symbol
        ).order_by(Dividend.ex_dividend_date.desc()).all()
        
        if not dividends:
            # Fetch from API
            dividends = await fetch_dividends_from_api(normalized_symbol, db)
        
        return dividends
        
    except Exception as e:
        logger.error(f"Error fetching dividends for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/corporate/splits/{symbol}", response_model=List[StockSplitSchema])
async def get_stock_splits(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get stock splits for a symbol"""
    try:
        # نظف الرمز من .SR إذا موجود
        normalized_symbol = normalize_saudi_symbol(symbol)
        
        # Try to get from database first
        splits = db.query(StockSplit).filter(
            StockSplit.symbol == normalized_symbol
        ).order_by(StockSplit.execution_date.desc()).all()
        
        if not splits:
            # Fetch from API
            splits = await fetch_splits_from_api(normalized_symbol, db)
        
        return splits
        
    except Exception as e:
        logger.error(f"Error fetching stock splits for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def fetch_dividends_from_api(symbol: str, db: Session) -> List[Dividend]:
    """Fetch dividends from API and upsert"""
    try:
        data = corporate_service.get_dividends(symbol)
        dividends = []
        
        if data and isinstance(data, dict) and 'data' in data:
            dividends_data = data.get('data', [])
            
            for item in dividends_data:
                dividend_data = {
                    "symbol": symbol,
                    "amount": safe_float(item.get('amount')),
                    "ex_dividend_date": safe_string(item.get('ex_dividend_date')),
                    "payment_date": safe_string(item.get('payment_date')),
                    "record_date": safe_string(item.get('record_date'))
                }
                
                # تحقق من صحة البيانات قبل التخزين
                if dividend_data["amount"] and dividend_data["ex_dividend_date"]:
                    dividend = upsert_dividend(db, dividend_data)
                    if dividend:
                        dividends.append(dividend)
            
            db.commit()
            logger.info(f"Successfully stored {len(dividends)} dividends for {symbol}")
        
        return dividends
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching dividends for {symbol} from API: {e}")
        return []

async def fetch_splits_from_api(symbol: str, db: Session) -> List[StockSplit]:
    """Fetch stock splits from API and upsert"""
    try:
        data = corporate_service.get_splits(symbol)
        splits = []
        
        if data and isinstance(data, dict) and 'data' in data:
            splits_data = data.get('data', [])
            
            for item in splits_data:
                split_data = {
                    "symbol": symbol,
                    "split_ratio": safe_string(item.get('split_ratio', '1:1')),
                    "execution_date": safe_string(item.get('execution_date'))
                }
                
                # تحقق من صحة البيانات قبل التخزين
                if split_data["split_ratio"] and split_data["execution_date"]:
                    split = upsert_stock_split(db, split_data)
                    if split:
                        splits.append(split)
            
            db.commit()
            logger.info(f"Successfully stored {len(splits)} stock splits for {symbol}")
        
        return splits
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching stock splits for {symbol} from API: {e}")
        return []

def upsert_dividend(db: Session, data: dict) -> Dividend:
    """Upsert dividend data"""
    try:
        symbol = data["symbol"]
        ex_dividend_date = data["ex_dividend_date"]
        
        # تحقق من صحة البيانات
        if not symbol or not ex_dividend_date:
            logger.warning(f"Invalid dividend data: {data}")
            return None
        
        existing = db.query(Dividend).filter(
            Dividend.symbol == symbol,
            Dividend.ex_dividend_date == ex_dividend_date
        ).first()
        
        if existing:
            # Update existing - تحديث الحقول الغير None فقط
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            # Create new
            dividend = Dividend(**data)
            db.add(dividend)
            return dividend
            
    except Exception as e:
        logger.error(f"Error in upsert_dividend for {data.get('symbol')}: {e}")
        return None

def upsert_stock_split(db: Session, data: dict) -> StockSplit:
    """Upsert stock split data"""
    try:
        symbol = data["symbol"]
        execution_date = data["execution_date"]
        
        # تحقق من صحة البيانات
        if not symbol or not execution_date:
            logger.warning(f"Invalid stock split data: {data}")
            return None
        
        existing = db.query(StockSplit).filter(
            StockSplit.symbol == symbol,
            StockSplit.execution_date == execution_date
        ).first()
        
        if existing:
            # Update existing - تحديث الحقول الغير None فقط
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            # Create new
            split = StockSplit(**data)
            db.add(split)
            return split
            
    except Exception as e:
        logger.error(f"Error in upsert_stock_split for {data.get('symbol')}: {e}")
        return None