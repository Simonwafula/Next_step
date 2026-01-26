import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.database import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash

def create_admin_user():
    db = SessionLocal()
    try:
        email = "mstatiliserver@gmail.com"
        password = "Password123!"
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            return
            
        print(f"Creating admin user {email}...")
        new_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="System Admin",
            is_active=True,
            is_verified=True,
            subscription_tier="enterprise"
        )
        db.add(new_user)
        db.commit()
        print("Admin user created successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
