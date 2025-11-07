from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.quote import Company
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_company_by_symbol(self, symbol: str) -> Optional[Company]:
        """البحث عن شركة بالرمز في PostgreSQL مع معالجة الأخطاء"""
        try:
            return self.db.query(Company).filter(Company.symbol == symbol).first()
        except Exception as e:
            logger.error(f"خطأ في البحث عن الشركة بالرمز {symbol}: {e}")
            return None
    
    def get_all_companies(self) -> Dict[str, Any]:
        """جلب كل الشركات بدون pagination"""
        try:
            companies = self.db.query(Company).all()
            
            # تحويل إلى dictionaries بشكل آمن
            companies_data = []
            for company in companies:
                try:
                    company_dict = {
                        "symbol": company.symbol,
                        "name": company.name,
                        "exchange": company.exchange or "Tadawul",
                        "currency": getattr(company, 'currency', None),
                        "price": getattr(company, 'price', None),
                        "change": getattr(company, 'change', None),
                        "change_percent": getattr(company, 'change_percent', None),
                        "previous_close": getattr(company, 'previous_close', None),
                        "volume": getattr(company, 'volume', None),
                        "turnover": getattr(company, 'turnover', None),
                        "fifty_two_week_range": getattr(company, 'fifty_two_week_range', None),
                        "last_updated": company.updated_at.isoformat() if company.updated_at else None
                    }
                    companies_data.append(company_dict)
                except Exception as e:
                    logger.warning(f"خطأ في تحويل بيانات الشركة {company.symbol}: {e}")
                    continue
            
            return {
                "data": companies_data,
                "total": len(companies_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في جلب كل الشركات من PostgreSQL: {e}")
            return {"data": [], "total": 0}
    
    def get_companies_paginated(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """جلب الشركات مع pagination من PostgreSQL مع معالجة الأخطاء"""
        try:
            offset = (page - 1) * limit
            
            companies = self.db.query(Company).offset(offset).limit(limit).all()
            total = self.db.query(Company).count()
            total_pages = (total + limit - 1) // limit
            
            # تحويل إلى dictionaries بشكل آمن
            companies_data = []
            for company in companies:
                try:
                    company_dict = {
                        "symbol": company.symbol,
                        "name": company.name,
                        "exchange": company.exchange or "Tadawul",
                        "currency": getattr(company, 'currency', None),
                        "price": getattr(company, 'price', None),
                        "change": getattr(company, 'change', None),
                        "change_percent": getattr(company, 'change_percent', None),
                        "previous_close": getattr(company, 'previous_close', None),
                        "volume": getattr(company, 'volume', None),
                        "turnover": getattr(company, 'turnover', None),
                        "fifty_two_week_range": getattr(company, 'fifty_two_week_range', None),
                    }
                    companies_data.append(company_dict)
                except Exception as e:
                    logger.warning(f"خطأ في تحويل بيانات الشركة {company.symbol}: {e}")
                    continue
            
            return {
                "data": companies_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"خطأ في جلب الشركات من PostgreSQL: {e}")
            return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0}}
    
    def create_or_update_company(self, company_data: Dict[str, Any]) -> Optional[Company]:
        """إنشاء أو تحديث بيانات الشركة في PostgreSQL مع معالجة الأخطاء"""
        try:
            symbol = company_data.get('symbol')
            if not symbol:
                return None
            
            # البحث عن الشركة الموجودة
            existing_company = self.get_company_by_symbol(symbol)
            
            if existing_company:
                # تحديث البيانات بشكل انتقائي
                update_data = {}
                for key, value in company_data.items():
                    if hasattr(existing_company, key) and value is not None:
                        # تجنب تحديث الحقول الفارغة
                        if value != "N/A" and value != "":
                            update_data[key] = value
                
                if update_data:
                    for key, value in update_data.items():
                        setattr(existing_company, key, value)
                    existing_company.updated_at = datetime.now()
            else:
                # إنشاء جديد مع البيانات المتاحة فقط
                create_data = {}
                for key, value in company_data.items():
                    if hasattr(Company, key) and value is not None:
                        # تجنب حفظ القيم غير الصالحة
                        if value != "N/A" and value != "":
                            create_data[key] = value
                
                existing_company = Company(**create_data)
                self.db.add(existing_company)
            
            self.db.commit()
            self.db.refresh(existing_company)
            return existing_company
            
        except Exception as e:
            logger.error(f"خطأ في حفظ/تحديث الشركة {company_data.get('symbol')}: {e}")
            self.db.rollback()
            return None
    
    def bulk_create_or_update_companies(self, companies_data: List[Dict[str, Any]]) -> List[Company]:
        """حفظ مجموعة من الشركات في PostgreSQL"""
        results = []
        for company_data in companies_data:
            company = self.create_or_update_company(company_data)
            if company:
                results.append(company)
        return results
