import requests
import json
from typing import Dict, List, Optional
from app.core.config import settings
from app.utils.logger import logger
from app.utils.parser import normalize_saudi_symbol, is_saudi_symbol

class TechnicalsService:
    def __init__(self):
        self.base_url = settings.BASE_URL
        self.api_key = settings.TWELVE_DATA_API_KEY

    def get_time_series(self, symbol: str, interval: str = "1day", 
                       output_size: int = 100) -> Optional[Dict]:
        """بيانات time series - النسخة المحدثة"""
        try:
            normalized_symbol = normalize_saudi_symbol(symbol)
            
            url = f"{self.base_url}/time_series"
            params = {
                "symbol": normalized_symbol,
                "interval": interval,
                "outputsize": output_size,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Fetching time series for: {normalized_symbol}, interval: {interval}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for time series: {normalized_symbol}")
                return None
                
            data = response.json()
            logger.info(f"✅ Successfully fetched time series for: {normalized_symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching time series for {symbol}: {e}")
            return None

    def get_technical_indicator(self, symbol: str, indicator: str, 
                               interval: str = "1day", 
                               time_period: int = 14) -> Optional[Dict]:
        """المؤشرات الفنية - النسخة المحدثة"""
        try:
            normalized_symbol = normalize_saudi_symbol(symbol)
            
            url = f"{self.base_url}/{indicator.lower()}"
            params = {
                "symbol": normalized_symbol,
                "interval": interval,
                "time_period": time_period,
                "apikey": self.api_key
            }
            
            logger.info(f"📊 Fetching {indicator} for: {normalized_symbol}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ HTTP {response.status_code} for {indicator}: {normalized_symbol}")
                return None
                
            data = response.json()
            logger.info(f"✅ Successfully fetched {indicator} for: {normalized_symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching {indicator} for {symbol}: {e}")
            return None

    # الدوال المساعدة المتبقية كما هي...
    def get_rsi(self, symbol: str, interval: str = "1day", time_period: int = 14) -> Optional[Dict]:
        return self.get_technical_indicator(symbol, "rsi", interval, time_period)

    def get_macd(self, symbol: str, interval: str = "1day") -> Optional[Dict]:
        return self.get_technical_indicator(symbol, "macd", interval)

    def get_sma(self, symbol: str, interval: str = "1day", time_period: int = 20) -> Optional[Dict]:
        return self.get_technical_indicator(symbol, "sma", interval, time_period)

    def get_saudi_technicals(self, symbol: str, indicator: str, **kwargs) -> Optional[Dict]:
        """المؤشرات الفنية للأسهم السعودية فقط"""
        if not is_saudi_symbol(symbol):
            logger.warning(f"⚠️ Symbol {symbol} is not a Saudi symbol")
            return None
        return self.get_technical_indicator(symbol, indicator, **kwargs)