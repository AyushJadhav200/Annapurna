import sys
import os
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import SessionLocal, init_db
from models import (
    MenuItem, User, Address, Order, KitchenStatus, 
    PartnerInquiry, Rating, Subscription, CoinLedger, 
    OrderItem, PromoCode, hash_password
)

def clear_all_data(db):
    """Deep clean of the database for a fresh start"""
    print("🧹 Clearing all existing dummy data...")
    db.query(OrderItem).delete()
    db.query(Rating).delete()
    db.query(Order).delete()
    db.query(Subscription).delete()
    db.query(CoinLedger).delete()
    db.query(Address).delete()
    db.query(PartnerInquiry).delete()
    db.query(PromoCode).delete()
    db.query(MenuItem).delete()
    db.query(User).delete()
    db.query(KitchenStatus).delete()
    db.commit()
    print("✅ Database is now clean!")

def seed_real_menu(db):
    print("🍱 Seeding Authentic Maharashtrian Menu...")
    items = [
        # --- SA KALCHA NASTA (BREAKFAST) ---
        {
            "name": "Kanda Pohe",
            "price": 45,
            "category": "Sakaalcha Nasta (Breakfast)",
            "description": "Flavorful flattened rice with onions, peanuts, and a hint of lemon.",
            "preparation_time_mins": 10,
            "is_bestseller": True
        },
        {
            "name": "Misal Pav",
            "price": 85,
            "category": "Sakaalcha Nasta (Breakfast)",
            "description": "Spicy sprouted bean curry topped with farsan, served with fresh pav.",
            "preparation_time_mins": 15,
            "is_bestseller": True
        },
        {
            "name": "Sabudana Khichdi",
            "price": 65,
            "category": "Sakaalcha Nasta (Breakfast)",
            "description": "Sago pearls cooked with crushed peanuts and green chillies. A fasting favorite.",
            "preparation_time_mins": 12
        },
        {
            "name": "Thalipeeth",
            "price": 75,
            "category": "Sakaalcha Nasta (Breakfast)",
            "description": "Traditional multi-grain pancake served with dollop of white butter (Loni).",
            "preparation_time_mins": 18
        },

        # --- SWAYAMPAKGHAR (MAIN COURSE) ---
        {
            "name": "Pithla Bhakri Thali",
            "price": 140,
            "category": "Swayampakghar (Main Course)",
            "description": "Rustic gram flour curry served with Jowar Bhakri, Thecha, and Onions.",
            "preparation_time_mins": 25,
            "is_bestseller": True
        },
        {
            "name": "Bharli Vangi",
            "price": 160,
            "category": "Swayampakghar (Main Course)",
            "description": "Baby eggplants stuffed with peanut-coconut masala in a rich gravy.",
            "preparation_time_mins": 25
        },
        {
            "name": "Varan Bhaat with Toop",
            "price": 90,
            "category": "Swayampakghar (Main Course)",
            "description": "The ultimate soul food: Comforting dal-rice served with pure cow ghee.",
            "preparation_time_mins": 15
        },
        {
            "name": "Tambda-Pandhra Rassa Thali",
            "price": 320,
            "category": "Swayampakghar (Main Course)",
            "description": "Kolhapuri Mutton feast with spicy red gravy and soothing white coconut gravy.",
            "preparation_time_mins": 35,
            "is_bestseller": True
        },

        # --- CHAHA-PAANI (SNACKS) ---
        {
            "name": "Vada Pav (2 pcs)",
            "price": 40,
            "category": "Chaha-Paani (Snacks)",
            "description": "The legendary Mumbai burger: Spiced potato dumpling in a bun.",
            "preparation_time_mins": 10,
            "is_bestseller": True
        },
        {
            "name": "Kothimbir Vadi",
            "price": 90,
            "category": "Chaha-Paani (Snacks)",
            "description": "Steamed and fried savory cakes made of coriander and gram flour.",
            "preparation_time_mins": 20
        },
        {
            "name": "Sabudana Vada (2 pcs)",
            "price": 70,
            "category": "Chaha-Paani (Snacks)",
            "description": "Golden fried sago and peanut patties served with sweet curd.",
            "preparation_time_mins": 15
        },

        # --- GOD-DHODD (DESSERTS) ---
        {
            "name": "Puran Poli (2 pcs)",
            "price": 110,
            "category": "God-Dhodd (Desserts)",
            "description": "Sweet flatbread filled with soft Chana Dal and jaggery. Served with Ghee.",
            "preparation_time_mins": 20,
            "is_bestseller": True
        },
        {
            "name": "Modak (5 pcs)",
            "price": 150,
            "category": "God-Dhodd (Desserts)",
            "description": "Steamed rice flour dumplings filled with fresh coconut and jaggery.",
            "preparation_time_mins": 30
        },
        {
            "name": "Shrikhand Puri Thali",
            "price": 130,
            "category": "God-Dhodd (Desserts)",
            "description": "Velvety saffron-infused sweet yogurt served with 5 hot, fluffy puris.",
            "preparation_time_mins": 15,
            "is_bestseller": True
        }
    ]
    
    for item_data in items:
        db.add(MenuItem(**item_data))
    
    db.commit()
    print(f"✅ Created {len(items)} real menu items")

def seed_essential_users(db):
    print("👤 Creating Official Accounts...")
    
    # Official Admin
    admin = User(
        full_name="Annapradata Admin",
        email="admin@annapradata.com",
        phone="9999999999",
        hashed_password=hash_password("admin_pass_2024"),
        is_admin=True,
        is_verified=True
    )
    db.add(admin)
    
    # Official Test Driver
    driver = User(
        full_name="Rajesh Delivery Partner",
        email="driver@annapradata.com",
        phone="9876543210",
        hashed_password=hash_password("driver123"),
        is_driver=True,
        is_verified=True
    )
    db.add(driver)
    
    db.commit()
    print("✅ Created Admin and Driver accounts")

def init_system(db):
    status = KitchenStatus(is_open=True, base_eta_mins=30)
    db.add(status)
    db.commit()
    print("✅ System configuration initialized")

def main():
    print("🚀 Starting Production Database Reset...")
    init_db()
    db = SessionLocal()
    try:
        clear_all_data(db)
        seed_real_menu(db)
        seed_essential_users(db)
        init_system(db)
        print("\n✨ SUCCESS: Database is now ready for Live Launch!")
        print("Admin Login: admin@annapradata.com / admin_pass_2024")
    finally:
        db.close()

if __name__ == "__main__":
    main()
