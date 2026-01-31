import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import SessionLocal
from models import User, hash_password

def create_admin():
    db = SessionLocal()
    email = "admin@annapradata.com"
    existing = db.query(User).filter(User.email == email).first()
    
    if existing:
        print(f"Admin already exists: {email}")
        db.close()
        return

    admin = User(
        full_name="Admin User",
        email=email,
        phone="9999999999",
        hashed_password=hash_password("admin"),
        is_admin=True,
        is_verified=True
    )
    db.add(admin)
    db.commit()
    print(f"✅ Admin created successfully!")
    print(f"Email: {email}")
    print(f"Password: admin")
    db.close()

if __name__ == "__main__":
    create_admin()
