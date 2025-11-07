# backend/test_final.py
import requests
import json

def test_final():
    symbol = "1304"
    country = "Saudi Arabia"
    
    print("🔍 الاختبار النهائي للـ API routes...")
    
    # اختبار 1: الـ route الجديد للبيانات المالية
    url1 = f"http://127.0.0.1:8000/api/v1/financials/{symbol}?country={country}&period=annual"
    print(f"📥 Testing 1: {url1}")
    
    try:
        response = requests.get(url1, timeout=10)
        print(f"📤 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ تم جلب البيانات بنجاح!")
            print(f"📊 Income: {len(data.get('income_statement', []))} records")
            print(f"📈 Balance: {len(data.get('balance_sheet', []))} records")
            print(f"💰 Cashflow: {len(data.get('cash_flow', []))} records")
            
            if data.get('income_statement'):
                print("\n📋 عينة من بيانات الدخل:")
                for item in data['income_statement'][:2]:
                    print(f"   {item.get('fiscal_date')}: sales={item.get('sales')}, net_income={item.get('net_income')}")
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*50)
    
    # اختبار 2: routes الكاش الحالية
    url2 = f"http://127.0.0.1:8000/api/v1/financials/income_statement/{symbol}?country={country}&period=annual"
    print(f"📥 Testing 2: {url2}")
    
    try:
        response = requests.get(url2, timeout=10)
        print(f"📤 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ تم جلب بيانات الدخل من الكاش!")
            print(f"📊 Records: {len(data.get('income_statement', []))}")
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_final()