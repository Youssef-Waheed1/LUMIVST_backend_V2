# app/api/routes/__init__.py
from .companies import router as companies_router
from .financials import router as financials_router

# علّق الـ cache إذا كان يسبب مشاكل
try:
    from .cache import router as cache_router
    __all__ = ["companies_router", "financials_router", "cache_router"]
except ImportError:
    __all__ = ["companies_router", "financials_router"]