from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from app.models.technical_indicators import TechnicalIndicator, TechnicalIndicatorData
from app.schemas.technical_indicators import TechnicalIndicatorCreate, TechnicalIndicatorDataCreate

class TechnicalIndicatorsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_indicators(self) -> List[TechnicalIndicator]:
        return self.db.query(TechnicalIndicator).all()

    def get_indicator_by_name(self, name: str) -> Optional[TechnicalIndicator]:
        return self.db.query(TechnicalIndicator).filter(TechnicalIndicator.name == name).first()

    def get_indicators_by_category(self, category: str) -> List[TechnicalIndicator]:
        return self.db.query(TechnicalIndicator).filter(TechnicalIndicator.category == category).all()

    def create_indicator(self, indicator_data: TechnicalIndicatorCreate) -> TechnicalIndicator:
        db_indicator = TechnicalIndicator(**indicator_data.dict())
        self.db.add(db_indicator)
        self.db.commit()
        self.db.refresh(db_indicator)
        return db_indicator

    def save_indicator_data(self, data: TechnicalIndicatorDataCreate) -> TechnicalIndicatorData:
        # Check if data already exists
        existing = self.db.query(TechnicalIndicatorData).filter(
            and_(
                TechnicalIndicatorData.symbol == data.symbol,
                TechnicalIndicatorData.indicator_name == data.indicator_name,
                TechnicalIndicatorData.timeframe == data.timeframe,
                TechnicalIndicatorData.date == data.date
            )
        ).first()
        
        if existing:
            # Update existing record
            existing.values = data.values
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            db_data = TechnicalIndicatorData(**data.dict())
            self.db.add(db_data)
            self.db.commit()
            self.db.refresh(db_data)
            return db_data

    def get_indicator_data(self, symbol: str, indicator_name: str, timeframe: str, 
                          start_date: datetime, end_date: datetime) -> List[TechnicalIndicatorData]:
        return self.db.query(TechnicalIndicatorData).filter(
            and_(
                TechnicalIndicatorData.symbol == symbol,
                TechnicalIndicatorData.indicator_name == indicator_name,
                TechnicalIndicatorData.timeframe == timeframe,
                TechnicalIndicatorData.date >= start_date,
                TechnicalIndicatorData.date <= end_date
            )
        ).order_by(TechnicalIndicatorData.date.asc()).all()

    def get_latest_indicator_data(self, symbol: str, indicator_name: str, timeframe: str) -> Optional[TechnicalIndicatorData]:
        return self.db.query(TechnicalIndicatorData).filter(
            and_(
                TechnicalIndicatorData.symbol == symbol,
                TechnicalIndicatorData.indicator_name == indicator_name,
                TechnicalIndicatorData.timeframe == timeframe
            )
        ).order_by(desc(TechnicalIndicatorData.date)).first()

    def batch_save_indicator_data(self, data_list: List[TechnicalIndicatorDataCreate]) -> List[TechnicalIndicatorData]:
        saved_data = []
        for data in data_list:
            saved = self.save_indicator_data(data)
            saved_data.append(saved)
        return saved_data