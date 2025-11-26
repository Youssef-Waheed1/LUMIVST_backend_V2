"""
Quick script to update admin credentials with predefined values
Usage: python quick_update_admin.py <new_email> <new_password>
Example: python quick_update_admin.py myemail@example.com MyNewPass123
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.core.auth import get_password_hash
from app.models.user import User

def quick_update_admin(new_email: str, new_password: str):
    """Update admin credentials quickly"""
    
    print("=" * 60)
    print("🔐 QUICK UPDATE ADMIN CREDENTIALS")
    print("=" * 60)
    
    db = next(get_db())
    try:
        # Find admin user (try both old and new email)
        admin = db.query(User).filter(
            (User.email == "admin@lumivst.com") | (User.is_admin == True)
        ).first()
        
        if not admin:
            print("\n❌ Admin user not found!")
            return
        
        # Update credentials
        admin.email = new_email
        admin.hashed_password = get_password_hash(new_password)
        admin.is_admin = True  # Ensure admin flag is set
        
        db.commit()
        
        print("\n✅ ADMIN CREDENTIALS UPDATED!")
        print(f"\n📝 New Credentials:")
        print(f"   Email: {new_email}")
        print(f"   Password: {new_password}")
        print("\n⚠️  Save these credentials securely!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python quick_update_admin.py <new_email> <new_password>")
        print("Example: python quick_update_admin.py myemail@example.com MyNewPass123")
        sys.exit(1)
    
    new_email = sys.argv[1]
    new_password = sys.argv[2]
    
    quick_update_admin(new_email, new_password)
