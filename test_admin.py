import requests

API_URL = "http://localhost:8000"

def test_admin_login():
    print("Testing Admin Login...")
    payload = {
        "email": "admin@lumivst.com",
        "password": "adminpassword123"
    }
    try:
        response = requests.post(f"{API_URL}/api/auth/login", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            token = response.json().get('access_token')
            print(f"Token: {token[:50]}...")
            
            # Test getting messages with the token
            headers = {"Authorization": f"Bearer {token}"}
            messages_response = requests.get(f"{API_URL}/api/contact/", headers=headers)
            print(f"\nMessages Status: {messages_response.status_code}")
            if messages_response.status_code == 200:
                print(f"✅ Got messages: {len(messages_response.json())} messages")
            else:
                print(f"❌ Failed to get messages: {messages_response.text}")
        else:
            print(f"❌ Login failed")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_admin_login()
