import sys
import os

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
# Ensure auth is imported after sys.path fix, and it handles the monkeypatch
from app.core.auth import get_password_hash
from app.models.user import User

def create_admin():
    print("--- Create Admin User ---")
    # Hardcoded for automation/testing purposes
    email = "admin@lumivst.com"
    password = "adminpassword123"
    full_name = "Admin User"

    print(f"Creating admin: {email}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            if not user.is_admin:
                user.is_admin = True
                db.commit()
                print(f"✅ Updated {email} to be an admin.")
            else:
                print(f"ℹ️ {email} is already an admin.")
            return

        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_verified=True,
            is_admin=True
        )
        db.add(new_user)
        db.commit()
        print(f"✅ Admin user {email} created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
