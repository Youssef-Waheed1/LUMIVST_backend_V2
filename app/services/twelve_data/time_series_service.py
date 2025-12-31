import httpx
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from app.core.config import settings

def clean_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

import asyncio
import pandas as pd
import httpx

async def fetch_time_series(
    symbol: str,
    interval: str = "1day",
    outputsize: int = 5000,
    country: str = "Saudi Arabia",
    max_retries: int = 3
) -> pd.DataFrame | None:
    """
    جلب بيانات time series من Twelve Data مع إعادة محاولة ذكية
    في حالة الـ Rate Limit أو أخطاء الشبكة
    """
    clean_sym = clean_symbol(symbol)

    for attempt in range(max_retries):
        try:
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": clean_sym,
                "interval": interval,
                "apikey": settings.API_KEY,
                "country": country,
                "outputsize": outputsize,
                "format": "JSON"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                data = response.json()

            # 1. حالة Rate Limit من Twelve Data
            if isinstance(data, dict) and "code" in data and "API limit" in data.get("message", ""):
                wait_time = 60 * (attempt + 1)  # 60, 120, 180 ثانية
                print(f"API limit hit for {symbol} | المحاولة {attempt + 1}/{max_retries} | ننتظر {wait_time} ثانية...")
                await asyncio.sleep(wait_time)
                continue  # نعيد المحاولة

            # 2. حالة خطأ عادي من الـ API
            if not isinstance(data, dict) or "status" not in data or data["status"] != "ok":
                error_msg = data.get("message", "Unknown error") if isinstance(data, dict) else "Invalid response"
                print(f"خطأ في جلب البيانات لـ {symbol}: {error_msg}")
                return None

            # 3. نجاح الطلب → نعالج البيانات
            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)

            numeric_cols = ["open", "high", "low", "close", "volume"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            print(f"تم جلب بيانات {symbol} بنجاح ({len(df)} صف)")
            return df

        except httpx.RequestError as e:
            print(f"فشل في الاتصال لـ {symbol} (محاولة {attempt + 1}): {e}")
        except Exception as e:
            print(f"استثناء غير متوقع لـ {symbol} (محاولة {attempt + 1}): {e}")

        # إذا كانت آخر محاولة → نخرج
        if attempt == max_retries - 1:
            print(f"فشل نهائي في جلب بيانات {symbol} بعد {max_retries} محاولات")
            return None

        # انتظار تصاعدي قبل المحاولة التالية (للأخطاء العادية)
        wait_time = 5 * (attempt + 1)  # 5, 10, 15 ثانية
        print(f"ننتظر {wait_time} ثانية قبل المحاولة التالية...")
        await asyncio.sleep(wait_time)

    return None  # لن يصل هنا فعليًا لكن للتوثيق

def calculate_period_change(df: pd.DataFrame, days: int) -> Optional[float]:
    """
    حساب Change% لفترة معينة من البيانات
    """
    try:
        if df is None or len(df) < days:
            return None
            
        # أخذ آخر N يوم
        recent_data = df.tail(days)
        
        if len(recent_data) < 2:
            return None
            
        # السعر قبل N يوم
        old_price = recent_data.iloc[0]["close"]
        # السعر الحالي
        new_price = recent_data.iloc[-1]["close"]
        
        if pd.isna(old_price) or pd.isna(new_price) or old_price == 0:
            return None
            
        change_percent = ((new_price - old_price) / old_price) * 100
        return change_percent
        
    except Exception as e:
        print(f"❌ Error calculating {days}d change: {str(e)}")
        return None