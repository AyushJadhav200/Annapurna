from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, Enum, Date
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, date
import hashlib
import secrets
import enum

from database import Base

# Enums
class SpiceLevel(str, enum.Enum):
    MILD = "Mild"
    MEDIUM = "Medium"
    SPICY = "Spicy"
    EXTRA_SPICY = "Extra Spicy"

class OrderStatus(str, enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    COOKING = "Cooking"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"

class SubscriptionPlan(str, enum.Enum):
    DAILY_DABBA = "Daily Dabba"
    EXECUTIVE_THALI = "Executive Thali"
    WEEKEND_FEAST = "Weekend Feast"

class CoinTransactionType(str, enum.Enum):
    EARNED = "Earned"
    SPENT = "Spent"
    EXPIRED = "Expired"

# Password Utils
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, stored_hash = hashed_password.split('$')
        hash_obj = hashlib.sha256((salt + plain_password).encode())
        return hash_obj.hexdigest() == stored_hash
    except ValueError:
        return False

# User Model - Enhanced
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(15), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    spice_preference = Column(String(20), default="Medium")
    loyalty_coins = Column(Integer, default=0)
    default_address_id = Column(Integer, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_driver = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String(10), nullable=True)
    refresh_token = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", foreign_keys="Order.user_id", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    coin_ledger = relationship("CoinLedger", back_populates="user", cascade="all, delete-orphan")

# Address Model - Enhanced
class Address(Base):
    __tablename__ = "addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    label = Column(String(50))  # Home, Office, Parents
    address_text = Column(Text, nullable=False)
    city = Column(String(50), default="Pune")
    is_default = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    pincode = Column(String(10), nullable=True)
    
    user = relationship("User", back_populates="addresses")

# MenuItem Model - Enhanced
class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String(50))
    image_url = Column(String(255))
    
    # Kitchen control
    is_available = Column(Boolean, default=True)  # Master switch
    stock_count = Column(Integer, default=100)    # Inventory
    preparation_time_mins = Column(Integer, default=20)
    
    # Marketing Flags
    is_bestseller = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    
    ratings = relationship("Rating", back_populates="menu_item")

    @property
    def average_rating(self):
        if not self.ratings:
            return 0
        return sum(r.score for r in self.ratings) / len(self.ratings)
    
    @property
    def rating_count(self):
        return len(self.ratings)

# Order Model - Enhanced
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float, nullable=False)
    status = Column(String(30), default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    items_summary = Column(Text)
    
    # New fields
    delivery_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)
    spice_level = Column(String(20), nullable=True)  # From user preference or custom
    loyalty_coins_earned = Column(Integer, default=0)
    loyalty_coins_spent = Column(Integer, default=0)
    discount_amount = Column(Float, default=0)
    delivery_fee = Column(Float, default=30)
    gst_amount = Column(Float, default=0)
    
    # Payment
    payment_status = Column(String(20), default="Pending")  # Pending, Paid, Failed
    payment_method = Column(String(50), default="Cash")    # Cash, UPI, Cards
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    
    # Delivery tracking
    estimated_delivery = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Driver assignment
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # From subscription?
    is_subscription_order = Column(Boolean, default=False)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="orders")
    driver = relationship("User", foreign_keys=[driver_id])
    items = relationship("OrderItem", back_populates="order")

# Rating Model - NEW
class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    score = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    menu_item = relationship("MenuItem", back_populates="ratings")
    order = relationship("Order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer, default=1)
    price_at_order = Column(Float)  # Capture price at time of order
    
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")

# Subscription Model - NEW
class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_type = Column(String(30), nullable=False)  # Daily Dabba, Executive Thali, Weekend Feast
    
    is_active = Column(Boolean, default=True)
    start_date = Column(Date, default=date.today)
    end_date = Column(Date, nullable=True)  # None = ongoing
    
    # Pause functionality
    paused_from = Column(Date, nullable=True)
    paused_until = Column(Date, nullable=True)
    
    # Delivery preferences
    delivery_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)
    preferred_time = Column(String(20), default="12:30 PM")  # Lunch time
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="subscriptions")

# Loyalty Coin Ledger - NEW
class CoinLedger(Base):
    __tablename__ = "coin_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False)  # Positive for earned, negative for spent
    transaction_type = Column(String(20), nullable=False)  # Earned, Spent, Expired
    description = Column(String(200))  # e.g., "Order #123", "Discount on Order #456"
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="coin_ledger")

# Kitchen Status - For order throttling
class KitchenStatus(Base):
    __tablename__ = "kitchen_status"
    
    id = Column(Integer, primary_key=True, index=True)
    is_open = Column(Boolean, default=True)
    current_load = Column(Integer, default=0)  # Orders in last 10 mins
    base_eta_mins = Column(Integer, default=30)
    extra_eta_mins = Column(Integer, default=0)  # Added when overloaded
    updated_at = Column(DateTime, default=datetime.utcnow)

# Promo Code Model - NEW
class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    discount_percentage = Column(Integer, default=0)
    max_discount_amount = Column(Float, nullable=True)
    min_order_amount = Column(Float, default=0)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, nullable=True)  # Total times can be used
    usage_count = Column(Integer, default=0)      # Current times used
    
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

# Partner Inquiry Model - NEW
class PartnerInquiry(Base):
    __tablename__ = "partner_inquiries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    business_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="Pending")  # Pending, Contacted, Rejected
    created_at = Column(DateTime, default=datetime.utcnow)
