#!/usr/bin/env python
# backend/scripts/run_scraper.py
"""
CLI script to run the financial scrapers.

Usage:
    python scripts/run_scraper.py --type multi --symbols 4020,4100,4150
    python scripts/run_scraper.py --type history --symbols 4020,4100
    python scripts/run_scraper.py --type reports --symbols 4020,2222
    python scripts/run_scraper.py --type single --symbols 4020
"""
import asyncio
import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_multi_company_scraper(symbols: list, headless: bool, send_api: bool, upload_excel: bool, save_json: bool):
    """Run the multi-company scraper."""
    from scrapers import MultiCompanyScraper
    
    print(f"\n🚀 Starting Multi-Company Scraper")
    print(f"   Symbols: {symbols}")
    print(f"   Headless: {headless}, API: {send_api}, Excel: {upload_excel}, JSON: {save_json}\n")
    
    scraper = MultiCompanyScraper(
        symbols=symbols,
        headless=headless,
        send_to_api=send_api,
        upload_excel=upload_excel,
        save_json=save_json
    )
    return await scraper.scrape_all()


async def run_historical_scraper(symbols: list, headless: bool, send_api: bool, upload_excel: bool, save_json: bool):
    """Run the historical data scraper."""
    from scrapers import HistoricalScraper
    
    print(f"\n🚀 Starting Historical Scraper")
    print(f"   Symbols: {symbols}")
    print(f"   Headless: {headless}, API: {send_api}, Excel: {upload_excel}, JSON: {save_json}\n")
    
    scraper = HistoricalScraper(
        symbols=symbols,
        headless=headless,
        send_to_api=send_api,
        upload_excel=upload_excel,
        save_json=save_json
    )
    return await scraper.scrape_all()


async def run_reports_scraper(symbols: list, headless: bool):
    """Run the financial reports links scraper."""
    from scrapers import FinancialReportsScraper
    
    print(f"\n🚀 Starting Financial Reports Scraper")
    print(f"   Symbols: {symbols}")
    print(f"   Headless: {headless}\n")
    
    scraper = FinancialReportsScraper(
        symbols=symbols,
        headless=headless
    )
    return await scraper.scrape_all()


async def run_single_company_scraper(symbol: str, headless: bool, send_api: bool, upload_excel: bool, save_json: bool):
    """Run the single company scraper."""
    from scrapers import SingleCompanyScraper
    
    print(f"\n🚀 Starting Single Company Scraper")
    print(f"   Symbol: {symbol}")
    print(f"   Headless: {headless}, API: {send_api}, Excel: {upload_excel}, JSON: {save_json}\n")
    
    scraper = SingleCompanyScraper(
        symbol=symbol,
        headless=headless,
        send_to_api=send_api,
        upload_excel=upload_excel,
        save_json=save_json
    )
    return await scraper.scrape()


def main():
    parser = argparse.ArgumentParser(description='Run financial data scrapers')
    
    parser.add_argument(
        '--type', '-t',
        choices=['multi', 'history', 'reports', 'single'],
        default='multi',
        help='Type of scraper to run'
    )
    
    parser.add_argument(
        '--symbols', '-s',
        type=str,
        required=True,
        help='Comma-separated list of company symbols (e.g., 4020,4100,4150)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=False,
        help='Run browser in headless mode'
    )
    
    parser.add_argument(
        '--no-api',
        action='store_true',
        default=False,
        help='Disable sending data to API'
    )
    
    parser.add_argument(
        '--no-excel',
        action='store_true',
        default=False,
        help='Disable Excel upload'
    )
    
    parser.add_argument(
        '--no-json',
        action='store_true',
        default=False,
        help='Disable JSON file saving'
    )
    
    args = parser.parse_args()
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    
    if not symbols:
        print("❌ No symbols provided")
        sys.exit(1)
    
    send_api = not args.no_api
    upload_excel = not args.no_excel
    save_json = not args.no_json
    
    # Run the appropriate scraper
    if args.type == 'multi':
        result = asyncio.run(run_multi_company_scraper(symbols, args.headless, send_api, upload_excel, save_json))
    elif args.type == 'history':
        result = asyncio.run(run_historical_scraper(symbols, args.headless, send_api, upload_excel, save_json))
    elif args.type == 'reports':
        result = asyncio.run(run_reports_scraper(symbols, args.headless))
    elif args.type == 'single':
        result = asyncio.run(run_single_company_scraper(symbols[0], args.headless, send_api, upload_excel, save_json))
    
    print(f"\n✅ Scraping Complete!")
    if result and 'summary' in result:
        print(f"   Summary: {result['summary']}")


if __name__ == "__main__":
    main()
