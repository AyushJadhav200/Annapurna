"""Admin API utilities for Annapurna"""
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Order, MenuItem, Subscription, KitchenStatus, PromoCode, CoinLedger, CoinTransactionType, PartnerInquiry

def get_dashboard_stats(db: Session) -> dict:
    """Get admin dashboard statistics"""
    today = datetime.combine(date.today(), datetime.min.time())
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's stats
    orders_today = db.query(Order).filter(Order.created_at >= today).count()
    revenue_today = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today,
        Order.payment_status == "Paid"
    ).scalar() or 0
    
    # This week
    orders_week = db.query(Order).filter(Order.created_at >= week_ago).count()
    revenue_week = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= week_ago,
        Order.payment_status == "Paid"
    ).scalar() or 0
    
    # Active subscriptions
    active_subs = db.query(Subscription).filter(Subscription.is_active == True).count()
    
    # Total users
    total_users = db.query(User).count()
    
    # Pending orders
    pending_orders = db.query(Order).filter(
        Order.status.in_(["Pending", "Confirmed", "Cooking"])
    ).count()
    
    # Kitchen status
    kitchen = db.query(KitchenStatus).first()
    
    return {
        "today": {
            "orders": orders_today,
            "revenue": revenue_today
        },
        "this_week": {
            "orders": orders_week,
            "revenue": revenue_week
        },
        "active_subscriptions": active_subs,
        "total_users": total_users,
        "pending_orders": pending_orders,
        "kitchen_status": {
            "is_open": kitchen.is_open if kitchen else True,
            "current_load": kitchen.current_load if kitchen else 0
        }
    }

def get_orders_list(
    db: Session, 
    status: str = None, 
    limit: int = 50, 
    offset: int = 0
) -> list:
    """Get list of orders with optional status filter"""
    query = db.query(Order).order_by(Order.created_at.desc())
    
    if status:
        if "," in status:
            status_list = [s.strip() for s in status.split(",")]
            query = query.filter(Order.status.in_(status_list))
        else:
            query = query.filter(Order.status == status)
    
    orders = query.offset(offset).limit(limit).all()
    
    return [
        {
            "id": o.id,
            "user_id": o.user_id,
            "total": o.total_amount,
            "status": o.status,
            "payment_status": o.payment_status,
            "items": o.items_summary,
            "created_at": o.created_at.isoformat(),
            "is_subscription": o.is_subscription_order
        }
        for o in orders
    ]

def update_order_status(db: Session, order_id: int, new_status: str) -> Order:
    """Update order status (Admin action)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = new_status
        if new_status == "Delivered":
            order.delivered_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order

def get_menu_items_admin(db: Session) -> list:
    """Get all menu items with availability status"""
    items = db.query(MenuItem).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "price": i.price,
            "category": i.category,
            "is_available": i.is_available,
            "stock_count": i.stock_count
        }
        for i in items
    ]

def update_menu_item(
    db: Session, 
    item_id: int, 
    name: str = None,
    price: float = None,
    is_available: bool = None,
    stock_count: int = None
) -> MenuItem:
    """Update menu item details"""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if item:
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        if is_available is not None:
            item.is_available = is_available
        if stock_count is not None:
            item.stock_count = stock_count
        db.commit()
        db.refresh(item)
    return item

def add_menu_item(
    db: Session,
    name: str,
    price: float,
    category: str,
    description: str = ""
) -> MenuItem:
    """Add new menu item"""
    item = MenuItem(
        name=name,
        price=price,
        category=category,
        description=description
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def get_subscription_stats(db: Session) -> dict:
    """Get subscription breakdown by plan"""
    stats = {}
    for plan in ["Daily Dabba", "Executive Thali", "Weekend Feast"]:
        count = db.query(Subscription).filter(
            Subscription.plan_type == plan,
            Subscription.is_active == True
        ).count()
        stats[plan] = count
    
    return stats

# ===== USER MANAGEMENT =====
def get_all_users(db: Session) -> list:
    """Get all users for admin view"""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "coins": u.loyalty_coins,
            "is_verified": u.is_verified,
            "is_admin": u.is_admin,
            "joined_at": u.created_at.strftime("%d %b %Y")
        }
        for u in users
    ]

def add_user_coins(db: Session, user_id: int, amount: int, description: str = "Admin Credit"):
    """Credit coins to a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.loyalty_coins += amount
        # Add to ledger
        tx = CoinLedger(
            user_id=user.id,
            amount=amount,
            transaction_type=CoinTransactionType.EARNED,
            description=description
        )
        db.add(tx)
        db.commit()
    return user

# ===== PROMO CODE MANAGEMENT =====
def get_all_promos(db: Session) -> list:
    """Get all promo codes"""
    promos = db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "discount": f"{p.discount_percentage}%",
            "is_active": p.is_active,
            "usage": f"{p.usage_count}/{p.usage_limit}" if p.usage_limit else f"{p.usage_count}/∞",
            "expiry": p.expiry_date.strftime("%d %b") if p.expiry_date else "No Expiry"
        }
        for p in promos
    ]

def create_promo_code(
    db: Session,
    code: str,
    discount_percentage: int,
    min_order_amount: float = 0,
    max_discount_amount: float = None,
    usage_limit: int = None
):
    """Create a new promo code"""
    promo = PromoCode(
        code=code.upper(),
        discount_percentage=discount_percentage,
        min_order_amount=min_order_amount,
        max_discount_amount=max_discount_amount,
        usage_limit=usage_limit,
        is_active=True
    )
    db.add(promo)
    db.commit()
    return promo

def delete_promo_code(db: Session, promo_id: int):
    """Delete a promo code"""
    promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if promo:
        db.delete(promo)
        db.commit()


# ===== PARTNER INQUIRY MANAGEMENT =====
def get_all_inquiries(db: Session) -> list:
    """Get all partner inquiries"""
    inquiries = db.query(PartnerInquiry).order_by(PartnerInquiry.created_at.desc()).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "business": i.business_name,
            "phone": i.phone,
            "category": i.category,
            "description": i.description,
            "status": i.status,
            "created_at": i.created_at.strftime("%d %b, %H:%M")
        }
        for i in inquiries
    ]

def update_inquiry_status(db: Session, inquiry_id: int, new_status: str):
    """Update status of an inquiry"""
    inquiry = db.query(PartnerInquiry).filter(PartnerInquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.status = new_status
        db.commit()
    return inquiry

# ===== DRIVER MANAGEMENT =====
def get_all_drivers(db: Session) -> list:
    """Get all registered drivers"""
    drivers = db.query(User).filter(User.is_driver == True).all()
    return [
        {"id": d.id, "name": d.full_name, "phone": d.phone}
        for d in drivers
    ]

def assign_driver_to_order(db: Session, order_id: int, driver_id: int):
    """Assign a driver to an order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.driver_id = driver_id
        db.commit()
    return order

# ===== ANALYTICS & TRENDS =====
def get_detailed_analytics(db: Session) -> dict:
    """Calculate revenue trends and top items for the last 30 days"""
    from models import OrderItem
    
    today = date.today()
    last_30_days = today - timedelta(days=30)
    
    # 1. Daily Revenue Chart Data (Last 7 days)
    revenue_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        
        daily_rev = db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= datetime.combine(day, datetime.min.time()),
            Order.created_at < datetime.combine(next_day, datetime.min.time()),
            Order.payment_status == "Paid"
        ).scalar() or 0
        
        revenue_chart.append({
            "date": day.strftime("%a"),
            "amount": float(daily_rev)
        })

    # 2. Top 5 Selling Items
    top_items_raw = db.query(
        MenuItem.name,
        func.count(OrderItem.id).label("total_sold")
    ).join(OrderItem).group_by(MenuItem.id).order_by(func.count(OrderItem.id).desc()).limit(5).all()
    
    top_items = [{"name": name, "sold": count} for name, count in top_items_raw]

    # 3. Order Status Distribution
    status_counts = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    distribution = {status: count for status, count in status_counts}

    return {
        "revenue_chart": revenue_chart,
        "top_items": top_items,
        "distribution": distribution
    }
