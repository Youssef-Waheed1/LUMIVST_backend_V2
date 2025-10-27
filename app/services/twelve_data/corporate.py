import requests
import json
from typing import Dict, List, Optional
from app.core.config import settings
from app.utils.logger import logger
from app.utils.parser import normalize_saudi_symbol, is_saudi_symbol

class CorporateService:
    def __init__(self):
        self.base_url = settings.BASE_URL
        self.api_key = settings.TWELVE_DATA_API_KEY

    def get_dividends(self, symbol: str) -> Optional[Dict]:
        """توزيعات الأرباح - النسخة المحدثة"""
        try:
            # استخدام الدالة الجديدة لتطبيع الرمز
            normalized_symbol = normalize_saudi_symbol(symbol)
            
            url = f"{self.base_url}/dividends"
            params = {
                "symbol": normalized_symbol,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Fetching dividends for: {normalized_symbol}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for dividends: {normalized_symbol}")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Successfully fetched dividends for: {normalized_symbol}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching dividends for {symbol}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error for dividends {symbol}: {e}")
            return None

    def get_splits(self, symbol: str) -> Optional[Dict]:
        """تقسيم الأسهم - النسخة المحدثة"""
        try:
            normalized_symbol = normalize_saudi_symbol(symbol)
            
            url = f"{self.base_url}/splits"
            params = {
                "symbol": normalized_symbol,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Fetching splits for: {normalized_symbol}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for splits: {normalized_symbol}")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Successfully fetched splits for: {normalized_symbol}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching splits for {symbol}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error for splits {symbol}: {e}")
            return None

    def get_ipo_calendar(self, country: str = None) -> Optional[Dict]:
        """الطروحات الأولية - مع دعم الفلترة بالبلد"""
        try:
            url = f"{self.base_url}/ipo_calendar"
            params = {
                "apikey": self.api_key
            }
            
            # إضافة فلترة البلد إذا كانت محددة
            if country:
                params["country"] = country
            
            logger.info(f"📊 Fetching IPO calendar for country: {country}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for IPO calendar")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            logger.info("✅ Successfully fetched IPO calendar")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching IPO calendar: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error for IPO calendar: {e}")
            return None

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """تصنيفات الشركات - النسخة المحدثة"""
        try:
            normalized_symbol = normalize_saudi_symbol(symbol)
            
            url = f"{self.base_url}/profile"
            params = {
                "symbol": normalized_symbol,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Fetching profile for: {normalized_symbol}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for profile: {normalized_symbol}")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Successfully fetched profile for: {normalized_symbol}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching profile for {symbol}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error for profile {symbol}: {e}")
            return None

    def get_saudi_dividends(self, symbol: str) -> Optional[Dict]:
        """توزيعات الأرباح للأسهم السعودية فقط"""
        if not is_saudi_symbol(symbol):
            logger.warning(f"⚠️ Symbol {symbol} is not a Saudi symbol")
            return None
        return self.get_dividends(symbol)

    def get_saudi_splits(self, symbol: str) -> Optional[Dict]:
        """تقسيم الأسهم للأسهم السعودية فقط"""
        if not is_saudi_symbol(symbol):
            logger.warning(f"⚠️ Symbol {symbol} is not a Saudi symbol")
            return None
        return self.get_splits(symbol)