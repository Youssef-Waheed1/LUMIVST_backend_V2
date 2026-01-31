from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import logging
import os

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_driver(headless=True):
    """
    إعداد متصفح كروم بنفس إعدادات السكريبت القديم
    مع دعم Render deployment
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Check for Chrome binary from environment variable (for Render)
    chrome_bin = os.environ.get('CHROME_BIN') or os.environ.get('GOOGLE_CHROME_BIN')
    if chrome_bin:
        logger.info(f"📍 Using Chrome binary from env: {chrome_bin}")
        options.binary_location = chrome_bin
    else:
        # Try common paths on Linux (Render)
        linux_chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
        ]
        for path in linux_chrome_paths:
            if os.path.exists(path):
                logger.info(f"📍 Found Chrome at: {path}")
                options.binary_location = path
                break
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def clean_number(text):
    """
    تنظيف الأرقام من الفواصل والنسب المئوية
    """
    if not text:
        return 0.0
    text = text.replace(',', '').replace('%', '').strip()
    try:
        return float(text)
    except:
        return 0.0

def scrape_daily_details(headless=True):
    """
    سحب البيانات اليومية من صفحة التقرير التفصيلي
    """
    url = "https://www.saudiexchange.sa/Resources/Reports-v2/DetailedDaily_en.html"
    driver = None
    data = []

    try:
        logger.info("🚀 Starting Daily Details Scraper...")
        driver = build_driver(headless)
        
        logger.info(f"🌍 Navigating to {url}")
        driver.get(url)
        
        # استخراج كل الجداول
        tables = driver.find_elements(By.TAG_NAME, "table")
        logger.info(f"🔍 Found {len(tables)} tables on the page.")
        
        target_table = None
        max_rows = 0
        
        # البحث عن جدول الشركات (عادة هو أكبر جدول)
        for tbl in tables:
            try:
                rows = tbl.find_elements(By.TAG_NAME, "tr")
                row_count = len(rows)
                logger.info(f"Table with {row_count} rows found.")
                
                # جدول الشركات لازم يكون فيه صفوف كتير (أكتر من 50 مثلاً)
                if row_count > 50:
                    # فحص إضافي: هل يحتوي على كلمة Symbol أو Company؟
                    if "Symbol" in tbl.text or "Company" in tbl.text:
                        if row_count > max_rows:
                            max_rows = row_count
                            target_table = tbl
            except:
                continue
        
        if not target_table:
            logger.error("❌ Could not identify the Companies List table.")
            return []
            
        logger.info(f"✅ Target table identified with {max_rows} rows.")
        
        # محاولة عمل Scroll للجدول المستهدف
        try:
            driver.execute_script("arguments[0].scrollIntoView();", target_table)
            time.sleep(1)
        except:
            pass

        # استخراج الصفوف من الجدول المختار
        tbody = target_table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        
        logger.info(f"📊 Processing {len(rows)} rows from target table...")
        
        for i, row in enumerate(rows):
            cols = row.find_elements(By.TAG_NAME, "td")
            
            # تجاهل الصفوف القصيرة أو الفواصل
            if len(cols) < 5: 
                continue
            
            try:
                # العمود الأول رمز أو اسم
                col0_text = cols[0].text.strip()
                
                # لو العمود الأول رقم، يبقى ده الرمز (Symbol)
                if col0_text.isdigit():
                    symbol = col0_text
                    company = cols[1].text.strip()
                    
                    entry = {
                        "Symbol": symbol,
                        "Company": company,
                        "Open": clean_number(cols[2].text),
                        "Highest": clean_number(cols[3].text),
                        "Lowest": clean_number(cols[4].text),
                        "Close": clean_number(cols[5].text),
                        "Change %": clean_number(cols[6].text),
                        "Volume Traded": clean_number(cols[7].text),
                        "Value Traded": clean_number(cols[8].text),
                        "No. of Trades": clean_number(cols[9].text)
                    }
                    data.append(entry)
                    
                    # Debug sample
                    if len(data) == 1:
                        print(f"DEBUG FIRST ROW: {entry}")
            except Exception as e:
                # logger.warning(f"Skipping row {i}: {e}")
                continue
            
        logger.info(f"✅ Successfully scraped {len(data)} stocks.")
        
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            
    return data

if __name__ == "__main__":
    # Test the scraper
    results = scrape_daily_details(headless=False) # Headless=False عشان تشوف المتصفح وهو شغال
    print(f"Sample data: {results[:2] if results else 'No data'}")
