import redis
import json
from typing import Optional, Any, List
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

class RedisCache:
    """
    مدير الـ Cache باستخدام Redis - النسخة المحدثة
    """
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # اختبار الاتصال
            self.redis_client.ping()
            print("✅ تم الاتصال بـ Redis بنجاح من utils/cache")
        except Exception as e:
            print(f"❌ فشل الاتصال بـ Redis: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        استرجاع قيمة من الـ Cache
        """
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Error getting cache: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 86400) -> bool:
        """
        حفظ قيمة في الـ Cache
        
        Args:
            key: مفتاح التخزين
            value: القيمة المراد حفظها
            expire: مدة انتهاء الصلاحية بالثواني (24 ساعة افتراضياً)
        """
        if not self.redis_client:
            return False
            
        try:
            serialized = json.dumps(value, default=str)
            if expire:
                self.redis_client.setex(key, expire, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            print(f"Error setting cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        حذف قيمة من الـ Cache
        """
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        التحقق من وجود مفتاح في الـ Cache
        """
        if not self.redis_client:
            return False
        return self.redis_client.exists(key) > 0
    
    def clear_pattern(self, pattern: str) -> int:
        """
        حذف جميع المفاتيح التي تطابق نمط معين
        
        مثال: clear_pattern("company:*") سيحذف كل ما يبدأ بـ company:
        """
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Error clearing cache pattern: {e}")
            return 0
    
    def get_keys(self, pattern: str = "*") -> List[str]:
        """
        الحصول على جميع المفاتيح التي تطابق نمط معين
        """
        if not self.redis_client:
            return []
            
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            print(f"Error getting keys: {e}")
            return []

# إنشاء instance واحد من الـ Cache
cache = RedisCache()

# دوال مساعدة للاستخدام السريع - متوافقة مع النظام الجديد
def get_cached_company(symbol: str) -> Optional[dict]:
    """
    الحصول على بيانات الشركة من الـ Cache
    """
    clean_symbol = symbol.split('.')[0].upper()
    return cache.get(f"companies:symbol:{clean_symbol}")

def cache_company(symbol: str, company_data: dict, expire: int = 86400) -> bool:
    """
    حفظ بيانات الشركة في الـ Cache
    """
    clean_symbol = symbol.split('.')[0].upper()
    return cache.set(
        f"companies:symbol:{clean_symbol}", 
        company_data, 
        expire=expire
    )

def get_cached_companies_list(page: int, limit: int, remove_duplicates: bool) -> Optional[dict]:
    """
    الحصول على قائمة الشركات من الـ Cache
    """
    key = f"companies:page:{page}:limit:{limit}:filter:{remove_duplicates}"
    return cache.get(key)

def cache_companies_list(page: int, limit: int, remove_duplicates: bool, companies_data: dict) -> bool:
    """
    حفظ قائمة الشركات في الـ Cache
    """
    key = f"companies:page:{page}:limit:{limit}:filter:{remove_duplicates}"
    return cache.set(key, companies_data, expire=86400)

def get_cached_financials(symbol: str, data_type: str, period: str, limit: int) -> Optional[dict]:
    """
    الحصول على البيانات المالية من الـ Cache
    """
    clean_symbol = symbol.split('.')[0].upper()
    key = f"financials:{data_type}:{clean_symbol}:{period}:{limit}"
    return cache.get(key)

def cache_financials(symbol: str, data_type: str, period: str, limit: int, financial_data: dict) -> bool:
    """
    حفظ البيانات المالية في الـ Cache
    """
    clean_symbol = symbol.split('.')[0].upper()
    key = f"financials:{data_type}:{clean_symbol}:{period}:{limit}"
    return cache.set(key, financial_data, expire=86400)

def clear_company_cache(symbol: str = None) -> int:
    """
    مسح الـ Cache الخاص بالشركات - متوافق مع النظام الجديد
    """
    if symbol:
        clean_symbol = symbol.split('.')[0].upper()
        count = cache.clear_pattern(f"companies:symbol:{clean_symbol}")
        count += cache.clear_pattern(f"companies:*{clean_symbol}*")
        return count
    else:
        return cache.clear_pattern("companies:*")

def clear_financial_cache(symbol: str = None) -> int:
    """
    مسح الـ Cache الخاص بالبيانات المالية - متوافق مع النظام الجديد
    """
    if symbol:
        clean_symbol = symbol.split('.')[0].upper()
        return cache.clear_pattern(f"financials:*:{clean_symbol}:*")
    else:
        return cache.clear_pattern("financials:*")

def get_cache_stats() -> dict:
    """
    الحصول على إحصائيات الـ Cache
    """
    try:
        company_keys = cache.get_keys("companies:*")
        financial_keys = cache.get_keys("financials:*")
        
        return {
            "total_companies_cache": len(company_keys),
            "total_financials_cache": len(financial_keys),
            "total_cache": len(company_keys) + len(financial_keys),
            "company_patterns": list(set([key.split(':')[1] for key in company_keys if ':' in key])),
            "financial_patterns": list(set([key.split(':')[1] for key in financial_keys if ':' in key]))
        }
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return {}