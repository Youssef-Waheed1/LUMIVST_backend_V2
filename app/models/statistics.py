from sqlalchemy import Column, String, Float, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base
from sqlalchemy.sql import func

class Statistics(Base):
    __tablename__ = "statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(50), nullable=False, index=True)
    country = Column(String(50), nullable=False, index=True, default="Saudi Arabia")
    
    # Metadata
    name = Column(String(255), nullable=True)
    currency = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)
    mic_code = Column(String(50), nullable=True)
    exchange_timezone = Column(String(50), nullable=True)
    
    # Statistics data stored as JSON for flexibility
    statistics_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Statistics(symbol='{self.symbol}', country='{self.country}')>"