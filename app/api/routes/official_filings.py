from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any
import asyncio
import os
from datetime import datetime

from app.core.database import get_db
from app.services.storage import storage_service
from app.models.official_filings import CompanyOfficialFiling, FilingCategory, FilingPeriod, FileType
from app.models.scraped_reports import Company
from app.schemas.official_filings import IngestOfficialFilingsRequest

router = APIRouter()

# --- Helpers ---

def map_category(cat_str: str) -> FilingCategory:
    # Maps scraper strings to Enum
    try:
        return FilingCategory(cat_str)
    except ValueError:
        # Fallback partial matching or return None
        if "financial" in cat_str.lower(): return FilingCategory.FINANCIAL_STATEMENTS
        if "xbrl" in cat_str.lower(): return FilingCategory.XBRL
        if "board" in cat_str.lower(): return FilingCategory.BOARD_REPORT
        if "esg" in cat_str.lower(): return FilingCategory.ESG_REPORT
        raise ValueError(f"Unknown category: {cat_str}")

def map_period(per_str: str) -> FilingPeriod:
    try:
        if not per_str: return FilingPeriod.ANNUAL
        return FilingPeriod(per_str)
    except ValueError:
        return FilingPeriod.ANNUAL # Default

def map_file_type(ft_str: str) -> FileType:
    ft_map = {'pdf': FileType.PDF, 'excel': FileType.EXCEL, 'xls': FileType.EXCEL, 'xlsx': FileType.EXCEL}
    key = ft_str.lower()
    if key in ft_map: return ft_map[key]
    return FileType.OTHER

async def process_ingestion(symbol: str, items: List[Dict[str, Any]], db_session_factory):
    """
    Background task to process items: Download -> S3 -> DB.
    """
    # Create a new session for background task
    db = db_session_factory()
    try:
        # Auto-create company if not exists
        existing_company = db.query(Company).filter(Company.symbol == symbol).first()
        if not existing_company:
            print(f"🏢 Company {symbol} not found. Creating automatically...")
            new_company = Company(symbol=symbol, name_en=f"Company {symbol}")
            db.add(new_company)
            db.commit()
            print(f"✅ Company {symbol} created.")
        
        for item in items:
            source_url = item.get('url')
            local_path = item.get('local_path')
            
            if not source_url and not local_path: continue # Skip if neither exist

            # Loop duplication check removed as it was faulty (missing symbol check)
            # and we trust the pre-filtering done in the route handler.

            try:
                # Prepare data
                year = item.get('year', 'Unknown')
                period = item.get('period', 'Annual')
                category = item.get('category_enum').value
                
                # Determine extension
                local_path = item.get('local_path')
                ext = 'pdf' # Default
                
                if item.get('file_type') == 'pdf':
                    ext = 'pdf'
                elif item.get('file_type') == 'excel':
                    # Check local path for true extension
                    if local_path and local_path.lower().endswith('.xls'):
                        ext = 'xls'
                    else:
                        ext = 'xlsx'
                
                # Sanitize filename
                filename = f"{period}_{category}".replace(" ", "_")
                destination_path = f"{symbol}/{year}/{filename}.{ext}"
                
                print(f"⬇️ Processing {filename} ({'Local' if local_path else 'Download'})...")
                
                public_url = ""
                if local_path and os.path.exists(local_path):
                     mime = 'application/pdf' if ext == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                     public_url = await storage_service.upload_local_file(local_path, destination_path, mime)
                elif source_url:
                     # Fallback to download
                     public_url = await storage_service.upload_file_from_url(source_url, destination_path)
                else:
                    print(f"⚠️  Skipping {filename}: No local path and no URL")
                    continue
                     
                print(f"✅ Uploaded to {public_url}")

                # Create DB Record
                new_record = CompanyOfficialFiling(
                    company_symbol=symbol,
                    category=item.get('category_enum'),
                    period=item.get('period_enum'),
                    year=int(year) if str(year).isdigit() else 0,
                    published_date=item.get('date_obj'),
                    file_url=public_url,
                    source_url=source_url,
                    file_type=item.get('file_type_enum'),
                    file_size_bytes=0 # We could capture this from storage service return or header
                )
                db.add(new_record)
                db.commit()

            except Exception as e:
                print(f"❌ Failed to process report {source_url}: {e}")
                db.rollback()

    except Exception as e:
        print(f"❌ Critical error in ingestion task: {e}")
    finally:
        db.close()


@router.post("/ingest/official-reports")
async def ingest_official_reports(
    payload: IngestOfficialFilingsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest metadata + triggers background file download/upload.
    """
    
    products_to_process = []
    
    # Pre-filter: Check what is new
    for category_name, items in payload.data.items():
        try:
            cat_enum = map_category(category_name)
        except ValueError:
            continue # Skip unknown categories
        
        for item in items:
            # Allow if URL exists OR local path exists
            if not item.url and not item.local_path: 
                continue
            
            # Check if exists in DB
            # If URL exists, check by URL
            exists = None
            if item.url:
                exists = db.query(CompanyOfficialFiling).filter(
                    CompanyOfficialFiling.source_url == item.url,
                    CompanyOfficialFiling.company_symbol == payload.symbol
                ).first()
            elif item.local_path:
                # If no URL, check by Year/Period/Category to avoid duplicates
                per_enum_check = map_period(item.period)
                cat_enum_check = map_category(category_name)
                exists = db.query(CompanyOfficialFiling).filter(
                    CompanyOfficialFiling.company_symbol == payload.symbol,
                    CompanyOfficialFiling.year == item.year,
                    CompanyOfficialFiling.period == per_enum_check,
                    CompanyOfficialFiling.category == cat_enum_check
                ).first()
            
            if exists:
                continue
                
            # Prepare data for processing
            per_enum = map_period(item.period)
            ft_enum = map_file_type(item.file_type)
            
            # Parse date if possible (scraper returns text like '2025-01-01' or similar)
            # You might need a date parser helper here
            date_obj = None 
            # (Skipping robust date parsing for brevity, let's assume NULL or implement simple)
            
            products_to_process.append({
                "url": item.url,
                "category_enum": cat_enum,
                "period_enum": per_enum,
                "file_type_enum": ft_enum,
                "year": item.year,
                "period": item.period,
                "file_type": item.file_type,
                "date_obj": date_obj,
                "local_path": item.local_path
            })
    
    if not products_to_process:
        return {"message": "No new reports to ingest."}

    # Pass a Session Factory or handle session carefully. 
    # FastAPI's Depends(get_db) session is closed after request.
    # We need a new session factory logic. 
    from app.core.database import SessionLocal
    
    background_tasks.add_task(process_ingestion, payload.symbol, products_to_process, SessionLocal)
    
    return {"message": f"Queued {len(products_to_process)} reports for background processing."}


@router.get("/reports/{symbol}")
def get_company_reports(symbol: str, db: Session = Depends(get_db)):
    """
    Get official filings grouped by category for frontend.
    """
    reports = db.query(CompanyOfficialFiling).filter(
        CompanyOfficialFiling.company_symbol == symbol
    ).all()
    
    # Structure for frontend: { "Financial Statements": [items...], ... }
    grouped = {
        FilingCategory.FINANCIAL_STATEMENTS.value: [],
        FilingCategory.XBRL.value: [],
        FilingCategory.BOARD_REPORT.value: [],
        FilingCategory.ESG_REPORT.value: []
    }
    
    for r in reports:
        item = {
            "id": r.id,
            "period": r.period.value,
            "year": r.year,
            "file_url": r.file_url,
            "published_date": r.published_date,
            "file_type": r.file_type.value if r.file_type else None
        }
        if r.category.value in grouped:
            grouped[r.category.value].append(item)
            
    return grouped
