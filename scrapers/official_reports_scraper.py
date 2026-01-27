import asyncio
import json
import os
import argparse
from typing import Dict, List, Any
from playwright.async_api import async_playwright, Page, Locator

# --- Configuration ---
TIMEOUT_MS = 120000

class FinancialReportsScraper:
    def __init__(self, symbol: str, headless: bool = False):
        self.symbol = symbol
        self.headless = headless
        
        # Updated URL that works for all companies
        base_long_url = "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz83d2MXA0C3SydAl1c3Q0NvE30I4EKzBEKDMKcTQzMDPxN3H19LAzdTU31w8syU8v1wwkpK8hOMgUA-oskdg!!/"
        self.base_url = f"{base_long_url}?companySymbol={symbol}"
        
        # Download directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.download_base_dir = os.path.join(script_dir, "..", "data", "downloads", symbol)
        os.makedirs(self.download_base_dir, exist_ok=True)
        
        self.context = None

    async def scrape(self) -> Dict[str, Any]:
        """Main method to scrape only Financial Statements and Reports."""
        reports_data = {}
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.headless, args=["--disable-http2"])
            self.context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (HTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1600, "height": 1000},
                locale="en-US",
                accept_downloads=True
            )
            page = await self.context.new_page()
            
            try:
                print(f"Navigating to {self.base_url}...")
                
                # Retry logic for navigation
                for attempt in range(3):
                    try:
                        await page.goto(self.base_url, timeout=TIMEOUT_MS)
                        await page.wait_for_load_state("domcontentloaded")
                        break
                    except Exception as nav_e:
                        print(f"  -> Navigation attempt {attempt+1} failed: {nav_e}")
                        if attempt == 2:
                             print("  -> Max retries reached. Returning empty data.")
                             await browser.close()
                             return reports_data
                        await asyncio.sleep(5)
                
                # Navigate to Financials Tab
                print("Processing Financials Tab...")
                if await self._click_tab(page, "Financials"):
                    await page.wait_for_timeout(3000) 
                    
                    # Target Section: FINANCIAL STATEMENTS AND REPORTS
                    print("\n--- Scraping FINANCIAL STATEMENTS AND REPORTS ---")
                    reports_data = await self._scrape_statements_and_reports(page)
                    
                else:
                    print("Could not find 'Financials' tab.")

            except Exception as e:
                print(f"An error occurred during scraping: {e}")
            finally:
                await browser.close()
                
        return reports_data

    # --- Helper methods ---

    async def _click_tab(self, page: Page, tab_name: str) -> bool:
        """Helper to find and click a tab."""
        return await self._js_click_tab(page, tab_name)

    async def _js_click_tab(self, page: Page, text: str) -> bool:
        """Robust JS click using scoring strategy."""
        return await page.evaluate(f"""(text) => {{
            const target = text.toLowerCase();
            const tags = ['li', 'a', 'button', 'div', 'span', 'h2', 'h3', 'h4', 'h5'];
            let best = null;
            let bestScore = -9999;
            
            function getScore(el) {{
               let score = 0;
               const txt = (el.innerText || '').toLowerCase().trim();
               if (!txt.includes(target)) return -10000;
               score -= txt.length; 
               const tag = el.tagName.toLowerCase();
               if (['li', 'a', 'button'].includes(tag)) score += 2000;
               else if (['div', 'span'].includes(tag)) score += 500;
               if (txt === target) score += 1000;
               if (el.offsetParent !== null) score += 100;
               return score;
            }}
            
            const all = document.querySelectorAll(tags.join(','));
            for (const el of all) {{
               if (el.offsetParent === null) continue;
               const s = getScore(el);
               if (s > bestScore) {{
                   bestScore = s;
                   best = el;
               }}
            }}
            
            if (best && bestScore > -5000) {{
                best.scrollIntoView();
                best.click();
                return true;
            }}
            return false;
        }}""", text)

    async def _download_file(self, url: str, section: str, year: str, period: str, f_type: str) -> str:
        """
        Downloads a file by injecting a click on the home page context.
        This ensures correct Cookies/Origin and forces 'download' attribute to bypass PDF viewer.
        """
        try:
            if not url: return None
            
            # Construct filename
            ext = 'pdf'
            low_url = url.lower()
            if f_type == 'excel' or '.xls' in low_url: 
                ext = 'xlsx' if '.xlsx' in low_url else 'xls'
            elif '.pdf' in low_url: 
                ext = 'pdf'
            
            safe_period = period.replace(" ", "_").replace("/", "-")
            safe_section = section.replace(" ", "_").replace("/", "-")
            filename = f"{year}_{safe_section}_{safe_period}.{ext}"
            
            file_path = os.path.join(self.download_base_dir, filename)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                 return file_path
            
            print(f"      ⬇️ Downloading {filename}...")
            
            # Retry download logic
            for attempt in range(2):
                page = await self.context.new_page()
                try:
                    # 1. Go to the domain root to establish context (Cookies/Origin)
                    await page.goto("https://www.saudiexchange.sa/wps/portal/saudiexchange/home", 
                                  wait_until="domcontentloaded", 
                                  timeout=90000) # Increased timeout
                    
                    # 2. Setup Listener
                    async with page.expect_download(timeout=120000) as download_info: # Increased wait for download start
                        # 3. Inject JS to force download
                        await page.evaluate(f"""(url) => {{
                            const a = document.createElement('a');
                            a.href = url;
                            a.setAttribute('download', 'file'); 
                            a.target = '_self'; 
                            document.body.appendChild(a);
                            a.click();
                        }}""", url)

                    download = await download_info.value
                    await download.save_as(file_path)
                    
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 100:
                        return file_path
                    else:
                        print(f"      ⚠️ Attempt {attempt+1}: File too small or missing.")
                        
                except Exception as e:
                    print(f"      ⚠️ Attempt {attempt+1} failed: {e}")
                    if attempt == 1: # Last attempt
                        print(f"      ❌ Final Download Failure for {filename}")
                        return None
                    await asyncio.sleep(2) # Wait before retry
                finally:
                    await page.close()
            
            return None

        except Exception as e:
            print(f"      ❌ General download error: {e}")
            return None

    async def _scrape_statements_and_reports(self, page: Page) -> Dict[str, Any]:
        """
        Scrapes 'FINANCIAL STATEMENTS AND REPORTS'.
        """
        reports_data = {}
        
        print("\n  -> Preparing view for FINANCIAL STATEMENTS AND REPORTS...")
        
        try:
            # Try specific text
            clicked = await self._js_click_tab(page, "FINANCIAL STATEMENTS AND REPORTS")
            if not clicked:
                 clicked = await self._js_click_tab(page, "Financial Statements")
            
            if not clicked:
                print("  -> Failed to click 'FINANCIAL STATEMENTS AND REPORTS' tab.")
                return reports_data
            
            await page.wait_for_timeout(5000)

            # Locate the main table
            table_locator = page.locator(".tableStyle table")
            try:
                await table_locator.first.wait_for(state="visible", timeout=10000)
            except: pass

            if await table_locator.count() == 0:
                print("  -> Main table (.tableStyle table) not found in DOM!")
                return reports_data
            
            print("  -> Found main table. Parsing rows sequentially...")

            # Capture ALL links
            raw_data = await page.evaluate(r"""() => {
                const rows = Array.from(document.querySelectorAll('.tableStyle table tr'));
                const results = {};
                let currentSection = 'General Reports';
                let columnYears = {}; 
                
                rows.forEach((row, rowIndex) => {
                    const text = row.innerText.trim();
                    const firstCell = row.querySelector('td');
                    let rowLabel = ''; 
                    if (firstCell) rowLabel = firstCell.innerText.trim();

                    // --- 1. Detect Section Headers ---
                    const validSections = ['Financial Statements', 'XBRL', 'Board Report', 'ESG Report'];
                    const validPeriods = ['Annual', 'Q1', 'Q2', 'Q3', 'Q4'];

                    if (validSections.includes(text) || validSections.includes(rowLabel)) {
                         const sectionName = validSections.includes(text) ? text : rowLabel;
                         currentSection = sectionName;
                         if (!results[currentSection]) results[currentSection] = [];
                         if (text === sectionName) return; 
                    } 
                    else if (validPeriods.includes(rowLabel)) {}
                    else if (rowLabel !== '') {
                        const potentialYears = Array.from(row.querySelectorAll('th, td')).map(c => c.innerText.trim());
                        const hasYears = potentialYears.some(t => /^\d{4}$/.test(t));
                        if (!hasYears) return; 
                    }

                    // --- 2. Detect Years ---
                    const ths = Array.from(row.querySelectorAll('th, td'));
                    const potentialYears = ths.map(cell => cell.innerText.trim());
                    const hasYears = potentialYears.some(t => /^\d{4}$/.test(t));
                    
                    if (hasYears) {
                        columnYears = {};
                        ths.forEach((cell, index) => {
                            const txt = cell.innerText.trim();
                            if (/^\d{4}$/.test(txt)) {
                                columnYears[index] = txt;
                            }
                        });
                        return; 
                    }

                    if (!results[currentSection]) results[currentSection] = [];

                    // --- 3. Process Cells ---
                    const cells = Array.from(row.querySelectorAll('td'));
                    cells.forEach((cell, colIndex) => {
                         let year = columnYears[colIndex] || "Unknown";
                         let finalPeriod = rowLabel || "Annual";

                         const anchors = Array.from(cell.querySelectorAll('a'));
                         
                         if (anchors.length > 0) {
                             anchors.forEach(a => {
                                 const href = a.href;
                                 if (!href || href.includes('javascript') || href === '#') return;
                                 results[currentSection].push({
                                     url: href,
                                     row_label: finalPeriod,
                                     year: year,          
                                     text: a.innerText.trim() 
                                 });
                             });
                         } else {
                             if (year !== "Unknown" && colIndex > 0) {
                                 const cellText = cell.innerText.trim();
                                 results[currentSection].push({
                                     url: null,
                                     row_label: finalPeriod,
                                     year: year,
                                     text: cellText || "-"
                                 });
                             }
                         }
                    });
                });
                return results;
            }""")
            
            for section, items in raw_data.items():
                if not items: continue
                clean_items = []
                print(f"      -> Processing {len(items)} items for {section}...")
                
                for item in items:
                    url = item.get('url') 
                    lower_url = (url or "").lower()
                    
                    if section == "XBRL":
                        if url and not (".xls" in lower_url): continue
                            
                    f_type = 'none'
                    if url:
                        if '.pdf' in lower_url: f_type = 'pdf'
                        elif '.xls' in lower_url: f_type = 'excel'
                        else: f_type = 'other'
                    
                    period = item.get('row_label', '')
                    year = item.get('year', '')
                    
                    # --- DOWNLOAD FILE ---
                    local_path = None
                    if url:
                        local_path = await self._download_file(url, section, year, period, f_type)
                    # ---------------------

                    clean_items.append({
                        "url": url,
                        "local_path": local_path,  # Added this field
                        "file_type": f_type,
                        "period": period,
                        "year": year,
                        "published_date": item.get('text', '')
                    })
                
                reports_data[section] = clean_items
                print(f"      -> Saved {len(clean_items)} items for {section}")

        except Exception as e:
            print(f"  -> Error processing statements section: {e}")
            
        return reports_data

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default="4322", help="Company symbol to scrape")
    args = parser.parse_args()
    
    scraper = FinancialReportsScraper(symbol=args.symbol, headless=False)
    data = await scraper.scrape()
    
    # Save to independent 'data' directory in backend
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    output_file = os.path.join(data_dir, "scrape_financial_reports.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"\nReports scraping complete. Data saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
