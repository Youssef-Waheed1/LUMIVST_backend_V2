from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.quote import StockQuote
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QuoteRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_quote_by_symbol(self, symbol: str) -> Optional[StockQuote]:
        """البحث عن بيانات سعر بالرمز"""
        try:
            return self.db.query(StockQuote).filter(StockQuote.symbol == symbol).first()
        except Exception as e:
            logger.error(f"خطأ في البحث عن بيانات السعر للرمز {symbol}: {e}")
            return None
    
    def get_all_quotes(self) -> List[StockQuote]:
        """جلب كل بيانات الأسعار"""
        try:
            return self.db.query(StockQuote).all()
        except Exception as e:
            logger.error(f"خطأ في جلب كل بيانات الأسعار: {e}")
            return []
    
    def create_or_update_quote(self, quote_data: Dict[str, Any]) -> Optional[StockQuote]:
        """إنشاء أو تحديث بيانات سعر"""
        try:
            symbol = quote_data.get('symbol')
            if not symbol:
                return None
            
            existing_quote = self.get_quote_by_symbol(symbol)
            
            if existing_quote:
                # تحديث البيانات
                for key, value in quote_data.items():
                    if hasattr(existing_quote, key) and value is not None:
                        setattr(existing_quote, key, value)
                existing_quote.updated_at = datetime.now()
            else:
                # إنشاء جديد
                existing_quote = StockQuote(**quote_data)
                self.db.add(existing_quote)
            
            self.db.commit()
            self.db.refresh(existing_quote)
            return existing_quote
            
        except Exception as e:
            logger.error(f"خطأ في حفظ/تحديث بيانات السعر {quote_data.get('symbol')}: {e}")
            self.db.rollback()
            return None
    
    def bulk_create_or_update_quotes(self, quotes_data: List[Dict[str, Any]]) -> List[StockQuote]:
        """حفظ مجموعة من بيانات الأسعار"""
        results = []
        for quote_data in quotes_data:
            quote = self.create_or_update_quote(quote_data)
            if quote:
                results.append(quote)
        return results