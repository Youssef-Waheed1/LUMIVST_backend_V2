#!/usr/bin/env python3
"""
Script to diagnose OAuth configuration and connectivity
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_var(var_name, required=True):
    """Check if environment variable exists"""
    value = os.getenv(var_name)
    status = "✅" if value else "❌"
    
    if value:
        # Mask secrets
        if "SECRET" in var_name:
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
        else:
            masked_value = value
        print(f"{status} {var_name}: {masked_value}")
        return True
    else:
        print(f"{status} {var_name}: NOT SET {'(REQUIRED)' if required else '(optional)'}")
        return False

print("=" * 60)
print("🔍 OAuth Configuration Diagnostic")
print("=" * 60)

print("\n📋 Required Environment Variables:")
print("-" * 60)

all_ok = True
all_ok &= check_env_var("GOOGLE_CLIENT_ID", required=True)
all_ok &= check_env_var("GOOGLE_CLIENT_SECRET", required=True)
all_ok &= check_env_var("FACEBOOK_CLIENT_ID", required=True)
all_ok &= check_env_var("FACEBOOK_CLIENT_SECRET", required=True)
all_ok &= check_env_var("FRONTEND_URL", required=True)

print("\n📋 Optional Environment Variables:")
print("-" * 60)
check_env_var("DATABASE_URL", required=False)
check_env_var("REDIS_URL", required=False)

print("\n" + "=" * 60)
if all_ok:
    print("✅ All required OAuth variables are configured!")
    print("\nYou can now:")
    print("  1. Start the backend: python -m uvicorn app.main:app --reload")
    print("  2. Test social login in the frontend")
else:
    print("❌ Some required variables are missing!")
    print("\nTo fix:")
    print("  1. Create/update .env file in backend/ directory")
    print("  2. Add the missing variables")
    print("  3. Restart the backend server")
    print("\nSee SOCIAL_LOGIN_APPROVAL_GUIDE.md for detailed instructions")

print("=" * 60)
