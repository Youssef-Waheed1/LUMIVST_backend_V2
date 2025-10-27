from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.company import Company
from app.models.screener import ScreenerFilter, ScreenerResult
from app.schemas.screener import (
    ScreenerFilter as ScreenerFilterSchema,
    ScreenerFilterCreate,
    ScreenerFilterUpdate,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerResultsList
)
from app.services.twelve_data.screener import ScreenerService
from app.utils.logger import logger

router = APIRouter()
screener_service = ScreenerService()

@router.post("/screener/filter", response_model=ScreenerResultsList)
async def filter_companies(
    request: ScreenerRequest,
    saudi_only: bool = Query(False, description="Filter Saudi companies only"),
    db: Session = Depends(get_db)
):
    """تصفية الأسهم بناء على معايير محددة"""
    try:
        # بناء query أساسية
        query = db.query(Company)

        if saudi_only:
            query = query.filter(
                Company.symbol.like('%.SR') | 
                Company.symbol.like('%.SA') |
                Company.country.in_(["SA", "Saudi Arabia"]) |
                Company.exchange == "Tadawul"   
            )     
        
        # تطبيق الفلاتر على البيانات الموجودة في DB
        if request.min_market_cap:
            query = query.filter(Company.market_cap >= request.min_market_cap)
        if request.max_market_cap:
            query = query.filter(Company.market_cap <= request.max_market_cap)
        if request.sector:
            query = query.filter(Company.sector == request.sector)
        if request.industry:
            query = query.filter(Company.industry == request.industry)
        
        companies = query.order_by(Company.market_cap.desc()).all()
        
        # تحويل النتائج إلى نموذج الاستجابة
        results = []
        for company in companies:
            result = ScreenerResponse(
                symbol=company.symbol,
                name=company.name,
                sector=company.sector,
                industry=company.industry,
                market_cap=company.market_cap,
                match_score=calculate_match_score(company, request)  # حساب درجة التوافق
            )
            results.append(result)
        
        return ScreenerResultsList(
            results=results,
            total=len(results),
            filter_criteria=request
        )
        
    except Exception as e:
        logger.error(f"Error filtering companies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def calculate_match_score(company: Company, criteria: ScreenerRequest) -> float:
    """حساب درجة التوافق مع معايير البحث"""
    score = 1.0  # درجة أساسية
    
    # يمكن إضافة منطق أكثر تعقيداً لحساب الدرجة
    # بناء على مدى توافق الشركة مع المعايير
    
    return score

@router.get("/screener/filters", response_model=List[ScreenerFilterSchema])
async def get_saved_filters(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """الحصول على الفلاتر المحفوظة"""
    try:
        filters = db.query(ScreenerFilter).filter(
            ScreenerFilter.is_active == True
        ).offset(skip).limit(limit).all()
        
        return filters
        
    except Exception as e:
        logger.error(f"Error fetching saved filters: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/screener/filters", response_model=ScreenerFilterSchema)
async def create_filter(
    filter_data: ScreenerFilterCreate,
    db: Session = Depends(get_db)
):
    """إنشاء فلتر جديد"""
    try:
        filter_obj = ScreenerFilter(**filter_data.dict())
        db.add(filter_obj)
        db.commit()
        db.refresh(filter_obj)
        
        logger.info(f"Successfully created filter: {filter_obj.name}")
        return filter_obj
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating filter: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/screener/filters/{filter_id}", response_model=ScreenerFilterSchema)
async def update_filter(
    filter_id: str,
    filter_data: ScreenerFilterUpdate,
    db: Session = Depends(get_db)
):
    """تحديث فلتر موجود"""
    try:
        filter_obj = db.query(ScreenerFilter).filter(ScreenerFilter.id == filter_id).first()
        
        if not filter_obj:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        # تحديث الحقول المقدمة فقط
        update_data = filter_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:  # تحديث الحقول الغير None فقط
                setattr(filter_obj, field, value)
        
        db.commit()
        db.refresh(filter_obj)
        
        logger.info(f"Successfully updated filter: {filter_obj.name}")
        return filter_obj
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating filter: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/screener/filters/{filter_id}")
async def delete_filter(
    filter_id: str,
    db: Session = Depends(get_db)
):
    """حذف فلتر (تعطيله)"""
    try:
        filter_obj = db.query(ScreenerFilter).filter(ScreenerFilter.id == filter_id).first()
        
        if not filter_obj:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        filter_obj.is_active = False
        db.commit()
        
        logger.info(f"Successfully deleted filter: {filter_obj.name}")
        return {"message": "Filter deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting filter: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")