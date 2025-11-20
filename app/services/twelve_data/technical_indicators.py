# app/services/twelve_data/technical_indicators_service.py
import httpx
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicatorsService:
    def __init__(self, api_key: str, base_url: str = "https://api.twelvedata.com"):
        self.base_url = base_url
        self.api_key = api_key

    async def get_technical_indicators_list(self) -> Dict[str, Any]:
        """Get list of all available technical indicators"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/technical_indicators"
                params = {"apikey": self.api_key}
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # ✅ تحويل البيانات من الشكل الجديد إلى الشكل المتوقع
                transformed_indicators = []
                
                if data.get('status') == 'ok' and 'data' in data:
                    for indicator_key, indicator_data in data['data'].items():
                        if indicator_data.get('enable', False):
                            transformed_indicators.append({
                                "name": indicator_key,
                                "display_name": indicator_data.get('full_name', indicator_key),
                                "description": indicator_data.get('description', ''),
                                "category": indicator_data.get('type', 'Other Indicators'),
                                "is_overlay": indicator_data.get('overlay', False),
                                "parameters": indicator_data.get('parameters', {}),
                                "output_values": indicator_data.get('output_values', {}),
                                "tinting": indicator_data.get('tinting', {})
                            })
                
                return {
                    "technical_indicators": transformed_indicators,
                    "status": "ok"
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching technical indicators: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching technical indicators: {e}")
            raise

    async def get_indicator_data(self, symbol: str, interval: str, indicator: str, 
                               exchange: str = "TADAWUL", **parameters) -> Dict[str, Any]:
        """Get technical indicator data for a symbol"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/{indicator}"
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "exchange": exchange,
                    "apikey": self.api_key,
                    "outputsize": parameters.pop('outputsize', 100)
                }
                params.update(parameters)
                
                logger.info(f"Fetching {indicator} for {symbol} with params: {params}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # ✅ إصلاح الـ meta إذا كان فيه خطأ في اسم المؤشر
                if data.get('meta') and data['meta'].get('indicator'):
                    if data['meta']['indicator'].get('name') != indicator:
                        print(f"⚠️ تصحيح اسم المؤشر في الـ meta: {data['meta']['indicator'].get('name')} -> {indicator}")
                        data['meta']['indicator']['name'] = indicator
                
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {indicator} for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {indicator} for {symbol}: {e}")
            raise

    async def get_multiple_indicators(self, symbol: str, interval: str, 
                                    indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get multiple technical indicators in one request"""
        tasks = []
        for indicator_config in indicators:
            task = self.get_indicator_data(
                symbol=symbol,
                interval=interval,
                indicator=indicator_config['name'],
                **indicator_config.get('parameters', {})
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = {}
        for i, result in enumerate(results):
            indicator_name = indicators[i]['name']
            if isinstance(result, Exception):
                logger.error(f"Error fetching {indicator_name}: {result}")
                processed_results[indicator_name] = {"error": str(result)}
            else:
                processed_results[indicator_name] = result
        
        return processed_results


    def _process_tinting_data(self, indicator_data: Dict[str, Any]) -> Dict[str, Any]:
        """معالجة بيانات الـ tinting باستخدام البيانات الحقيقية من API"""
        indicator_name = indicator_data.get('name', '')
        
        # ✅ نستخدم البيانات الحقيقية من API إذا موجودة، وإلا نستخدم افتراضيات ذكية
        original_tinting = indicator_data.get('tinting', {})
        
        if original_tinting:
            # إذا في tinting من API، نستخدمه ونضيف parameters فقط
            tinting = original_tinting.copy()
        else:
            # إذا مفيش tinting من API، ننشئ واحد ذكي بناءً على نوع المؤشر
            tinting = self._create_smart_tinting(indicator_data)
        
        return tinting

    def _create_smart_tinting(self, indicator_data: Dict[str, Any]) -> Dict[str, Any]:
        """إنشاء tinting ذكي بناءً على خصائص المؤشر"""
        indicator_name = indicator_data.get('name', '')
        category = indicator_data.get('type', '')
        output_values = indicator_data.get('output_values', {})
        
        # إعدادات افتراضية ذكية بناءً على نوع المؤشر
        base_tinting = {
            "display": "fill",
            "color": "#FF0000",
            "transparency": 0.5,
            "lower_bound": "0",
            "upper_bound": indicator_name
        }
        
        # تخصيص بناءً على نوع المؤشر
        if indicator_name in ['rsi', 'stoch', 'williams_r']:
            base_tinting.update({
                "lower_bound": "20",
                "upper_bound": "80",
                "color": "#FF6B6B",
                "display": "fill"
            })
        elif indicator_name in ['bollinger_upper', 'bollinger_lower']:
            base_tinting.update({
                "display": "line",
                "color": "#45B7D1"
            })
        elif 'volume' in indicator_name.lower():
            base_tinting.update({
                "display": "histogram",
                "color": "#4ECDC4"
            })
        elif category == 'Momentum Indicators':
            base_tinting.update({
                "color": "#FFA500",
                "lower_bound": "-1",
                "upper_bound": "1"
            })
        
        return base_tinting

    def _transform_output_values(self, original_output: Dict[str, Any]) -> Dict[str, Any]:
        """تحويل output_values مع الحفاظ على البيانات الأصلية"""
        transformed = {}
        
        for key, value in original_output.items():
            # ✅ نحافظ على البيانات الأصلية ونضيف القيم الناقصة فقط
            transformed_value = {
                "default_color": value.get("default_color", "#FF0000"),
                "display": value.get("display", "line"),
                "min_range": value.get("min_range", 0),
                "max_range": value.get("max_range", 5)
            }
            
            # نحافظ على أي بيانات إضافية موجودة في الأصل
            for extra_key, extra_value in value.items():
                if extra_key not in transformed_value:
                    transformed_value[extra_key] = extra_value
            
            transformed[key] = transformed_value
        
        return transformed

    def _transform_parameters(self, original_params: Dict[str, Any]) -> Dict[str, Any]:
        """تحويل parameters مع الحفاظ على البيانات الأصلية"""
        transformed = {}
        
        for key, value in original_params.items():
            # ✅ نحافظ على البيانات الأصلية ونضيف القيم الناقصة فقط
            transformed_value = {
                "default": value.get("default", 12),
                "max_range": value.get("max_range", 1),
                "min_range": value.get("min_range", 1),
                "range": value.get("range", ["open", "high", "low", "close"]),
                "type": value.get("type", "int")
            }
            
            # نحافظ على أي بيانات إضافية موجودة في الأصل
            for extra_key, extra_value in value.items():
                if extra_key not in transformed_value:
                    transformed_value[extra_key] = extra_value
            
            transformed[key] = transformed_value
        
        return transformed




























# import httpx
# from typing import Dict, Any, Optional, List
# import asyncio
# from datetime import datetime
# import logging

# logger = logging.getLogger(__name__)

# class TechnicalIndicatorsService:
#     def __init__(self, api_key: str, base_url: str = "https://api.twelvedata.com"):
#         self.base_url = base_url
#         self.api_key = api_key

#     async def get_technical_indicators_list(self) -> Dict[str, Any]:
#         """Get list of all available technical indicators"""
#         try:
#             async with httpx.AsyncClient(timeout=30.0) as client:
#                 url = f"{self.base_url}/technical_indicators"
#                 params = {"apikey": self.api_key}
                
#                 response = await client.get(url, params=params)
#                 response.raise_for_status()
#                 return response.json()
                
#         except httpx.HTTPStatusError as e:
#             logger.error(f"HTTP error fetching technical indicators: {e}")
#             raise
#         except Exception as e:
#             logger.error(f"Error fetching technical indicators: {e}")
#             raise

#     async def get_indicator_data(self, symbol: str, interval: str, indicator: str, 
#                                **parameters) -> Dict[str, Any]:
#         """Get technical indicator data for a symbol"""
#         try:
#             async with httpx.AsyncClient(timeout=30.0) as client:
#                 url = f"{self.base_url}/{indicator}"
#                 params = {
#                     "symbol": symbol,
#                     "interval": interval,
#                     "apikey": self.api_key,
#                     "outputsize": parameters.pop('outputsize', 100)
#                 }
#                 params.update(parameters)
                
#                 logger.info(f"Fetching {indicator} for {symbol} with params: {params}")
#                 response = await client.get(url, params=params)
#                 response.raise_for_status()
                
#                 data = response.json()
#                                 # ✅ إصلاح الـ meta إذا كان فيه خطأ في اسم المؤشر
#                 if data.get('meta') and data['meta'].get('indicator'):
#                     if data['meta']['indicator'].get('name') != indicator:
#                         print(f"⚠️ تصحيح اسم المؤشر في الـ meta: {data['meta']['indicator'].get('name')} -> {indicator}")
#                         data['meta']['indicator']['name'] = indicator
                
#                 return data
                
#         except httpx.HTTPStatusError as e:
#             logger.error(f"HTTP error fetching {indicator} for {symbol}: {e}")
#             raise
#         except Exception as e:
#             logger.error(f"Error fetching {indicator} for {symbol}: {e}")
#             raise

#     async def get_multiple_indicators(self, symbol: str, interval: str, 
#                                     indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
#         """Get multiple technical indicators in one request"""
#         tasks = []
#         for indicator_config in indicators:
#             task = self.get_indicator_data(
#                 symbol=symbol,
#                 interval=interval,
#                 indicator=indicator_config['name'],
#                 **indicator_config.get('parameters', {})
#             )
#             tasks.append(task)
        
#         results = await asyncio.gather(*tasks, return_exceptions=True)
        
#         processed_results = {}
#         for i, result in enumerate(results):
#             indicator_name = indicators[i]['name']
#             if isinstance(result, Exception):
#                 logger.error(f"Error fetching {indicator_name}: {result}")
#                 processed_results[indicator_name] = {"error": str(result)}
#             else:
#                 processed_results[indicator_name] = result
        
#         return processed_results

#     def transform_indicator_data(self, raw_data: Dict[str, Any], indicator_name: str) -> List[Dict[str, Any]]:
#         """Transform raw indicator data to our format"""
#         transformed_data = []
        
#         if 'values' in raw_data:
#             for item in raw_data['values']:
#                 if 'datetime' in item:
#                     try:
#                         # Parse datetime
#                         date = datetime.fromisoformat(item['datetime'].replace('Z', '+00:00'))
                        
#                         # Extract values (excluding datetime)
#                         values = {k: float(v) if v is not None else None 
#                                  for k, v in item.items() if k != 'datetime' and v is not None}
                        
#                         transformed_data.append({
#                             "date": date,
#                             "values": values
#                         })
#                     except (ValueError, TypeError) as e:
#                         logger.warning(f"Error parsing data point for {indicator_name}: {e}")
#                         continue
        
#         return transformed_data