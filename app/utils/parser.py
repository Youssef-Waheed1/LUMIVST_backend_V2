from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.logger import logger

class FinancialDataParser:
    """
    محسن لتحليل البيانات المالية - متكامل مع نظام الكاش
    """
    
    @staticmethod
    def parse_income_statement(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل بيانات قائمة الدخل مع تحسينات للكاش
        """
        try:
            if not data.get("income_statement"):
                logger.warning("لا توجد بيانات قائمة دخل")
                return data
                
            parsed_data = data.copy()
            
            # تحويل التواريخ وتنسيق البيانات
            for statement in parsed_data["income_statement"]:
                # تحويل التواريخ
                if "fiscal_date" in statement:
                    statement["fiscal_date"] = FinancialDataParser._parse_date(statement["fiscal_date"])
                
                # تحويل القيم الرقمية
                FinancialDataParser._parse_numeric_values(statement)
                    
            logger.info(f"تم تحليل {len(parsed_data['income_statement'])} سجل في قائمة الدخل")
            return parsed_data
            
        except Exception as e:
            logger.error(f"خطأ في تحليل قائمة الدخل: {str(e)}")
            return data
    
    @staticmethod
    def parse_balance_sheet(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل بيانات الميزانية العمومية مع تحسينات للكاش
        """
        try:
            if not data.get("balance_sheet"):
                logger.warning("لا توجد بيانات ميزانية عمومية")
                return data
                
            parsed_data = data.copy()
            
            for sheet in parsed_data["balance_sheet"]:
                # تحويل التواريخ
                if "fiscal_date" in sheet:
                    sheet["fiscal_date"] = FinancialDataParser._parse_date(sheet["fiscal_date"])
                
                # تحويل القيم الرقمية في الأقسام المختلفة
                if "assets" in sheet and isinstance(sheet["assets"], dict):
                    FinancialDataParser._parse_numeric_values(sheet["assets"])
                
                if "liabilities" in sheet and isinstance(sheet["liabilities"], dict):
                    FinancialDataParser._parse_numeric_values(sheet["liabilities"])
                
                if "shareholders_equity" in sheet and isinstance(sheet["shareholders_equity"], dict):
                    FinancialDataParser._parse_numeric_values(sheet["shareholders_equity"])
                    
            logger.info(f"تم تحليل {len(parsed_data['balance_sheet'])} سجل في الميزانية العمومية")
            return parsed_data
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الميزانية العمومية: {str(e)}")
            return data
    
    @staticmethod
    def parse_cash_flow(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل بيانات قائمة التدفقات النقدية مع تحسينات للكاش
        """
        try:
            if not data.get("cash_flow"):
                logger.warning("لا توجد بيانات تدفقات نقدية")
                return data
                
            parsed_data = data.copy()
            
            for flow in parsed_data["cash_flow"]:
                # تحويل التواريخ
                if "fiscal_date" in flow:
                    flow["fiscal_date"] = FinancialDataParser._parse_date(flow["fiscal_date"])
                
                # تحويل القيم الرقمية في الأقسام المختلفة
                if "operating_activities" in flow and isinstance(flow["operating_activities"], dict):
                    FinancialDataParser._parse_numeric_values(flow["operating_activities"])
                
                if "investing_activities" in flow and isinstance(flow["investing_activities"], dict):
                    FinancialDataParser._parse_numeric_values(flow["investing_activities"])
                
                if "financing_activities" in flow and isinstance(flow["financing_activities"], dict):
                    FinancialDataParser._parse_numeric_values(flow["financing_activities"])
                
                # تحويل القيم الرقمية المباشرة
                FinancialDataParser._parse_numeric_values(flow)
                    
            logger.info(f"تم تحليل {len(parsed_data['cash_flow'])} سجل في التدفقات النقدية")
            return parsed_data
            
        except Exception as e:
            logger.error(f"خطأ في تحليل قائمة التدفقات النقدية: {str(e)}")
            return data
    
    @staticmethod
    def parse_company_data(company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل بيانات الشركة للتخزين في الكاش
        """
        try:
            parsed_data = company_data.copy()
            
            # تنظيف البيانات الأساسية
            if "symbol" in parsed_data:
                parsed_data["clean_symbol"] = parsed_data["symbol"].split('.')[0].upper()
            
            # تحويل القيم الرقمية إذا وجدت
            FinancialDataParser._parse_numeric_values(parsed_data)
            
            # إضافة timestamp للتخزين
            parsed_data["cached_at"] = datetime.now().isoformat()
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"خطأ في تحليل بيانات الشركة: {str(e)}")
            return company_data
    
    @staticmethod
    def _parse_date(date_str: str) -> str:
        """
        تحويل التاريخ إلى تنسيق مناسب للتخزين في الكاش
        """
        try:
            if not date_str:
                return date_str
                
            # تحويل من YYYY-MM-DD إلى تنسيق مناسب
            if isinstance(date_str, str):
                return datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
            return date_str
        except Exception as e:
            logger.warning(f"تعذر تحويل التاريخ: {date_str}, الخطأ: {e}")
            return date_str
    
    @staticmethod
    def _parse_numeric_values(data_dict: Dict[str, Any]):
        """
        تحويل القيم النصية إلى رقمية عندما يكون ذلك ممكناً
        """
        for key, value in data_dict.items():
            if isinstance(value, str):
                # محاولة تحويل إلى float
                try:
                    # إزالة الفواصل إذا وجدت
                    clean_value = value.replace(',', '')
                    float_value = float(clean_value)
                    data_dict[key] = float_value
                except (ValueError, AttributeError):
                    # إذا فشل التحويل، نترك القيمة كما هي
                    pass
            elif isinstance(value, dict):
                # معالجة القواميس المتداخلة
                FinancialDataParser._parse_numeric_values(value)
    
    @staticmethod
    def prepare_for_cache(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        تحضير البيانات للتخزين في الكاش
        """
        try:
            prepared_data = data.copy()
            
            # إضافة metadata للتخزين
            prepared_data["_cache_metadata"] = {
                "cached_at": datetime.now().isoformat(),
                "data_type": data_type,
                "version": "1.0"
            }
            
            return prepared_data
            
        except Exception as e:
            logger.error(f"خطأ في تحضير البيانات للكاش: {str(e)}")
            return data