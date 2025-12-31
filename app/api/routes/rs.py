from fastapi import APIRouter, Depends, HTTPException, Query
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
    min_rs: Optional[float] = Query(None, ge=0, le=100, description="الحد الأدنى لـ RS"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    الحصول على آخر RS لكل الأسهم.
    يستخدم لعرض جدول الترتيب (Screener)
    """
    # 1. معرفة آخر تاريخ متاح
    latest_date_row = db.query(RSDaily.date).order_by(desc(RSDaily.date)).first()
    
    if not latest_date_row:
        return RSLatestResponse(data=[], total_count=0, date=date.today())
    
    latest_date = latest_date_row[0]
    
    # 2. بناء الاستعلام
    query = db.query(RSDaily).filter(RSDaily.date == latest_date)
    
    if min_rs is not None:
        query = query.filter(RSDaily.rs_percentile >= min_rs)
    
    # الترتيب حسب RS بشكل افتراضي
    query = query.order_by(desc(RSDaily.rs_percentile))
    
    # تنفيذ الاستعلام
    results = query.all()
    
    # جلب أسماء الشركات من ملف CSV للمصداقية الكاملة
    import csv
    from pathlib import Path
    company_names = {}
    csv_path = Path(__file__).resolve().parent.parent.parent.parent / "company_symbols.csv"
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get('Symbol', '').strip()
                name = row.get('Company', '').strip()
                if sym and name:
                    company_names[sym] = name
        print(f"DEBUG: Loaded {len(company_names)} names from CSV")
    except Exception as e:
        print(f"DEBUG: Failed to load CSV names: {e}")

    # حساب RS لكل فترة (3M, 6M, 9M, 12M) على الطاير
    import pandas as pd
    
    # تحويل لـ DataFrame
    if results:
        df = pd.DataFrame([r.__dict__ for r in results])
        
        # دالة لحساب الترتيب المئوي (1-99)
        def calc_percentile(series):
            return (series.rank(pct=True) * 99).fillna(0).astype(int).clip(1, 99)
        
        if 'return_3m' in df.columns:
            df['rs_3m'] = calc_percentile(df['return_3m'])
        if 'return_6m' in df.columns:
            df['rs_6m'] = calc_percentile(df['return_6m'])
        if 'return_9m' in df.columns:
            df['rs_9m'] = calc_percentile(df['return_9m'])
        if 'return_12m' in df.columns:
            df['rs_12m'] = calc_percentile(df['return_12m'])
            
        # تحديث النتائج
        # نحتاج إرجاع قائمة objects متوافقة مع Pydantic
        # الطريقة الأسرع هي تحويل DataFrame لـ Dict
        final_results = []
        for _, row in df.iterrows():
            item = row.to_dict()
            # إضافة اسم الشركة مع تنظيف الرمز
            current_symbol = str(item['symbol']).strip()
            item['company_name'] = company_names.get(current_symbol, '')
            final_results.append(item)
            
        # تطبيق الفلاتر والترتيب (لأننا غيرنا القائمة)
        if limit and limit < len(final_results):
            final_results = final_results[:limit]
            
        return RSLatestResponse(
            data=final_results,
            total_count=len(df),
            date=latest_date
        )

    return RSLatestResponse(
        data=results,
        total_count=len(results),
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
    يستخدم للرسم البياني.
    """
    # تسوية الرمز (إذا كان حروف)
    # في حالتنا الرمز أرقام فقط (مثلاً 1010)، لكن لو كان حروف نحوله Upper
    symbol_str = str(symbol).strip().upper()
    
    query = db.query(RSDaily).filter(RSDaily.symbol == symbol_str)
    
    if from_date:
        query = query.filter(RSDaily.date >= from_date)
    if to_date:
        query = query.filter(RSDaily.date <= to_date)
    
    # ترتيب حسب التاريخ
    results = query.order_by(RSDaily.date).all()
    
    if not results:
        # لا نرجع 404 إذا كانت القائمة فارغة، بل قائمة فارغة أفضل للواجهة
        return []
    
    return results

@router.get("/screener/advanced", response_model=RSLatestResponse)
@limiter.limit("10/minute")
async def advanced_screener(
    request: Request,
    min_rs: float = Query(0, ge=0, le=99),
    min_r3m: Optional[float] = Query(None, description="Minimum 3 Month Return"),
    min_r12m: Optional[float] = Query(None, description="Minimum 12 Month Return"),
    sort_by: str = Query("rs_percentile", regex="^(rs_percentile|return_3m|return_12m|weighted_performance)$"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """
    فلترة متقدمة للأسهم
    """
    # آخر تاريخ
    latest_date_row = db.query(RSDaily.date).order_by(desc(RSDaily.date)).first()
    if not latest_date_row:
        return RSLatestResponse(data=[], total_count=0, date=date.today())
    
    latest_date = latest_date_row[0]
    
    query = db.query(RSDaily).filter(RSDaily.date == latest_date)
    
    # تطبيق الفلاتر
    if min_rs > 0:
        query = query.filter(RSDaily.rs_percentile >= min_rs)
    
    if min_r3m is not None:
        query = query.filter(RSDaily.return_3m >= min_r3m)
        
    if min_r12m is not None:
        query = query.filter(RSDaily.return_12m >= min_r12m)
    
    # الترتيب
    if sort_by == 'rs_percentile':
        query = query.order_by(desc(RSDaily.rs_percentile))
    elif sort_by == 'return_3m':
        query = query.order_by(desc(RSDaily.return_3m))
    elif sort_by == 'return_12m':
        query = query.order_by(desc(RSDaily.return_12m))
        
    results = query.limit(limit).all()
    
    return RSLatestResponse(
        data=results,
        total_count=len(results),
        date=latest_date
    )
