"""
Script to update admin credentials
Usage: python update_admin.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.core.auth import get_password_hash
from app.models.user import User

def update_admin_credentials():
    """Update admin email and password"""
    
    print("=" * 60)
    print("🔐 UPDATE ADMIN CREDENTIALS")
    print("=" * 60)
    
    # Get current admin info
    print("\n📋 Current Admin Info:")
    print("   Email: admin@lumivst.com")
    print("   Password: adminpassword123")
    
    # Get new credentials
    print("\n✏️  Enter New Credentials:")
    new_email = input("   New Email (press Enter to keep current): ").strip()
    new_password = input("   New Password (press Enter to keep current): ").strip()
    
    if not new_email and not new_password:
        print("\n⚠️  No changes made.")
        return
    
    # Confirm
    print("\n⚠️  Confirm Changes:")
    if new_email:
        print(f"   New Email: {new_email}")
    if new_password:
        print(f"   New Password: {'*' * len(new_password)}")
    
    confirm = input("\n   Continue? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ Update cancelled.")
        return
    
    # Update database
    db = next(get_db())
    try:
        # Find admin user
        admin = db.query(User).filter(User.email == "admin@lumivst.com").first()
        
        if not admin:
            print("\n❌ Admin user not found!")
            return
        
        # Update email
        if new_email:
            admin.email = new_email
            print(f"\n✅ Email updated to: {new_email}")
        
        # Update password
        if new_password:
            admin.hashed_password = get_password_hash(new_password)
            print(f"✅ Password updated successfully")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("✅ ADMIN CREDENTIALS UPDATED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📝 New Credentials:")
        print(f"   Email: {new_email if new_email else 'admin@lumivst.com'}")
        print(f"   Password: {new_password if new_password else 'adminpassword123'}")
        print("\n⚠️  Please save these credentials in a secure location!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error updating credentials: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_credentials()
