# backend/scrapers/single_company_scraper.py
"""
Single Company Financial Scraper.
Scrapes current financial data for a single company from Saudi Exchange.
"""
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper


class SingleCompanyScraper(BaseScraper):
    """
    Scraper for extracting current financial data from a single company.
    """
    
    def __init__(self, symbol: str = None, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
    
    async def scrape_financials(self) -> Dict[str, Any]:
        """Scrape financial data including Balance Sheet, Income Statement, and Cash Flows."""
        financial_data = {}
        periods = ["Annually", "Quarterly"]
        
        for period in periods:
            if self.page.is_closed():
                break

            try:
                print(f"    → Processing Period: {period}...")
                
                clicked = await self.click_tab(period)
                if not clicked:
                    print(f"      → Failed to find tab for {period}")
                    continue
                
                await self.page.wait_for_timeout(3000)
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(1000)

                tables_info = await self.extract_all_tables_with_visibility()
                
                main_table = None
                candidates = []
                
                for t_info in tables_info:
                    tbl = t_info['content']
                    if not tbl:
                        continue
                    
                    header_row = tbl[0]
                    headers = " ".join(list(header_row.keys())).lower()
                    first_col_val = list(header_row.values())[0] if header_row else ""
                    
                    is_candidate = False
                    if "balance sheet" in headers or "balance sheet" in str(first_col_val).lower():
                        if len(tbl) > 5:
                            is_candidate = True
                    elif "20" in headers and len(tbl) > 5:
                        content_snippet = str(tbl[:3]).lower()
                        if "assets" in content_snippet or "revenue" in content_snippet:
                            is_candidate = True
                    
                    if is_candidate:
                        candidates.append(t_info)

                visible_candidates = [c for c in candidates if c['visible']]
                
                if visible_candidates:
                    main_table = visible_candidates[0]['content']
                elif candidates:
                    main_table = candidates[0]['content']
                
                if main_table:
                    print(f"      → Selected Table with {len(main_table)} rows.")
                    
                    for section in ["Balance Sheet", "Statement Of Income", "Cash Flows"]:
                        sliced = self.slice_mixed_table(main_table, section)
                        if sliced:
                            key = f"{period}_{section.replace(' ', '_')}"
                            financial_data[key] = [sliced]
                            print(f"        → Extracted {section}: {len(sliced)} rows")
                else:
                    print(f"      → Warning: No main data table found for {period}")

            except Exception as e:
                print(f"    → Error processing {period}: {e}")

        return financial_data
    
    async def scrape_company(self, symbol: str = None) -> Dict[str, Any]:
        """
        Scrape financial data for a single company.
        
        Args:
            symbol: Company symbol (optional if set in constructor)
            
        Returns:
            Dictionary containing scraped financial data
        """
        symbol = symbol or self.symbol
        if not symbol:
            raise ValueError("Symbol must be provided")
        
        print(f"\n{'='*60}")
        print(f"Processing Company: {symbol}")
        print(f"{'='*60}")
        
        company_data = {
            "symbol": symbol,
            "financial_information": {}
        }
        
        try:
            if not await self.navigate_to_company(symbol):
                company_data["error"] = "Failed to navigate to company page"
                return company_data
            
            print("  📊 Processing Financials...")
            if await self.click_tab("Financials"):
                await self.page.wait_for_timeout(2000)
                
                print("    → Switching to 'FINANCIAL INFORMATION' tab...")
                if await self.click_tab("FINANCIAL INFORMATION"):
                    await self.page.wait_for_timeout(3000)
                    company_data["financial_information"] = await self.scrape_financials()
                else:
                    print("    → 'FINANCIAL INFORMATION' tab not found.")
            else:
                print("  ❌ Could not find 'Financials' tab.")
                company_data["error"] = "Financials tab not found"
                
        except Exception as e:
            print(f"  ❌ Error scraping company {symbol}: {e}")
            company_data["error"] = str(e)
            
        return company_data
    
    async def scrape_all(self) -> Dict[str, Any]:
        """
        Scrape a single company (for interface consistency).
        """
        if not self.symbol:
            raise ValueError("Symbol must be set before calling scrape_all()")
        
        async with async_playwright() as p:
            await self.init_browser()
            await self.init_http_client()
            
            try:
                result = await self.scrape_company(self.symbol)
                
                # Save JSON
                if "error" not in result:
                    self.save_to_json(self.symbol, result, "current")
                    
                    # Send to API
                    await self.send_to_api(result)
                    
                    # Upload Excel
                    excel_bytes = await self.export_to_excel(result)
                    if excel_bytes:
                        await self.upload_excel(self.symbol, excel_bytes)
                
                return result
                
            finally:
                await self.close_browser()
                await self.close_http_client()
    
    async def scrape(self, symbol: str = None) -> Dict[str, Any]:
        """
        Convenience method to scrape a single company.
        
        Args:
            symbol: Company symbol to scrape
            
        Returns:
            Dictionary containing scraped data
        """
        self.symbol = symbol or self.symbol
        return await self.scrape_all()


async def main():
    """Example usage."""
    scraper = SingleCompanyScraper(
        symbol="4020",
        headless=False,
        send_to_api=False,  # Set True when API is running
        upload_excel=False  # Set True when API is running
    )
    result = await scraper.scrape()
    print(f"\n✅ Scraped {len(result.get('financial_information', {}))} sections")


if __name__ == "__main__":
    asyncio.run(main())
