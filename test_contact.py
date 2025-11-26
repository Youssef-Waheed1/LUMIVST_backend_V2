import requests
import sys

API_URL = "http://localhost:8000/api/contact/"

def test_contact_submission():
    print("Testing Contact Submission...")
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "message": "This is a test message from the automated script."
    }
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 201:
            print("✅ Contact submission successful!")
            print(response.json())
        else:
            print(f"❌ Contact submission failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")

if __name__ == "__main__":
    test_contact_submission()
