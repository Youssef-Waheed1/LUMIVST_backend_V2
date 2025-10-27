from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.models.technicals import TimeSeries, TechnicalIndicator
from app.schemas.technicals import TimeSeries as TimeSeriesSchema, TechnicalIndicator as TechnicalIndicatorSchema
from app.services.twelve_data.technicals import TechnicalsService
from app.utils.logger import logger
from app.utils.parser import safe_float, safe_string
from app.utils.parser import normalize_saudi_symbol

router = APIRouter()
technicals_service = TechnicalsService()

@router.get("/technicals/timeseries/{symbol}", response_model=List[TimeSeriesSchema])
async def get_time_series(
    symbol: str,
    interval: str = Query("1day", regex="^(1min|5min|15min|1day)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get time series data for a symbol"""
    try:
        # نظف الرمز من .SR إذا موجود
        normalized_symbol = normalize_saudi_symbol(symbol)
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Try to get from database first
        query = db.query(TimeSeries).filter(
            TimeSeries.symbol == normalized_symbol,
            TimeSeries.date >= start_date,
            TimeSeries.date <= end_date
        ).order_by(TimeSeries.date.desc())
        
        time_series = query.all()
        
        if not time_series:
            # Fetch from API
            time_series = await fetch_time_series_from_api(normalized_symbol, interval, start_date, end_date, db)
        
        return time_series
        
    except Exception as e:
        logger.error(f"Error fetching time series for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/technicals/indicators/{symbol}", response_model=List[TechnicalIndicatorSchema])
async def get_technical_indicators(
    symbol: str,
    indicator_type: str = Query(..., regex="^(RSI|MACD|SMA|EMA)$"),
    interval: str = Query("1day", regex="^(1min|5min|15min|1day)$"),
    db: Session = Depends(get_db)
):
    """Get technical indicators for a symbol"""
    try:
        # نظف الرمز من .SR إذا موجود
        normalized_symbol = normalize_saudi_symbol(symbol)
        
        # Try to get from database first
        indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.symbol == normalized_symbol,
            TechnicalIndicator.indicator_type == indicator_type
        ).order_by(TechnicalIndicator.date.desc()).limit(50).all()
        
        if not indicators:
            # Fetch from API based on indicator type
            indicators = await fetch_indicator_from_api(normalized_symbol, indicator_type, interval, db)
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error fetching {indicator_type} for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def fetch_time_series_from_api(symbol: str, interval: str, start_date: date, end_date: date, db: Session) -> List[TimeSeries]:
    """Fetch time series from API and upsert"""
    try:
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        data = technicals_service.get_time_series(symbol, interval, start_str, end_str)
        time_series = []
        
        if data and isinstance(data, dict) and 'values' in data:
            for item in data['values']:
                ts_data = {
                    "symbol": symbol,
                    "date": safe_string(item.get('datetime')),
                    "open": safe_float(item.get('open')),
                    "high": safe_float(item.get('high')),
                    "low": safe_float(item.get('low')),
                    "close": safe_float(item.get('close')),
                    "volume": safe_float(item.get('volume', 0))
                }
                
                # تحقق من صحة البيانات قبل التخزين
                if ts_data["date"] and ts_data["close"]:
                    # Convert date string to date object
                    try:
                        ts_data["date"] = datetime.strptime(ts_data["date"], '%Y-%m-%d').date()
                    except ValueError:
                        continue
                    
                    time_series_item = upsert_time_series(db, ts_data)
                    if time_series_item:
                        time_series.append(time_series_item)
        
            db.commit()
            logger.info(f"Successfully stored {len(time_series)} time series records for {symbol}")
        
        return time_series
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching time series for {symbol} from API: {e}")
        return []

async def fetch_indicator_from_api(symbol: str, indicator_type: str, interval: str, db: Session) -> List[TechnicalIndicator]:
    """Fetch technical indicator from API and upsert"""
    try:
        data = technicals_service.get_technical_indicator(symbol, indicator_type, interval)
        indicators = []
        
        if data and isinstance(data, dict) and 'values' in data:
            for item in data['values']:
                indicator_data = {
                    "symbol": symbol,
                    "date": safe_string(item.get('datetime')),
                    "indicator_type": indicator_type,
                    "value": safe_float(item.get('value', item.get(indicator_type.lower(), 0)))
                }
                
                # تحقق من صحة البيانات قبل التخزين
                if indicator_data["date"] and indicator_data["value"] is not None:
                    # Convert date string to date object
                    try:
                        indicator_data["date"] = datetime.strptime(indicator_data["date"], '%Y-%m-%d').date()
                    except ValueError:
                        continue
                    
                    indicator = upsert_technical_indicator(db, indicator_data)
                    if indicator:
                        indicators.append(indicator)
        
            db.commit()
            logger.info(f"Successfully stored {len(indicators)} {indicator_type} indicators for {symbol}")
        
        return indicators
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching {indicator_type} for {symbol} from API: {e}")
        return []

def upsert_time_series(db: Session, data: dict) -> TimeSeries:
    """Upsert time series data"""
    try:
        symbol = data["symbol"]
        date = data["date"]
        
        # تحقق من صحة البيانات
        if not symbol or not date:
            logger.warning(f"Invalid time series data: {data}")
            return None
        
        existing = db.query(TimeSeries).filter(
            TimeSeries.symbol == symbol,
            TimeSeries.date == date
        ).first()
        
        if existing:
            # Update existing - تحديث الحقول الغير None فقط
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            ts = TimeSeries(**data)
            db.add(ts)
            return ts
            
    except Exception as e:
        logger.error(f"Error in upsert_time_series for {data.get('symbol')}: {e}")
        return None

def upsert_technical_indicator(db: Session, data: dict) -> TechnicalIndicator:
    """Upsert technical indicator"""
    try:
        symbol = data["symbol"]
        date = data["date"]
        indicator_type = data["indicator_type"]
        
        # تحقق من صحة البيانات
        if not symbol or not date or not indicator_type:
            logger.warning(f"Invalid technical indicator data: {data}")
            return None
        
        existing = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.symbol == symbol,
            TechnicalIndicator.date == date,
            TechnicalIndicator.indicator_type == indicator_type
        ).first()
        
        if existing:
            # Update existing - تحديث الحقول الغير None فقط
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            indicator = TechnicalIndicator(**data)
            db.add(indicator)
            return indicator
            
    except Exception as e:
        logger.error(f"Error in upsert_technical_indicator for {data.get('symbol')}: {e}")
        return None