import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import MenuItem, Base

# Create tables if not exist
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    
    # clear existing items
    db.query(MenuItem).delete()
    db.commit()
    
    items = [
        # --- SA KALCHA NASTA (BREAKFAST) ---
        {
            "name": "Puran Poli",
            "description": "Sweet flatbread stuffed with lentil and jaggery filling, served with warm ghee/milk.",
            "price": 60.0,
            "category": "Sakaalcha Nasta (Breakfast)",
            "image_url": "/static/food_1_puran_poli.png",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Misal Pav",
            "description": "Spicy sprouted bean curry topped with farsan, onions, lemon, served with pav.",
            "price": 90.0,
            "category": "Sakaalcha Nasta (Breakfast)",
            "image_url": "https://source.unsplash.com/featured/400x300/?misal-pav",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Thalipeeth",
            "description": "Nutritious multi-grain pancake served with white butter and pickle.",
            "price": 70.0,
            "category": "Sakaalcha Nasta (Breakfast)",
            "image_url": "https://source.unsplash.com/featured/400x300/?thalipeeth,roti",
            "is_available": True,
            "is_bestseller": False
        },
        {
            "name": "Dadpe Pohe",
            "description": "Soft flattened rice mixed with coconut, onions, and lime juice. A light breakfast.",
            "price": 50.0,
            "category": "Sakaalcha Nasta (Breakfast)",
            "image_url": "https://source.unsplash.com/featured/400x300/?poha,breakfast",
            "is_available": True,
            "is_bestseller": False
        },

        # --- SWAYAMPAKGHAR (MAIN COURSE) ---
        {
            "name": "Pithla Bhakri",
            "description": "Rustic chickpea flour curry (Pithla) served with Jowar/Bajra Bhakri and Thecha.",
            "price": 120.0,
            "category": "Swayampakghar (Main Course)",
            "image_url": "https://source.unsplash.com/featured/400x300/?indian-curry,bhakri",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Bharli Vangi",
            "description": "Stuffed baby eggplants cooked in a rich peanut and goda masala gravy.",
            "price": 140.0,
            "category": "Swayampakghar (Main Course)",
            "image_url": "https://source.unsplash.com/featured/400x300/?eggplant-curry",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Mutton Rassa Thali",
            "description": "Kolhapuri style spicy mutton curry (Tambda Rassa) with Bhakri and Rice.",
            "price": 350.0,
            "category": "Swayampakghar (Main Course)",
            "image_url": "https://source.unsplash.com/featured/400x300/?mutton-curry",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Masale Bhaat",
            "description": "Traditional spicy rice cooked with seasonal vegetables and goda masala.",
            "price": 110.0,
            "category": "Swayampakghar (Main Course)",
            "image_url": "https://source.unsplash.com/featured/400x300/?rice-pilaf",
            "is_available": True,
            "is_bestseller": False
        },

        # --- CHAHA-PAANI (SNACKS) ---
        {
            "name": "Kanda Bhaji",
            "description": "Crispy onion fritters, perfect companion for masala chai.",
            "price": 40.0,
            "category": "Chaha-Paani (Snacks)",
            "image_url": "https://source.unsplash.com/featured/400x300/?pakora,fritters",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Sabudana Vada",
            "description": "Crispy sago and peanut patties, served with sweetened curd.",
            "price": 55.0,
            "category": "Chaha-Paani (Snacks)",
            "image_url": "https://source.unsplash.com/featured/400x300/?vada,snack",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Kothimbir Vadi",
            "description": "Steamed and fried coriander and gram flour cakes.",
            "price": 60.0,
            "category": "Chaha-Paani (Snacks)",
            "image_url": "https://source.unsplash.com/featured/400x300/?indian-snack,fried",
            "is_available": True,
            "is_bestseller": False
        },

        # --- GOD-DHODD (DESSERTS) ---
        {
            "name": "Shrikhand Puri",
            "description": "Sweet strained yoghurt flavored with saffron and cardamom, served with puris.",
            "price": 100.0,
            "category": "God-Dhodd (Desserts)",
            "image_url": "https://source.unsplash.com/featured/400x300/?dessert,yogurt",
            "is_available": True,
            "is_bestseller": True
        },
        {
            "name": "Ukadiche Modak",
            "description": "Steamed rice dumplings stuffed with coconut and jaggery (Ganpati Special).",
            "price": 120.0,
            "category": "God-Dhodd (Desserts)",
            "image_url": "https://source.unsplash.com/featured/400x300/?dumplings,sweet",
            "is_available": True,
            "is_bestseller": True
        }
    ]

    for item_data in items:
        item = MenuItem(**item_data)
        db.add(item)
    
    db.commit()
    print("Database seeded with Authentic Maharashtrian Menu!")
    db.close()

if __name__ == "__main__":
    seed_data()
