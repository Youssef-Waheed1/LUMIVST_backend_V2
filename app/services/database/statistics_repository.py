from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.statistics import Statistics
from app.schemas.statistics import StatisticsResponse
from services.twelve_data.statistics_service import StatisticsService
from datetime import datetime
import uuid

class StatisticsRepository:
    def __init__(self, db: Session):
        self.db = db
        self.twelve_data_service = StatisticsService()
        
    async def get_statistics(
        self,
        symbol: Optional[str] = None,
        figi: Optional[str] = None,
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        exchange: Optional[str] = None,
        mic_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> StatisticsResponse:
        """
        Get statistics data, first from database, then from Twelve Data if not found
        """
        # Try to get from database first
        db_statistics = self._get_from_database(
            symbol=symbol,
            figi=figi,
            isin=isin,
            cusip=cusip,
            exchange=exchange,
            mic_code=mic_code,
            country=country
        )
        
        if db_statistics and self._is_data_fresh(db_statistics):
            return StatisticsResponse(**db_statistics.statistics_data)
        
        # If not in database or data is stale, fetch from Twelve Data
        fresh_data = await self.twelve_data_service.get_statistics(
            symbol=symbol,
            figi=figi,
            isin=isin,
            cusip=cusip,
            exchange=exchange,
            mic_code=mic_code,
            country=country
        )
        
        # Save to database
        self._save_to_database(fresh_data)
        
        return StatisticsResponse(**fresh_data)
    
    def _get_from_database(
        self,
        symbol: Optional[str] = None,
        figi: Optional[str] = None,
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        exchange: Optional[str] = None,
        mic_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> Optional[Statistics]:
        """
        Retrieve statistics from database based on available parameters
        """
        query = self.db.query(Statistics)
        
        if symbol:
            query = query.filter(Statistics.symbol == symbol)
        elif figi:
            query = query.filter(Statistics.figi == figi)
        elif isin:
            query = query.filter(Statistics.isin == isin)
        elif cusip:
            query = query.filter(Statistics.cusip == cusip)
        elif exchange:
            query = query.filter(Statistics.exchange == exchange)
        elif mic_code:
            query = query.filter(Statistics.mic_code == mic_code)
        elif country:
            query = query.filter(Statistics.country == country)
            
        return query.first()
    
    def _save_to_database(self, data: Dict[str, Any]) -> Statistics:
        """
        Save statistics data to database
        """
        meta = data.get("meta", {})
        statistics_data = data.get("statistics", {})
        
        # Check if record already exists
        existing_record = self.db.query(Statistics).filter(
            Statistics.symbol == meta.get("symbol")
        ).first()
        
        now = datetime.utcnow()
        
        if existing_record:
            # Update existing record
            existing_record.statistics_data = data
            existing_record.updated_at = now
            statistics_record = existing_record
        else:
            # Create new record
            statistics_record = Statistics(
                id=uuid.uuid4(),
                symbol=meta.get("symbol"),
                name=meta.get("name"),
                currency=meta.get("currency"),
                exchange=meta.get("exchange"),
                mic_code=meta.get("mic_code"),
                exchange_timezone=meta.get("exchange_timezone"),
                statistics_data=data,
                created_at=now,
                updated_at=now
            )
            self.db.add(statistics_record)
        
        self.db.commit()
        self.db.refresh(statistics_record)
        
        return statistics_record
    
    def _is_data_fresh(self, statistics: Statistics) -> bool:
        """
        Check if the data is fresh (less than 24 hours old)
        """
        from datetime import timedelta
        
        if not statistics.updated_at:
            return False
            
        time_difference = datetime.utcnow() - statistics.updated_at
        return time_difference < timedelta(hours=24)