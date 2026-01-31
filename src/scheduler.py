"""Subscription Scheduler for Annapurna Daily Dabba"""
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Subscription, Order, User, Address

scheduler = BackgroundScheduler()

def is_paused(subscription: Subscription) -> bool:
    """Check if subscription is currently paused"""
    today = date.today()
    if subscription.paused_from and subscription.paused_until:
        return subscription.paused_from <= today <= subscription.paused_until
    return False

def get_plan_price(plan_type: str) -> float:
    """Get price for subscription plan"""
    prices = {
        "Daily Dabba": 120,
        "Executive Thali": 180,
        "Weekend Feast": 350
    }
    return prices.get(plan_type, 120)

def generate_daily_orders():
    """Generate orders for all active subscribers - runs at 6 AM"""
    db = SessionLocal()
    try:
        today = date.today()
        weekday = today.weekday()  # 0=Monday, 6=Sunday
        
        # Get all active subscriptions
        active_subs = db.query(Subscription).filter(
            Subscription.is_active == True
        ).all()
        
        orders_created = 0
        
        for sub in active_subs:
            # Skip if paused
            if is_paused(sub):
                continue
            
            # Weekend Feast only on Sat/Sun
            if sub.plan_type == "Weekend Feast" and weekday < 5:
                continue
            
            # Check if order already exists for today
            existing = db.query(Order).filter(
                Order.user_id == sub.user_id,
                Order.is_subscription_order == True,
                Order.created_at >= datetime.combine(today, datetime.min.time())
            ).first()
            
            if existing:
                continue
            
            # Create order
            order = Order(
                user_id=sub.user_id,
                total_amount=get_plan_price(sub.plan_type),
                status="Pending",
                items_summary=f"{sub.plan_type} - Auto Generated",
                is_subscription_order=True,
                delivery_address_id=sub.delivery_address_id,
                delivery_fee=0,  # Free delivery for subscribers
                estimated_delivery=datetime.combine(
                    today, 
                    datetime.strptime(sub.preferred_time, "%I:%M %p").time()
                )
            )
            db.add(order)
            orders_created += 1
        
        db.commit()
        print(f"[{datetime.now()}] 🍱 Generated {orders_created} subscription orders")
        
    finally:
        db.close()

def pause_subscription(db: Session, subscription_id: int, pause_from: date, pause_until: date) -> Subscription:
    """Pause a subscription for a date range"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if sub:
        sub.paused_from = pause_from
        sub.paused_until = pause_until
        db.commit()
        db.refresh(sub)
    return sub

def resume_subscription(db: Session, subscription_id: int) -> Subscription:
    """Resume a paused subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if sub:
        sub.paused_from = None
        sub.paused_until = None
        db.commit()
        db.refresh(sub)
    return sub

def create_subscription(
    db: Session, 
    user_id: int, 
    plan_type: str, 
    address_id: int,
    preferred_time: str = "12:30 PM"
) -> Subscription:
    """Create a new subscription"""
    sub = Subscription(
        user_id=user_id,
        plan_type=plan_type,
        delivery_address_id=address_id,
        preferred_time=preferred_time,
        start_date=date.today()
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

def cancel_subscription(db: Session, subscription_id: int) -> Subscription:
    """Cancel a subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if sub:
        sub.is_active = False
        sub.end_date = date.today()
        db.commit()
        db.refresh(sub)
    return sub

def start_scheduler():
    """Start the background scheduler"""
    # Run at 6:00 AM every day
    scheduler.add_job(
        generate_daily_orders,
        CronTrigger(hour=6, minute=0),
        id="daily_dabba_generator",
        replace_existing=True
    )
    scheduler.start()
    print("🕐 Subscription scheduler started - Daily orders at 6:00 AM")

def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
