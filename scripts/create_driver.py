import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, hash_password

def create_test_driver():
    db = SessionLocal()
    try:
        # Check if driver already exists
        driver = db.query(User).filter(User.email == "driver@annapradata.com").first()
        if not driver:
            driver = User(
                full_name="Rajesh Delivery",
                email="driver@annapradata.com",
                phone="9822001122",
                hashed_password=hash_password("driver123"),
                is_driver=True,
                is_verified=True
            )
            db.add(driver)
            db.commit()
            print("Driver 'Rajesh' created successfully.")
        else:
            print("Driver already exists.")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_driver()
