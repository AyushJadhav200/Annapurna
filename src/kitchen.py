"""Kitchen Control System for Annapurna"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Order, MenuItem, KitchenStatus

# Constants
ORDER_THROTTLE_WINDOW_MINS = 10
ORDER_THROTTLE_THRESHOLD = 20
EXTRA_ETA_PER_OVERLOAD = 15  # mins

def get_kitchen_status(db: Session) -> KitchenStatus:
    """Get or create kitchen status"""
    status = db.query(KitchenStatus).first()
    if not status:
        status = KitchenStatus()
        db.add(status)
        db.commit()
        db.refresh(status)
    return status

def update_kitchen_load(db: Session) -> int:
    """Count orders in last 10 mins and update load"""
    window_start = datetime.utcnow() - timedelta(minutes=ORDER_THROTTLE_WINDOW_MINS)
    recent_orders = db.query(Order).filter(
        Order.created_at >= window_start,
        Order.status.in_(["Pending", "Confirmed", "Cooking"])
    ).count()
    
    status = get_kitchen_status(db)
    status.current_load = recent_orders
    
    # Calculate extra ETA if overloaded
    if recent_orders > ORDER_THROTTLE_THRESHOLD:
        overload_factor = (recent_orders - ORDER_THROTTLE_THRESHOLD) // 5
        status.extra_eta_mins = min(overload_factor * EXTRA_ETA_PER_OVERLOAD, 60)  # Max 60 mins extra
    else:
        status.extra_eta_mins = 0
    
    status.updated_at = datetime.utcnow()
    db.commit()
    
    return status.base_eta_mins + status.extra_eta_mins

def get_current_eta(db: Session) -> dict:
    """Get current estimated delivery time"""
    status = get_kitchen_status(db)
    
    # Update load
    eta_mins = update_kitchen_load(db)
    
    return {
        "is_open": status.is_open,
        "current_load": status.current_load,
        "base_eta_mins": status.base_eta_mins,
        "extra_eta_mins": status.extra_eta_mins,
        "total_eta_mins": eta_mins,
        "message": get_eta_message(status.current_load)
    }

def get_eta_message(load: int) -> str:
    """Get user-friendly ETA message"""
    if load <= 10:
        return "Kitchen is ready! Quick delivery expected."
    elif load <= 20:
        return "Moderate rush. Your order will be prioritized."
    elif load <= 30:
        return "High demand! Please allow extra time for freshness."
    else:
        return "Peak hours! Thank you for your patience."

def toggle_menu_item_availability(db: Session, item_id: int, is_available: bool) -> MenuItem:
    """Toggle menu item availability (Admin function)"""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if item:
        item.is_available = is_available
        db.commit()
        db.refresh(item)
    return item

def toggle_kitchen_status(db: Session, is_open: bool) -> KitchenStatus:
    """Toggle kitchen open/closed (Admin function)"""
    status = get_kitchen_status(db)
    status.is_open = is_open
    status.updated_at = datetime.utcnow()
    db.commit()
    return status
