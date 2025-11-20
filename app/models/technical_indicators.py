from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, nullable=False)
    is_overlay = Column(Boolean, default=False)
    parameters = Column(JSON)
    output_values = Column(JSON)
    tinting = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TechnicalIndicator {self.name}>"

class TechnicalIndicatorData(Base):
    __tablename__ = "technical_indicator_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, nullable=False, index=True)
    indicator_name = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    values = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TechnicalIndicatorData {self.symbol} {self.indicator_name} {self.date}>"