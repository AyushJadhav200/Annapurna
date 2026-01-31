"""Loyalty System for Annapurna"""
from sqlalchemy.orm import Session
from models import User, CoinLedger, Order

# Constants
COINS_PER_100_RUPEES = 10  # Earn 10 coins per ₹100 spent
COINS_TO_RUPEE_RATIO = 10  # 10 coins = ₹1 discount
MAX_DISCOUNT_PERCENTAGE = 20  # Max 20% discount via coins

def calculate_coins_earned(order_amount: float) -> int:
    """Calculate coins earned from an order"""
    return int((order_amount / 100) * COINS_PER_100_RUPEES)

def add_coins(db: Session, user_id: int, amount: int, description: str, order_id: int = None) -> CoinLedger:
    """Add coins to user's account"""
    # Update user balance
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.loyalty_coins += amount
    
    # Create ledger entry
    entry = CoinLedger(
        user_id=user_id,
        amount=amount,
        transaction_type="Earned",
        description=description,
        order_id=order_id
    )
    db.add(entry)
    db.commit()
    return entry

def spend_coins(db: Session, user_id: int, amount: int, description: str, order_id: int = None) -> CoinLedger:
    """Spend coins from user's account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.loyalty_coins < amount:
        return None
    
    user.loyalty_coins -= amount
    
    entry = CoinLedger(
        user_id=user_id,
        amount=-amount,
        transaction_type="Spent",
        description=description,
        order_id=order_id
    )
    db.add(entry)
    db.commit()
    return entry

def get_coin_balance(db: Session, user_id: int) -> dict:
    """Get user's coin balance and potential discount"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"balance": 0, "max_discount": 0}
    
    balance = user.loyalty_coins
    max_discount = balance / COINS_TO_RUPEE_RATIO  # 10 coins = ₹1
    
    return {
        "balance": balance,
        "max_discount": max_discount,
        "description": f"Use {balance} coins for ₹{max_discount:.0f} off"
    }

def get_coin_history(db: Session, user_id: int, limit: int = 10) -> list:
    """Get user's coin transaction history"""
    entries = db.query(CoinLedger).filter(
        CoinLedger.user_id == user_id
    ).order_by(CoinLedger.created_at.desc()).limit(limit).all()
    
    return [
        {
            "amount": e.amount,
            "type": e.transaction_type,
            "description": e.description,
            "date": e.created_at.strftime("%d %b %Y")
        }
        for e in entries
    ]

def calculate_discount_from_coins(coins_to_use: int, order_total: float) -> dict:
    """Calculate discount when using coins"""
    max_discount = coins_to_use / COINS_TO_RUPEE_RATIO
    max_allowed = order_total * (MAX_DISCOUNT_PERCENTAGE / 100)
    
    actual_discount = min(max_discount, max_allowed)
    coins_used = int(actual_discount * COINS_TO_RUPEE_RATIO)
    
    return {
        "coins_used": coins_used,
        "discount_amount": actual_discount,
        "final_total": order_total - actual_discount
    }

def credit_order_coins(db: Session, order: Order) -> int:
    """Credit coins to user after order is delivered"""
    if order.status != "Delivered":
        return 0
    
    coins_earned = calculate_coins_earned(order.total_amount)
    if coins_earned > 0:
        add_coins(
            db, 
            order.user_id, 
            coins_earned, 
            f"Order #{order.id} completed",
            order.id
        )
        order.loyalty_coins_earned = coins_earned
        db.commit()
    
    return coins_earned
