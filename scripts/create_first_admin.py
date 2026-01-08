import sys
import os

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User
from app.core.auth import get_password_hash
from datetime import datetime

def create_admin():
    print("🚀 Initializing Admin User Creation...")
    
    email = input("Enter Admin Email (default: ayman@lumivst.com): ").strip()
    if not email:
        email = "ayman@lumivst.com"
        
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"✅ User {email} found.")
            if user.is_admin and user.is_approved:
                print("⚠️ User is already an admin and approved.")
            else:
                user.is_admin = True
                user.is_approved = True
                user.approved_at = datetime.utcnow()
                db.commit()
                print("✅ promoted existing user to ADMIN and APPROVED.")
        else:
            print(f"🆕 Creating new user {email}...")
            password = input("Enter Password (default: lumivst112026@): ").strip()
            if not password:
                password = "lumivst112026@"
            
            fullname = input("Enter Full Name (default:ayman): ").strip()
            if not fullname:
                fullname = "ayman"

            hashed_password = get_password_hash(password)
            
            new_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=fullname,
                is_admin=True,
                is_approved=True,
                is_verified=True,
                approved_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            print(f"✅ Created new ADMIN user: {email}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
