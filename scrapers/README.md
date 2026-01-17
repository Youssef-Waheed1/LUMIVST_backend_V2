# Lumivst Financial Scrapers

This folder contains Playwright-based scrapers for extracting financial data from Saudi Exchange.

## 📁 Scripts Overview

| Script | الوصف (Arabic) | Description |
|--------|---------------|-------------|
| `base_scraper.py` | الكلاس الأساسي مع كل الوظائف المشتركة | Base class with common functionality |
| `single_company_scraper.py` | سحب البيانات المالية لشركة واحدة | Scrapes financial data for a single company |
| `multi_company_scraper.py` | سحب البيانات المالية لشركات متعددة | Scrapes multiple companies with API integration |
| `historical_scraper.py` | سحب البيانات التاريخية (Display Previous Periods) | Scrapes historical data by clicking "Display Previous Periods" |
| `financial_reports_scraper.py` | سحب روابط التقارير (PDF, Excel, XBRL) | Extracts links to Financial Statements, XBRL, Board/ESG Reports |

## ⚙️ Requirements

```bash
pip install playwright httpx pandas openpyxl
playwright install chromium
```

## 🚀 Usage Examples

### Single Company - شركة واحدة
```python
from scrapers import SingleCompanyScraper

scraper = SingleCompanyScraper(symbol="4020")
await scraper.scrape()
```

### Multiple Companies - شركات متعددة
```python
from scrapers import MultiCompanyScraper

scraper = MultiCompanyScraper(symbols=["4020", "4100", "4150"])
await scraper.scrape_all()
```

### Historical Data - البيانات التاريخية
```python
from scrapers import HistoricalScraper

scraper = HistoricalScraper(symbols=["4020", "4100"])
await scraper.scrape_all()
```

### Financial Reports Links - روابط التقارير
```python
from scrapers import FinancialReportsScraper

scraper = FinancialReportsScraper(symbols=["4020", "2222"])
await scraper.scrape_all()
```

## 🔧 Configuration

Environment variables:
- `LUMIVST_API_URL`: API base URL (default: http://localhost:8000)
- `LUMIVST_API_TOKEN`: Bearer token for authentication

## 📊 Output

Scraped data is saved in:
- `backend/scraped_data/current/` - Current financial data
- `backend/scraped_data/historical/` - Historical financial data  
- `backend/scraped_data/report_links/` - PDF/Excel/XBRL report links

## 🔗 Mapping to Original Scripts

| Original Script (webScraping3g) | Lumivst Scraper |
|--------------------------------|-----------------|
| `scrape_multi_companies.py` | `multi_company_scraper.py` |
| `scrape_multi_history.py` | `historical_scraper.py` |
| `scrape_financial_reports.py` | `financial_reports_scraper.py` |
| `scrape_single_company.py` | `single_company_scraper.py` |
