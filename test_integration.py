import requests
import json

API_URL = "http://localhost:8000"

print("=" * 50)
print("🧪 TESTING ADMIN SYSTEM")
print("=" * 50)

# Test 1: Login
print("\n1️⃣ Testing Admin Login...")
try:
    login_response = requests.post(
        f"{API_URL}/api/auth/login",
        json={"email": "admin@lumivst.com", "password": "adminpassword123"},
        timeout=5
    )
    print(f"   Status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        token = token_data.get('access_token')
        print(f"   ✅ Login successful! Token: {token[:30]}...")
    else:
        print(f"   ❌ Login failed: {login_response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Test 2: Get Messages (Admin)
print("\n2️⃣ Testing Get Messages (Admin)...")
try:
    headers = {"Authorization": f"Bearer {token}"}
    messages_response = requests.get(
        f"{API_URL}/api/contact/",
        headers=headers,
        timeout=5
    )
    print(f"   Status: {messages_response.status_code}")
    
    if messages_response.status_code == 200:
        messages = messages_response.json()
        print(f"   ✅ Got {len(messages)} messages")
        for msg in messages[:2]:
            print(f"      - ID:{msg['id']}, Name:{msg['name']}, Email:{msg['email']}")
    else:
        print(f"   ❌ Failed: {messages_response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Submit Contact (Public)
print("\n3️⃣ Testing Contact Submission (Public)...")
try:
    contact_response = requests.post(
        f"{API_URL}/api/contact/",
        json={
            "name": "Integration Test",
            "email": "test@integration.com",
            "message": "This is an integration test message"
        },
        timeout=5
    )
    print(f"   Status: {contact_response.status_code}")
    
    if contact_response.status_code == 201:
        new_msg = contact_response.json()
        print(f"   ✅ Message submitted! ID: {new_msg['id']}")
        test_msg_id = new_msg['id']
    else:
        print(f"   ❌ Failed: {contact_response.text}")
        test_msg_id = None
except Exception as e:
    print(f"   ❌ Error: {e}")
    test_msg_id = None

# Test 4: Search/Filter
print("\n4️⃣ Testing Search...")
try:
    search_response = requests.get(
        f"{API_URL}/api/contact/?search=Integration",
        headers=headers,
        timeout=5
    )
    print(f"   Status: {search_response.status_code}")
    
    if search_response.status_code == 200:
        results = search_response.json()
        print(f"   ✅ Found {len(results)} results for 'Integration'")
    else:
        print(f"   ❌ Failed: {search_response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Delete Message (Admin)
if test_msg_id:
    print(f"\n5️⃣ Testing Delete Message (ID: {test_msg_id})...")
    try:
        delete_response = requests.delete(
            f"{API_URL}/api/contact/{test_msg_id}",
            headers=headers,
            timeout=5
        )
        print(f"   Status: {delete_response.status_code}")
        
        if delete_response.status_code == 204:
            print(f"   ✅ Message deleted successfully!")
        else:
            print(f"   ❌ Failed: {delete_response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Test 6: Verify non-admin can't access
print("\n6️⃣ Testing Security (Non-admin access)...")
try:
    no_auth_response = requests.get(
        f"{API_URL}/api/contact/",
        timeout=5
    )
    print(f"   Status: {no_auth_response.status_code}")
    
    if no_auth_response.status_code == 401 or no_auth_response.status_code == 403:
        print(f"   ✅ Correctly blocked unauthorized access!")
    else:
        print(f"   ⚠️ Warning: Endpoint accessible without auth!")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 50)
print("✅ ALL TESTS COMPLETED!")
print("=" * 50)
