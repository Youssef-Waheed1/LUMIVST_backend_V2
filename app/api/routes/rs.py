from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.models.rs_daily import RSDaily
from app.schemas.rs import RSResponse, RSLatestResponse
from app.core.limiter import limiter
from fastapi import Request

router = APIRouter(prefix="/rs", tags=["Relative Strength"])

@router.get("/latest", response_model=RSLatestResponse)
@limiter.limit("20/minute")
async def get_latest_rs(
    request: Request,
    min_rs: Optional[int] = Query(None, ge=0, le=99, description="الحد الأدنى لـ RS Rating"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    الحصول على آخر RS Rating لكل الأسهم.
    """
    # 1. معرفة آخر تاريخ متاح
    latest_date_row = db.query(RSDaily.date).order_by(desc(RSDaily.date)).first()
    
    if not latest_date_row:
        return RSLatestResponse(data=[], total_count=0, date=date.today())
    
    latest_date = latest_date_row[0]
    
    # 2. بناء الاستعلام
    query = db.query(RSDaily).filter(RSDaily.date == latest_date)
    
    if min_rs is not None:
        query = query.filter(RSDaily.rs_rating >= min_rs)
    
    # الترتيب حسب RS Rating بشكل افتراضي
    query = query.order_by(desc(RSDaily.rs_rating))
    
    # تنفيذ الاستعلام مع الحد الأقصى
    results = query.limit(limit).all()
    
    return RSLatestResponse(
        data=results,
        total_count=len(results), # This isn't accurate for pagination but fine for simple limit
        date=latest_date
    )

@router.get("/{symbol}", response_model=List[RSResponse])
@limiter.limit("20/minute")
async def get_rs_history(
    request: Request,
    symbol: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    الحصول على تاريخ RS لسهم معين.
    """
    symbol_str = str(symbol).strip()
    
    query = db.query(RSDaily).filter(RSDaily.symbol == symbol_str)
    
    if from_date:
        query = query.filter(RSDaily.date >= from_date)
    if to_date:
        query = query.filter(RSDaily.date <= to_date)
    
    # ترتيب حسب التاريخ
    results = query.order_by(RSDaily.date).all()
    
    return results or []

@router.get("/screener/advanced", response_model=RSLatestResponse)
@limiter.limit("10/minute")
async def advanced_screener(
    request: Request,
    min_rs: int = Query(0, ge=0, le=99),
    min_rank_3m: Optional[int] = Query(None, description="Minimum 3 Month Rank"),
    min_rank_6m: Optional[int] = Query(None, description="Minimum 6 Month Rank"),
    sort_by: str = Query("rs_rating", regex="^(rs_rating|rank_3m|rank_6m|rank_12m|return_3m|return_12m)$"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """
    فلترة متقدمة للأسهم بناءً على الرتب والفترات
    """
    # آخر تاريخ
    latest_date_row = db.query(RSDaily.date).order_by(desc(RSDaily.date)).first()
    if not latest_date_row:
        return RSLatestResponse(data=[], total_count=0, date=date.today())
    
    latest_date = latest_date_row[0]
    
    query = db.query(RSDaily).filter(RSDaily.date == latest_date)
    
    # تطبيق الفلاتر
    if min_rs > 0:
        query = query.filter(RSDaily.rs_rating >= min_rs)
    
    if min_rank_3m is not None:
        query = query.filter(RSDaily.rank_3m >= min_rank_3m)
        
    if min_rank_6m is not None:
        query = query.filter(RSDaily.rank_6m >= min_rank_6m)
    
    # الترتيب
    if hasattr(RSDaily, sort_by):
        col = getattr(RSDaily, sort_by)
        query = query.order_by(desc(col))
    else:
        query = query.order_by(desc(RSDaily.rs_rating))
        
    results = query.limit(limit).all()
    
    return RSLatestResponse(
        data=results,
        total_count=len(results),
        date=latest_date
    )
