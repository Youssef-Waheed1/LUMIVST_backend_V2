from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.financials import IncomeStatement, BalanceSheet, CashFlow
from typing import List, Dict, Any, Optional
from datetime import datetime

class FinancialRepository:
    def __init__(self, db: Session):
        self.db = db

    # Income Statement Operations مع البلد
    async def get_income_statement(self, symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6) -> List[IncomeStatement]:
        query = self.db.query(IncomeStatement).filter(
            IncomeStatement.symbol == symbol,
            IncomeStatement.country == country
        )
        
        if period == "quarterly":
            query = query.filter(IncomeStatement.quarter.isnot(None))
        else:
            query = query.filter(IncomeStatement.quarter.is_(None))
            
        return query.order_by(desc(IncomeStatement.fiscal_date)).limit(limit).all()

    async def save_income_statement(self, symbol: str, country: str, income_data: Dict[str, Any]) -> IncomeStatement:
        # استخراج الحقول المعروفة فقط
        known_fields = {k: v for k, v in income_data.items() if hasattr(IncomeStatement, k)}
        
        # تخزين البيانات الإضافية في حقل additional_data
        additional_data = {k: v for k, v in income_data.items() if not hasattr(IncomeStatement, k)}
        
        existing = self.db.query(IncomeStatement).filter(
            IncomeStatement.symbol == symbol,
            IncomeStatement.country == country,
            IncomeStatement.fiscal_date == income_data.get('fiscal_date')
        ).first()
        
        if existing:
            # تحديث البيانات الموجودة
            for key, value in known_fields.items():
                setattr(existing, key, value)
            if additional_data:
                existing.additional_data = additional_data
            existing.updated_at = datetime.utcnow()
        else:
            # إنشاء سجل جديد
            existing = IncomeStatement(
                symbol=symbol, 
                country=country, 
                **known_fields,
                additional_data=additional_data if additional_data else None
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing

    async def save_bulk_income_statements(self, symbol: str, country: str, income_list: List[Dict[str, Any]]) -> List[IncomeStatement]:
        saved_records = []
        for income_data in income_list:
            record = await self.save_income_statement(symbol, country, income_data)
            saved_records.append(record)
        return saved_records

    # Balance Sheet Operations مع البلد
    # Balance Sheet Operations مع البلد
    async def get_balance_sheet(self, symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6) -> List[BalanceSheet]:
        query = self.db.query(BalanceSheet).filter(
            BalanceSheet.symbol == symbol,
            BalanceSheet.country == country
        )
        
        # ✅ أضف هذا الـ filter المفقود
        if period == "quarterly":
            query = query.filter(BalanceSheet.quarter.isnot(None))
        else:
            query = query.filter(BalanceSheet.quarter.is_(None))
            
        return query.order_by(desc(BalanceSheet.fiscal_date)).limit(limit).all()

    async def save_balance_sheet(self, symbol: str, country: str, balance_data: Dict[str, Any]) -> BalanceSheet:
        # استخراج الحقول المعروفة فقط
        known_fields = {k: v for k, v in balance_data.items() if hasattr(BalanceSheet, k)}
        
        # تخزين البيانات الإضافية في حقل additional_data
        additional_data = {k: v for k, v in balance_data.items() if not hasattr(BalanceSheet, k)}
        
        existing = self.db.query(BalanceSheet).filter(
            BalanceSheet.symbol == symbol,
            BalanceSheet.country == country,
            BalanceSheet.fiscal_date == balance_data.get('fiscal_date')
        ).first()
        
        if existing:
            # تحديث البيانات الموجودة
            for key, value in known_fields.items():
                setattr(existing, key, value)
            if additional_data:
                existing.additional_data = additional_data
            existing.updated_at = datetime.utcnow()
        else:
            # إنشاء سجل جديد
            existing = BalanceSheet(
                symbol=symbol, 
                country=country, 
                **known_fields,
                additional_data=additional_data if additional_data else None
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing

    async def save_bulk_balance_sheets(self, symbol: str, country: str, balance_list: List[Dict[str, Any]]) -> List[BalanceSheet]:
        saved_records = []
        for balance_data in balance_list:
            record = await self.save_balance_sheet(symbol, country, balance_data)
            saved_records.append(record)
        return saved_records

    # Cash Flow Operations مع البلد
    async def get_cash_flow(self, symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6) -> List[CashFlow]:
        query = self.db.query(CashFlow).filter(
            CashFlow.symbol == symbol,
            CashFlow.country == country
        )
        
        if period == "quarterly":
            query = query.filter(CashFlow.quarter.isnot(None))
        else:
            query = query.filter(CashFlow.quarter.is_(None))
            
        return query.order_by(desc(CashFlow.fiscal_date)).limit(limit).all()

    async def save_cash_flow(self, symbol: str, country: str, cash_flow_data: Dict[str, Any]) -> CashFlow:
        # استخراج الحقول المعروفة فقط
        known_fields = {k: v for k, v in cash_flow_data.items() if hasattr(CashFlow, k)}
        
        # تخزين البيانات الإضافية في حقل additional_data
        additional_data = {k: v for k, v in cash_flow_data.items() if not hasattr(CashFlow, k)}
        
        existing = self.db.query(CashFlow).filter(
            CashFlow.symbol == symbol,
            CashFlow.country == country,
            CashFlow.fiscal_date == cash_flow_data.get('fiscal_date')
        ).first()
        
        if existing:
            # تحديث البيانات الموجودة
            for key, value in known_fields.items():
                setattr(existing, key, value)
            if additional_data:
                existing.additional_data = additional_data
            existing.updated_at = datetime.utcnow()
        else:
            # إنشاء سجل جديد
            existing = CashFlow(
                symbol=symbol, 
                country=country, 
                **known_fields,
                additional_data=additional_data if additional_data else None
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing

    async def save_bulk_cash_flows(self, symbol: str, country: str, cash_flow_list: List[Dict[str, Any]]) -> List[CashFlow]:
        saved_records = []
        for cash_flow_data in cash_flow_list:
            record = await self.save_cash_flow(symbol, country, cash_flow_data)
            saved_records.append(record)
        return saved_records

    # Utility Methods مع البلد
    async def symbol_has_financial_data(self, symbol: str, country: str = "Saudi Arabia") -> bool:
        """التحقق من وجود أي بيانات مالية للرمز في البلد"""
        income_exists = self.db.query(IncomeStatement).filter(
            IncomeStatement.symbol == symbol,
            IncomeStatement.country == country
        ).first()
        
        balance_exists = self.db.query(BalanceSheet).filter(
            BalanceSheet.symbol == symbol,
            BalanceSheet.country == country
        ).first()
        
        cash_flow_exists = self.db.query(CashFlow).filter(
            CashFlow.symbol == symbol,
            CashFlow.country == country
        ).first()
        
        return any([income_exists, balance_exists, cash_flow_exists])

    async def delete_financial_data(self, symbol: str, country: str = "Saudi Arabia"):
        """حذف جميع البيانات المالية للرمز في البلد"""
        self.db.query(IncomeStatement).filter(
            IncomeStatement.symbol == symbol,
            IncomeStatement.country == country
        ).delete()
        
        self.db.query(BalanceSheet).filter(
            BalanceSheet.symbol == symbol,
            BalanceSheet.country == country
        ).delete()
        
        self.db.query(CashFlow).filter(
            CashFlow.symbol == symbol,
            CashFlow.country == country
        ).delete()
        
        self.db.commit()