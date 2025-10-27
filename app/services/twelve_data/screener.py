import requests
import json
from typing import Dict, List, Optional
from app.core.config import settings
from app.utils.logger import logger
from app.utils.parser import normalize_saudi_symbol

class ScreenerService:
    def __init__(self):
        self.base_url = settings.BASE_URL
        self.api_key = settings.TWELVE_DATA_API_KEY

    def batch_query(self, symbols: List[str], indicators: List[str]) -> Optional[Dict]:
        """Batch query - النسخة المحدثة"""
        try:
            # تطبيع جميع الرموز
            normalized_symbols = [normalize_saudi_symbol(symbol) for symbol in symbols]
            
            symbols_str = ",".join(normalized_symbols)
            indicators_str = ",".join(indicators)
            
            url = f"{self.base_url}/batch"
            params = {
                "symbols": symbols_str,
                "indicators": indicators_str,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Batch query for {len(normalized_symbols)} symbols")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for batch query")
                return None
                
            data = response.json()
            logger.info("✅ Successfully executed batch query")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error in batch query: {e}")
            return None

    def screen_saudi_stocks(self, criteria: Dict) -> Optional[List[Dict]]:
        """تصفية الأسهم السعودية فقط"""
        try:
            # إضافة شرط السعودية للتأكد
            criteria['saudi_only'] = True
            criteria['country'] = 'Saudi Arabia'
            
            logger.info(f"📊 Screening Saudi stocks with criteria: {criteria}")
            
            # يمكن تطوير هذه الدالة للاتصال المباشر بـ Twelve Data إذا كان متوفراً
            # حالياً نستخدم البيانات المحلية
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error screening Saudi stocks: {e}")
            return None