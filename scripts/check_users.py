import sys
import os

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User

def check_users():
    print("🚀 Checking Users Status...")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"{'ID':<5} {'Email':<30} {'Approved':<10} {'Admin':<10} {'Verified':<10}")
        print("-" * 70)
        for user in users:
            print(f"{user.id:<5} {user.email:<30} {str(user.is_approved):<10} {str(user.is_admin):<10} {str(user.is_verified):<10}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
