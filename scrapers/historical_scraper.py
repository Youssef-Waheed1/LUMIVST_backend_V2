# backend/scrapers/historical_scraper.py
"""
Historical Financial Scraper.
Scrapes historical financial data by clicking "Display Previous Periods" on Saudi Exchange.
"""
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper


class HistoricalScraper(BaseScraper):
    """
    Scraper for extracting historical financial data from Saudi Exchange.
    Clicks "Display Previous Periods" to show data for multiple years.
    """
    
    def __init__(self, symbols: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.symbols = symbols or []
    
    async def scrape_historical_financials(self) -> Dict[str, Any]:
        """
        Scrape historical financial data including Balance Sheet, Income Statement, and Cash Flows.
        Activates history mode first by clicking "Display Previous Periods".
        """
        history_data = {}
        
        # Activate history mode
        print("    → Activating History Mode (Clicking 'Display Previous Periods')...")
        if not await self.table_has_history():
            await self.click_display_previous_periods()
            
            # Wait for history headers to appear
            print("      → Waiting for history headers to appear...")
            for _ in range(15):
                await self.page.wait_for_timeout(1000)
                if await self.table_has_history():
                    print("      → History headers (2021/2020) appeared!")
                    break
        
        # Iterate through sub-tabs and periods
        sub_tabs = ["Balance Sheet", "Statement Of Income", "Cash Flows"]
        periods = ["Annually", "Quarterly"]
        
        for tab_name in sub_tabs:
            print(f"      → Sub-tab: {tab_name}...")
            if not await self.click_tab(tab_name):
                continue
            await self.page.wait_for_timeout(2500)

            for period in periods:
                print(f"        → Period: {period}...")
                await self.click_tab(period)
                await self.page.wait_for_timeout(2500)
                
                target_table = None
                visible_tables = await self.get_visible_tables()
                
                # Prioritize table with history headers
                for tbl in visible_tables:
                    if not tbl:
                        continue
                    headers = str(list(tbl[0].keys())).lower()
                    if "2021" in headers or "2020" in headers or "2019" in headers:
                        target_table = tbl
                        break
                
                if not target_table and visible_tables:
                    # Fallback to largest table
                    target_table = max(visible_tables, key=len)

                if target_table:
                    key = f"{tab_name.replace(' ', '_')}_{period}"
                    history_data[key] = [target_table]
                    print(f"          ✅ Captured {len(target_table)} rows")
        
        return history_data
    
    async def scrape_company(self, symbol: str) -> Dict[str, Any]:
        """
        Scrape historical financial data for a single company.
        
        Args:
            symbol: Company symbol
            
        Returns:
            Dictionary containing scraped historical financial data
        """
        print(f"\n{'='*60}")
        print(f"Processing Historical Data for: {symbol}")
        print(f"{'='*60}")
        
        company_history = {
            "symbol": symbol,
            "history_information": {}
        }
        
        try:
            if not await self.navigate_to_company(symbol):
                company_history["error"] = "Failed to navigate to company page"
                return company_history
            
            print("  📊 Processing Financials...")
            if await self.click_tab("Financials"):
                await self.page.wait_for_timeout(2000)
                
                print("    → Switching to 'FINANCIAL INFORMATION' tab...")
                if await self.click_tab("FINANCIAL INFORMATION"):
                    await self.page.wait_for_timeout(3000)
                    company_history["history_information"] = await self.scrape_historical_financials()
                else:
                    print("    → 'FINANCIAL INFORMATION' tab not found.")
            else:
                print("  ❌ Could not find 'Financials' tab.")
                company_history["error"] = "Financials tab not found"
                
        except Exception as e:
            print(f"  ❌ Error scraping history for {symbol}: {e}")
            company_history["error"] = str(e)
            
        return company_history
    
    async def scrape_all(self) -> Dict[str, Any]:
        """
        Scrape historical data for all companies in the symbols list.
        
        Returns:
            Dictionary with summary of scraping results
        """
        if not self.symbols:
            raise ValueError("Symbols list is empty")
        
        print(f"\n{'='*60}")
        print(f"Starting Historical Scraper")
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
                        history_data = await self.scrape_company(symbol)
                        results[symbol] = history_data
                        
                        if "error" not in history_data:
                            successful += 1
                            
                            # Save JSON
                            self.save_to_json(symbol, history_data, "historical")
                            
                            # Send to API
                            if await self.send_to_api(history_data):
                                api_success += 1
                            
                            # Upload Excel
                            excel_bytes = await self.export_to_excel(history_data)
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
        print(f"Historical Scraping Complete!")
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


async def main():
    """Example usage."""
    # Scrape historical data for a subset of companies
    test_symbols = ["4020", "4100"]
    
    scraper = HistoricalScraper(
        symbols=test_symbols,
        headless=False,
        send_to_api=False,  # Set True when API is running
        upload_excel=False  # Set True when API is running
    )
    
    results = await scraper.scrape_all()
    print(f"\nSummary: {results['summary']}")


if __name__ == "__main__":
    asyncio.run(main())
