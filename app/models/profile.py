from sqlalchemy import Column, String, Integer, Text
from app.core.database import Base

class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    
    symbol = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    exchange = Column(String(100))
    sector = Column(String(255))
    industry = Column(String(255))
    employees = Column(Integer)
    website = Column(String(500))
    description = Column(Text)
    state = Column(String(100))
    country = Column(String(100))
    logo_url = Column(String(500))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    zip_code = Column(String(20))




    