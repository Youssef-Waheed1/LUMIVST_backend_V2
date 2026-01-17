# backend/scrapers/multi_company_scraper.py
"""
Multi-Company Financial Scraper.
Scrapes current financial data for multiple companies from Saudi Exchange.
"""
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .single_company_scraper import SingleCompanyScraper


class MultiCompanyScraper(SingleCompanyScraper):
    """
    Scraper for extracting current financial data from multiple companies.
    """
    
    def __init__(self, symbols: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.symbols = symbols or []
    
    async def scrape_all(self) -> Dict[str, Any]:
        """
        Scrape all companies in the symbols list.
        
        Returns:
            Dictionary with summary of scraping results
        """
        if not self.symbols:
            raise ValueError("Symbols list is empty")
        
        print(f"\n{'='*60}")
        print(f"Starting Multi-Company Scraper")
        print(f"Companies to scrape: {len(self.symbols)}")
        print(f"{'='*60}")
        
        async with async_playwright() as p:
            await self.init_browser()
            await self.init_http_client()
            
            successful = 0
            failed = 0
            api_success = 0
            excel_success = 0
            results = {}
            
            try:
                for i, symbol in enumerate(self.symbols, 1):
                    print(f"\n[{i}/{len(self.symbols)}] Processing {symbol}...")
                    
                    try:
                        company_data = await self.scrape_company(symbol)
                        results[symbol] = company_data
                        
                        if "error" not in company_data:
                            successful += 1
                            
                            # Save JSON
                            self.save_to_json(symbol, company_data, "current")
                            
                            # Send to API
                            if await self.send_to_api(company_data):
                                api_success += 1
                            
                            # Upload Excel
                            excel_bytes = await self.export_to_excel(company_data)
                            if excel_bytes:
                                if await self.upload_excel(symbol, excel_bytes):
                                    excel_success += 1
                        else:
                            failed += 1
                        
                        # Delay between companies
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        failed += 1
                        print(f"  ❌ Error processing company {symbol}: {e}")
                        results[symbol] = {"symbol": symbol, "error": str(e)}
                
            finally:
                await self.close_browser()
                await self.close_http_client()
        
        print(f"\n{'='*60}")
        print(f"Scraping Complete!")
        print(f"{'='*60}")
        print(f"✅ Scraped Successfully: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📤 API Ingested: {api_success}")
        print(f"📊 Excel Uploaded: {excel_success}")
        print(f"{'='*60}")
        
        return {
            "summary": {
                "total": len(self.symbols),
                "successful": successful,
                "failed": failed,
                "api_ingested": api_success,
                "excel_uploaded": excel_success
            },
            "results": results
        }


# Default list of Saudi Exchange company symbols
DEFAULT_SYMBOLS = [
    # Banks
    "1180", "1050", "1010", "1020", "1030", "1060", "1080", "1120", "1140", "1150",
    # Petrochemicals
    "2010", "2020", "2060", "2070", "2170", "2210", "2250", "2290", "2310", "2330",
    # Retail
    "4001", "4002", "4003", "4004", "4005", "4006", "4007", "4008", "4009", "4010",
    # Healthcare
    "4004", "4005", "4007",
    # Insurance
    "8010", "8020", "8030", "8040", "8050", "8060", "8070", "8080",
    # Real Estate
    "4020", "4090", "4100", "4150", "4220", "4230", "4250", "4300", "4310", "4320",
    # And more...
]


async def main():
    """Example usage."""
    # Scrape a subset of companies
    test_symbols = ["4020", "4100", "4150"]
    
    scraper = MultiCompanyScraper(
        symbols=test_symbols,
        headless=False,
        send_to_api=False,  # Set True when API is running
        upload_excel=False  # Set True when API is running
    )
    
    results = await scraper.scrape_all()
    print(f"\nSummary: {results['summary']}")


if __name__ == "__main__":
    asyncio.run(main())
