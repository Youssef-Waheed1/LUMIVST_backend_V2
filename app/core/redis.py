import redis.asyncio as redis
import os
import json
from typing import Any, Optional

class RedisCache:
    def __init__(self):
        self.redis_client = None
    
    async def init_redis(self):
        """تهيئة اتصال Redis"""
        try:
            # قراءة رابط الاتصال من متغير البيئة
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

            # إنشاء الاتصال من URL
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # اختبار الاتصال
            await self.redis_client.ping()
            print("✅ تم الاتصال بـ Redis بنجاح")
            return True
        except Exception as e:
            print(f"❌ فشل الاتصال بـ Redis: {e}")
            self.redis_client = None
            return False

    
    async def set(self, key: str, value: Any, expire: int = 86400) -> bool:
        """تخزين بيانات في الكاش لمدة 24 ساعة افتراضياً"""
        if not self.redis_client:
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
        if not self.redis_client:
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
        if not self.redis_client:
            return False
            
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"❌ خطأ في حذف الكاش للمفتاح {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """التحقق من وجود مفتاح في الكاش"""
        if not self.redis_client:
            return False
            
        try:
            return await self.redis_client.exists(key) == 1
        except Exception as e:
            print(f"❌ خطأ في التحقق من الكاش للمفتاح {key}: {e}")
            return False
    
    async def flush_all(self) -> bool:
        """مسح كل الكاش"""
        if not self.redis_client:
            return False
            
        try:
            await self.redis_client.flushall()
            print("✅ تم مسح كل الكاش")
            return True
        except Exception as e:
            print(f"❌ خطأ في مسح الكاش: {e}")
            return False

# إنشاء نسخة عامة
redis_cache = RedisCache()