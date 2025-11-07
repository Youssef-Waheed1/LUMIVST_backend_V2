import redis.asyncio as redis
import os
import json
from typing import Any, Optional, List
from app.core.config import REDIS_URL  # ⭐ استيراد من config

class RedisCache:
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
    
    async def init_redis(self):
        """تهيئة اتصال Redis"""
        try:
            # استخدام REDIS_URL من الإعدادات
            self.redis_client = redis.from_url(
                REDIS_URL,  # ⭐ استخدام المتغير من config
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # اختبار الاتصال
            await self.redis_client.ping()
            self.is_connected = True
            print(f"✅ تم الاتصال بـ Redis بنجاح: {REDIS_URL}")
            return True
        except Exception as e:
            print(f"❌ فشل الاتصال بـ Redis: {e}")
            self.redis_client = None
            self.is_connected = False
            return False

    # باقي الدوال تبقى كما هي...
    async def ensure_connection(self):
        if not self.is_connected or not self.redis_client:
            return await self.init_redis()
        return True
    
    async def set(self, key: str, value: Any, expire: int = 86400) -> bool:
        """تخزين بيانات في الكاش لمدة 24 ساعة افتراضياً"""
        if not await self.ensure_connection():
            return False
            
        try:
            # تأكد من تحويل جميع القيم إلى JSON string
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized_value = str(value)
            
            result = await self.redis_client.set(key, serialized_value, ex=expire)
            return result
        except Exception as e:
            print(f"❌ خطأ في تخزين الكاش للمفتاح {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """جلب بيانات من الكاش"""
        if not await self.ensure_connection():
            return None
            
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None
                
            # حاول تحليل JSON أولاً
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # إذا فشل التحليل، ارجع القيمة كما هي
                return value
                
        except Exception as e:
            print(f"❌ خطأ في جلب الكاش للمفتاح {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """حذف بيانات من الكاش"""
        if not await self.ensure_connection():
            return False
            
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"❌ خطأ في حذف الكاش للمفتاح {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """التحقق من وجود مفتاح في الكاش"""
        if not await self.ensure_connection():
            return False
            
        try:
            return await self.redis_client.exists(key) == 1
        except Exception as e:
            print(f"❌ خطأ في التحقق من الكاش للمفتاح {key}: {e}")
            return False
    
    async def flush_all(self) -> bool:
        """مسح كل الكاش"""
        if not await self.ensure_connection():
            return False
            
        try:
            await self.redis_client.flushall()
            print("✅ تم مسح كل الكاش")
            return True
        except Exception as e:
            print(f"❌ خطأ في مسح الكاش: {e}")
            return False

    async def keys(self, pattern: str) -> List[str]:
        """الحصول على جميع المفاتيح التي تطابق النمط"""
        if not await self.ensure_connection():
            print("❌ Redis غير متصل")
            return []  # إرجاع قائمة فارغة بدلاً من None
        
        try:
            keys = await self.redis_client.keys(pattern)
            return keys or []  # ✅ إرجاع قائمة فارغة إذا كانت None
        except Exception as e:
            print(f"❌ خطأ في جلب المفاتيح للنمط {pattern}: {e}")
            return []  # ✅ إرجاع قائمة فارغة بدلاً من None

    async def scan_iter(self, pattern: str):
        """استخدام SCAN للحصول على المفاتيح (أفضل للأداء)"""
        if not await self.ensure_connection():
            return []
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except Exception as e:
            print(f"❌ خطأ في SCAN للنمط {pattern}: {e}")
            return []

# إنشاء نسخة عامة
redis_cache = RedisCache()