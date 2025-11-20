# app/services/cache/technical_indicators_cache.py
from typing import Optional, Dict, Any, List
from datetime import timedelta
from app.core.redis import redis_cache
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicatorsCache:
    def __init__(self):
        self.redis = redis_cache
        self.default_expire = 3600  # 1 hour

    def get_indicator_data_key(self, cache_key: str, indicator: str, interval: str) -> str:
        return f"tech_ind:{cache_key}:{indicator}:{interval}"

    def get_indicators_list_key(self) -> str:
        return "tech_indicators:list"

    async def get_indicator_data(self, cache_key: str, indicator: str, interval: str) -> Optional[Dict[str, Any]]:
        key = self.get_indicator_data_key(cache_key, indicator, interval)
        try:
            data = await self.redis.get(key)
            return data if data else None
        except Exception as e:
            logger.error(f"Error getting indicator data from cache: {e}")
            return None

    async def set_indicator_data(self, cache_key: str, indicator: str, interval: str, 
                               data: Dict[str, Any], expire_minutes: int = 60):
        key = self.get_indicator_data_key(cache_key, indicator, interval)
        expire_seconds = expire_minutes * 60
        try:
            await self.redis.set(key, data, expire=expire_seconds)
        except Exception as e:
            logger.error(f"Error setting indicator data in cache: {e}")

    async def get_indicators_list(self) -> Optional[List[Dict[str, Any]]]:
        try:
            return await self.redis.get(self.get_indicators_list_key())
        except Exception as e:
            logger.error(f"Error getting indicators list from cache: {e}")
            return None

    async def set_indicators_list(self, indicators: List[Dict[str, Any]]):
        try:
            await self.redis.set(self.get_indicators_list_key(), indicators, expire=self.default_expire)
        except Exception as e:
            logger.error(f"Error setting indicators list in cache: {e}")

# Create global instance
technical_indicators_cache = TechnicalIndicatorsCache()