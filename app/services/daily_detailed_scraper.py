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
    مع دعم Render/Docker deployment
    """
    import shutil
    
    options = Options()
    
    # إعدادات أساسية للاستقرار
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    if headless:
        options.add_argument("--headless=new")
    
    # البحث عن Chrome binary
    chrome_bin = None
    
    # 1. Check environment variables first
    for env_var in ['CHROME_BIN', 'GOOGLE_CHROME_BIN', 'CHROMIUM_BIN']:
        env_path = os.environ.get(env_var)
        if env_path and os.path.exists(env_path):
            chrome_bin = env_path
            logger.info(f"📍 Found Chrome from env {env_var}: {chrome_bin}")
            break
    
    # 2. Try shutil.which() to find Chrome in PATH
    if not chrome_bin:
        for chrome_name in ['google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium', 'chrome']:
            found_path = shutil.which(chrome_name)
            if found_path:
                chrome_bin = found_path
                logger.info(f"📍 Found Chrome in PATH: {chrome_bin}")
                break
    
    # 3. Try common Linux/Docker/Render paths
    if not chrome_bin:
        linux_chrome_paths = [
            # Render Chrome for Testing (from build script)
            '/opt/render/project/.chrome/chrome-linux64/chrome',
            # Standard Linux paths
            '/usr/bin/google-chrome-stable',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/opt/google/chrome/google-chrome',
            '/snap/bin/chromium',
            # Render apt buildpack path
            '/app/.apt/usr/bin/google-chrome',
        ]
        for path in linux_chrome_paths:
            if os.path.exists(path):
                chrome_bin = path
                logger.info(f"📍 Found Chrome at common path: {chrome_bin}")
                break
    
    # Set binary location if found
    if chrome_bin:
        options.binary_location = chrome_bin
        logger.info(f"✅ Using Chrome binary: {chrome_bin}")
    else:
        logger.warning("⚠️ Chrome binary not found! Will try default ChromeDriver behavior.")
    
    # Try to locate ChromeDriver manually first (Best for Render/Docker)
    chromedriver_path = None
    
    # Check environment variable
    env_chromedriver = os.environ.get('CHROMEDRIVER_PATH')
    if env_chromedriver and os.path.exists(env_chromedriver):
        chromedriver_path = env_chromedriver
    
    # Check common paths if env var not set
    if not chromedriver_path:
        possible_driver_paths = [
            '/opt/render/project/.chrome/chromedriver-linux64/chromedriver',
            '/app/.chromedriver/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver'
        ]
        for path in possible_driver_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break

    # If we found a specific ChromeDriver, try using it first
    if chromedriver_path:
        try:
            logger.info(f"📍 Found explicit ChromeDriver at: {chromedriver_path}")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("✅ Chrome WebDriver initialized successfully (via explicit path)")
            return driver
        except Exception as e:
            logger.warning(f"⚠️ Explicit ChromeDriver failed, falling back to manager: {e}")

    # Fallback: webdriver-manager
    try:
        logger.info("🔄 Attempting to use webdriver-manager...")
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Chrome WebDriver initialized successfully (via webdriver-manager)")
        return driver
    except Exception as e:
        logger.error(f"❌ All methods failed to initialize Chrome: {e}")
        raise

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
            
            # Check if row has enough columns (at least 11 for Market Cap)
            if len(cols) < 11: 
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
                        "No. of Trades": clean_number(cols[9].text),
                        "Market Cap": clean_number(cols[10].text)
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
