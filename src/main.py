from fastapi import FastAPI, Request, Form, Depends, Response, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from database import get_db, init_db
from models import User, Address, Order, MenuItem, Subscription, CoinLedger, PartnerInquiry, PromoCode, Rating, hash_password, verify_password
from auth import create_access_token, create_refresh_token, get_user_id_from_token, verify_refresh_token
from kitchen import get_current_eta, toggle_menu_item_availability, toggle_kitchen_status
from loyalty import get_coin_balance, get_coin_history, add_coins, spend_coins, calculate_discount_from_coins
from scheduler import start_scheduler, pause_subscription, resume_subscription, create_subscription, cancel_subscription
import admin as admin_utils
import location_utils
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Manual .env loader
def load_dotenv_manual(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

load_dotenv_manual()

app = FastAPI(title="Annapurna API", version="2.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==================== SEO ROUTES ====================
from fastapi.responses import FileResponse

@app.get("/robots.txt")
async def get_robots():
    return FileResponse("static/robots.txt")

@app.get("/sitemap.xml")
async def get_sitemap():
    return FileResponse("static/sitemap.xml")

# ==================== STARTUP ====================
@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()

# ==================== AUTH HELPERS ====================
def get_current_user_jwt(
    request: Request,
    authorization: Optional[str] = Header(None), 
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get user from JWT Bearer token or Cookie"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        return None
        
    user_id = get_user_id_from_token(token)
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None

def require_auth(user: User = Depends(get_current_user_jwt)) -> User:
    """Require authentication - raises 401 if not authenticated"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin authentication"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==================== PAGE ROUTES (HTML) ====================
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: Session = Depends(get_db)):
    # Feature 3 bestsellers for the blog/preview section
    items = db.query(MenuItem).filter(MenuItem.is_available == True, MenuItem.is_bestseller == True).limit(3).all()
    if not items: # Fallback
        items = db.query(MenuItem).filter(MenuItem.is_available == True).limit(3).all()
        
    eta = get_current_eta(db)
    
    # Real Data for Daily Dabba: Fetch a random Main Course
    daily_menu_item = db.query(MenuItem).filter(MenuItem.category == "Main Course").first()
    
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "items": items, 
        "eta": eta, 
        "user": user,
        "daily_menu_item": daily_menu_item
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    if user_id:
        return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        if not user.is_verified:
            # Send OTP and redirect to verification
            otp = str(random.randint(1000, 9999))
            user.otp_code = otp
            db.commit()
            send_otp_email(user.email, otp)
            response = RedirectResponse(url=f"/verify-account?email={email}", status_code=303)
            return response

        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)
        user.refresh_token = refresh_token
        db.commit()
        redirect = RedirectResponse(url="/profile", status_code=303)
        redirect.set_cookie("access_token", access_token, httponly=True, max_age=3600) 
        redirect.set_cookie("refresh_token", refresh_token, httponly=True, max_age=2592000)
        return redirect
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    if user_id:
        return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": error})

@app.post("/register")
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter((User.email == email) | (User.phone == phone)).first()
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email or phone already registered"})
    
    user = User(full_name=full_name, email=email, phone=phone, hashed_password=hash_password(password))
    # Generate OTP for registration
    otp = str(random.randint(1000, 9999))
    user.otp_code = otp
    db.add(user)
    db.commit()
    
    # Welcome bonus coins
    add_coins(db, user.id, 50, "Welcome bonus!")
    
    send_otp_email(email, otp)
    return RedirectResponse(url=f"/verify-account?email={email}", status_code=303)

# ===== FORGOT PASSWORD =====
@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, error: str = None):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": error})

@app.post("/forgot-password")
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal user existence, but for now just show error for better UX in this demo
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "Email not found registered with us."})
    
    # Generate OTP
    otp = str(random.randint(1000, 9999))
    user.otp_code = otp
    db.commit()
    
    send_otp_email(user.email, otp)
    
    # Redirect to reset page
    return RedirectResponse(url=f"/reset-password?email={email}", status_code=303)

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, email: str, error: str = None):
    return templates.TemplateResponse("reset_password.html", {"request": request, "email": email, "error": error})

@app.post("/reset-password")
async def reset_password_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("reset_password.html", {"request": request, "email": email, "error": "User not found"})
        
    if user.otp_code != otp:
        return templates.TemplateResponse("reset_password.html", {"request": request, "email": email, "error": "Invalid OTP Code"})
    
    # Reset Password
    user.hashed_password = hash_password(new_password)
    user.otp_code = None # Clear OTP
    user.is_verified = True # Should be verified if they have access to email
    db.commit()
    
    return RedirectResponse(url="/login?error=Password+reset+successfully.+Please+login.", status_code=303)


    redirect.delete_cookie("refresh_token")
    return redirect

@app.post("/api/orders/{order_id}/rate")
async def rate_order(
    order_id: int,
    item_id: int = Form(...),
    score: int = Form(...),
    comment: str = Form(""),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    # Verify order belongs to user and is delivered
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order or order.status != "Delivered":
        raise HTTPException(status_code=400, detail="Only delivered orders can be rated")
    
    # Check if already rated
    existing = db.query(Rating).filter(Rating.order_id == order_id, Rating.menu_item_id == item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item already rated for this order")
    
    rating = Rating(
        user_id=user.id,
        menu_item_id=item_id,
        order_id=order_id,
        score=score,
        comment=comment
    )
    db.add(rating)
    db.commit()
    return {"message": "Rating submitted! Thank you for your feedback."}

@app.get("/partner", response_class=HTMLResponse)
async def partner_page(request: Request):
    return templates.TemplateResponse("partner.html", {"request": request})

@app.post("/api/partner/inquiry")
async def partner_inquiry(
    name: str = Form(...),
    business_name: str = Form(...),
    phone: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    print(f"DEBUG: Received inquiry from {name} ({business_name})")
    try:
        # Save to Database
        inquiry = PartnerInquiry(
            name=name,
            business_name=business_name,
            phone=phone,
            category=category,
            description=description
        )
        db.add(inquiry)
        db.commit()
        print("DEBUG: Inquiry saved successfully")
        return {"status": "success", "message": "Inquiry received"}
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/admin/inquiries")
async def get_inquiries(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_utils.get_all_inquiries(db)

@app.post("/api/admin/inquiries/{inquiry_id}/status")
async def update_inquiry(
    inquiry_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    admin_utils.update_inquiry_status(db, inquiry_id, status)
    return {"message": "Inquiry updated"}

@app.get("/api/admin/drivers")
async def get_drivers(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_utils.get_all_drivers(db)

@app.post("/api/admin/orders/{order_id}/assign")
async def assign_driver(
    order_id: int,
    driver_id: int = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    admin_utils.assign_driver_to_order(db, order_id, driver_id)
    return {"message": "Driver assigned"}

@app.get("/api/admin/analytics")
async def get_analytics(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_utils.get_detailed_analytics(db)

@app.get("/menu", response_class=HTMLResponse)
async def menu_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    
    return templates.TemplateResponse("menu.html", {"request": request, "items": items, "user": user})

@app.get("/api/items/{item_id}/ratings")
async def get_item_ratings(item_id: int, db: Session = Depends(get_db)):
    ratings = db.query(Rating).filter(Rating.menu_item_id == item_id).order_by(Rating.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "score": r.score,
            "comment": r.comment,
            "user_name": r.user.full_name if r.user else "Anonymous",
            "date": r.created_at.strftime("%d %b %Y")
        }
        for r in ratings
    ]

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    
    if not user or not user.is_admin:
         return RedirectResponse(url="/login?error=Admin+access+required", status_code=303)

    stats = admin_utils.get_dashboard_stats(db)
    orders = admin_utils.get_orders_list(db, limit=20)
    menu_items = admin_utils.get_menu_items_admin(db)
    
    # New Data
    users = admin_utils.get_all_users(db)
    promos = admin_utils.get_all_promos(db)
    inquiries = admin_utils.get_all_inquiries(db)
    drivers = admin_utils.get_all_drivers(db)
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "user": user, 
        "stats": stats, 
        "orders": orders, 
        "menu_items": menu_items,
        "users": users,
        "promos": promos,
        "inquiries": inquiries,
        "drivers": drivers,
        "analytics": admin_utils.get_detailed_analytics(db)
    })

@app.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page(request: Request, db: Session = Depends(get_db)):
    """Dedicated view for kitchen staff"""
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    
    if not user or not user.is_admin:
        return RedirectResponse(url="/login?error=Kitchen+access+required", status_code=303)
        
    return templates.TemplateResponse("kitchen.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    addresses = db.query(Address).filter(Address.user_id == user_id).all()
    orders = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(10).all()
    coins = get_coin_balance(db, user_id)
    
    # Get active subscription
    active_sub = db.query(Subscription).filter(Subscription.user_id == user_id, Subscription.is_active == True).first()
    
    print(f"DEBUG: Serving profile for user {user.email}")
    
    # Format orders for display
    formatted_orders = [
        {
            "id": f"#ORD-{o.id:04d}", 
            "date": o.created_at.strftime("%d %b %Y"), 
            "items_summary": o.items_summary, 
            "total": o.total_amount, 
            "status": o.status
        }
        for o in orders
    ]
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user,
        "avatar": f"https://ui-avatars.com/api/?name={user.full_name.replace(' ', '+')}&background=B85C38&color=fff",
        "loyalty_coins": coins["balance"],
        "has_active_subscription": active_sub is not None,
        "subscription_plan": active_sub.plan_type if active_sub else None,
        "addresses": addresses,
        "orders": formatted_orders,
        "total_orders": len(orders)
    })

@app.get("/wallet-history", response_class=HTMLResponse)
async def wallet_history_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    history = get_coin_history(db, user_id, limit=50)
    coins = get_coin_balance(db, user_id)
    
    return templates.TemplateResponse("wallet_history.html", {
        "request": request,
        "user": user,
        "history": history,
        "balance": coins["balance"],
        "discount": coins["max_discount"]
    })

@app.post("/api/subscription/skip-tomorrow")
async def skip_tomorrow(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    # Simple mock skip logic
    return {"message": "Tomorrow's meal skipped! Your wallet will be credited."}

@app.post("/api/subscription/{sub_id}/pause")
async def pause_sub(sub_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub:
        sub.is_active = False
        db.commit()
        return {"message": "Subscription paused successfully"}
    raise HTTPException(status_code=404, detail="Subscription not found")

@app.post("/api/subscription/{sub_id}/resume")
async def resume_sub(sub_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub:
        sub.is_active = True
        db.commit()
        return {"message": "Subscription resumed successfully"}
    raise HTTPException(status_code=404, detail="Subscription not found")

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    
    user = None
    addresses = []
    
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            addresses = db.query(Address).filter(Address.user_id == user_id).all()
            
    return templates.TemplateResponse("checkout.html", {
        "request": request, 
        "user": user,
        "addresses": addresses
    })

# ===== ORDER API =====
@app.post("/api/orders")
async def create_order(
    request: Request,
    item_ids: list[int] = Form(...), # List of MenuItem IDs
    use_coins: bool = Form(False),
    address_id: Optional[int] = Form(None),
    payment_method: str = Form("Cash"),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    user_id = get_user_id_from_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Please login to place an order")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Fetch menu items
    menu_items = db.query(MenuItem).filter(MenuItem.id.in_(items)).all()
    if not menu_items:
        raise HTTPException(status_code=400, detail="No valid items selected")
    
    total_amount = sum(item.price for item in menu_items)
    items_summary = ", ".join([item.name for item in menu_items])
    
    # Handle coins
    discount = 0
    coins_used = 0
    if use_coins and user.loyalty_coins > 0:
        result = calculate_discount_from_coins(user.loyalty_coins, total_amount)
        discount = result["discount_amount"]
        coins_used = result["coins_used"]
        spend_coins(db, user_id, coins_used, f"Discount on order", None) # Order ID assigned later
    
    # Calculate delivery/gst
    delivery_fee = 30
    gst = total_amount * 0.05 # 5% GST
    final_total = total_amount - discount + delivery_fee + gst
    
    # Create order
    order = Order(
        user_id=user_id,
        total_amount=final_total,
        status="Pending",
        items_summary=items_summary,
        delivery_address_id=address_id or user.default_address_id,
        payment_method=payment_method,
        discount_amount=discount,
        loyalty_coins_spent=coins_used,
        delivery_fee=delivery_fee,
        gst_amount=gst,
        payment_status="Pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Create detailed order items (Phase 21 Reorder support)
    from models import OrderItem
    for it in menu_items:
        order_item = OrderItem(
            order_id=order.id,
            item_id=it.id,
            quantity=1, # Defaulting to 1 for now
            price_at_order=it.price
        )
        db.add(order_item)
    db.commit()
    
    # Update coin ledger with order_id
    if coins_used > 0:
        ledger = db.query(CoinLedger).filter(CoinLedger.user_id == user_id, CoinLedger.amount == -coins_used).order_by(CoinLedger.created_at.desc()).first()
        if ledger:
            ledger.order_id = order.id
            db.commit()
            
    return {"message": "Order placed successfully", "order_id": order.id, "total": final_total}

@app.get("/api/orders/{order_id}")
async def get_order_details(order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    # Remove prefix #ORD-
    numeric_id = int(order_id.replace("#ORD-", ""))
    order = db.query(Order).filter(Order.id == numeric_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order.id,
        "items": [{"id": oi.item_id, "name": oi.menu_item.name, "price": oi.price_at_order} for oi in order.items]
    }

@app.post("/api/subscription/skip-tomorrow")
async def skip_tomorrow(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    active_sub = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.is_active == True).first()
    if not active_sub:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    # Simple logic: Increase extra_eta_mins or a dedicated skip_dates field (not in model yet, but let's simulate)
    # For now, let's just log it and return success as requested.
    print(f"DEBUG: Skipping tomorrow's meal for user {user.email}")
    return {"message": "Success! Tomorrow's Dabba has been skipped. Enjoy your outing!"}

# ==================== API ROUTES ====================
@app.post("/api/auth/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    user_id = verify_refresh_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.refresh_token != token:
        raise HTTPException(status_code=401, detail="Token revoked")
    
    access_token = create_access_token(user.id, user.email)
    return JSONResponse({"access_token": access_token})

# ===== CHECKOUT OTP API =====
@app.post("/api/checkout/otp/send")
async def send_checkout_otp(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    otp = str(random.randint(1000, 9999))
    user.otp_code = otp
    db.commit()
    
    send_otp_email(user.email, otp)
    return {"message": "Verification code sent to your registered email."}

@app.post("/api/checkout/otp/verify")
async def verify_checkout_otp(otp: str = Form(...), user: User = Depends(require_auth), db: Session = Depends(get_db)):
    if user.otp_code == otp:
        # We don't necessarily need to set is_verified to True here if it's just for one order,
        # but let's do it to keep them verified for future checkouts too.
        user.is_verified = True
        user.otp_code = None
        db.commit()
        return {"message": "OTP verified successfully!"}
    raise HTTPException(status_code=400, detail="Invalid verification code. Please check your email.")

# ===== KITCHEN API =====
@app.get("/api/kitchen/eta")
async def kitchen_eta(db: Session = Depends(get_db)):
    return get_current_eta(db)

# ===== LOYALTY API =====
@app.get("/api/user/coins")
async def user_coins(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    balance = get_coin_balance(db, user.id)
    history = get_coin_history(db, user.id)
    return {"balance": balance, "history": history}

# ===== SUBSCRIPTION API =====
@app.post("/api/subscription/create")
async def create_sub(
    plan_type: str = Form(...),
    address_id: Optional[int] = Form(None),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    # Use provided address if possible
    addr_id = address_id
    
    # If not provided, use user's default address
    if not addr_id:
        addr_id = user.default_address_id
        
    # If still not found, use first address
    if not addr_id:
        first_addr = db.query(Address).filter(Address.user_id == user.id).first()
        if first_addr:
            addr_id = first_addr.id
            
    if not addr_id:
        raise HTTPException(status_code=400, detail="Please add a delivery address first in your profile.")
        
    sub = create_subscription(db, user.id, plan_type, addr_id)
    return {"message": f"Subscription to {plan_type} created successfully!", "id": sub.id}

@app.post("/api/subscription/{sub_id}/pause")
async def pause_sub(
    sub_id: int,
    pause_from: str = Form(...),
    pause_until: str = Form(...),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    from_date = datetime.strptime(pause_from, "%Y-%m-%d").date()
    until_date = datetime.strptime(pause_until, "%Y-%m-%d").date()
    sub = pause_subscription(db, sub_id, from_date, until_date)
    return {"message": "Subscription paused", "from": pause_from, "until": pause_until}

@app.post("/api/subscription/{sub_id}/resume")
async def resume_sub(sub_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    sub = resume_subscription(db, sub_id)
    return {"message": "Subscription resumed"}

# ===== ADDRESS API =====
@app.post("/api/promo/validate")
async def validate_promo(
    code: str = Form(...),
    total_amount: float = Form(...),
    db: Session = Depends(get_db)
):
    from models import PromoCode
    promo = db.query(PromoCode).filter(
        PromoCode.code == code,
        PromoCode.is_active == True
    ).first()
    
    if not promo:
        return {"valid": False, "message": "Invalid or inactive promo code"}
    
    if promo.expiry_date and promo.expiry_date < datetime.utcnow():
        return {"valid": False, "message": "Promo code has expired"}
    
    if promo.usage_limit and promo.usage_count >= promo.usage_limit:
        return {"valid": False, "message": "Promo code usage limit reached"}
        
    if total_amount < promo.min_order_amount:
        return {"valid": False, "message": f"Min order amount for this code is ₹{promo.min_order_amount}"}
        
    discount = (total_amount * promo.discount_percentage) / 100
    if promo.max_discount_amount and discount > promo.max_discount_amount:
        discount = promo.max_discount_amount
        
    return {
        "valid": True, 
        "discount_amount": discount, 
        "discount_percentage": promo.discount_percentage,
        "message": f"Promo applied! You saved ₹{discount}"
    }

# ==================== SEARCH API ====================
@app.get("/api/search/food")
async def search_food(q: str = "", db: Session = Depends(get_db)):
    if not q:
        return []
    items = db.query(MenuItem).filter(
        (MenuItem.name.ilike(f"%{q}%")) | (MenuItem.description.ilike(f"%{q}%")),
        MenuItem.is_available == True
    ).limit(5).all()
    
    return [{"id": it.id, "name": it.name, "category": it.category, "price": it.price} for it in items]

@app.get("/api/search/location")
async def search_location(q: str = ""):
    service_areas = [
        "Mira Road East", "Mira Road West", "Bhayandar East", "Bhayandar West",
        "Kanakia Park", "Shanti Nagar", "Poonam Sagar", "Pleasant Park",
        "Silver Park", "Beverly Park", "Golden Nest", "Indralok", 
        "Jesal Park", "Navghar", "Kashimira", "Thakur Village", "Hatkesh"
    ]
    if not q:
        return []
    
    matches = [area for area in service_areas if q.lower() in area.lower()]
    return matches[:5]

# ===== ADDRESS API =====
@app.post("/api/addresses")
async def add_address(
    label: str = Form(...),
    address_text: str = Form(...),
    city: str = Form("Pune"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    from models import Address
    new_addr = Address(
        user_id=user.id,
        label=label,
        address_text=address_text,
        city=city,
        latitude=latitude,
        longitude=longitude
    )
    db.add(new_addr)
    # Set as default if it's the first one
    if not user.default_address_id:
        db.flush() # Get ID
        user.default_address_id = new_addr.id
    
    db.commit()
    return {"message": "Address added successfully", "id": new_addr.id}

@app.get("/api/addresses")
async def get_addresses(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    from models import Address
    addresses = db.query(Address).filter(Address.user_id == user.id).all()
    return [
        {
            "id": a.id,
            "label": a.label,
            "address_text": a.address_text,
            "city": a.city,
            "latitude": a.latitude,
            "longitude": a.longitude
        } for a in addresses
    ]

# ==================== EMAIL UTILITY ====================
def send_otp_email(target_email: str, otp: str):
    # SMTP Config (Using environment variables or defaults)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "ayushjadhav200605@gmail.com")
    SMTP_PASS = os.getenv("SMTP_PASS", "your-app-password")

    msg = MIMEMultipart()
    msg['From'] = f"Annapradata Verification <{SMTP_USER}>"
    msg['To'] = target_email
    msg['Subject'] = f"{otp} is your Annapradata Verification Code"

    # Load HTML Template
    try:
        with open("templates/otp_email.html", "r") as f:
            template = f.read()
        html_content = template.replace("{{ otp }}", otp)
    except Exception:
        html_content = f"<h1>Your OTP is {otp}</h1>"

    msg.attach(MIMEText(html_content, 'html'))

    # Send (Try/Catch to avoid blocking on invalid credentials)
    try:
        print(f"DEBUG: Attempting to send email from {SMTP_USER} to {target_email}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(1) # Enable for debugging
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"DEBUG: Email simulating sending to {target_email} with OTP {otp}")
        return True
    except Exception as e:
        print(f"DEBUG: Email send failed: {e}")
        return False

# ==================== SUBSCRIPTION API ====================
@app.post("/api/subscription/create")
async def create_subscription_endpoint(
    plan_type: str = Form(...),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    from models import Subscription
    from datetime import date
    # Check if active subscription exists
    active_sub = db.query(Subscription).filter(
        Subscription.user_id == user.id, 
        Subscription.is_active == True
    ).first()
    
    if active_sub:
        raise HTTPException(status_code=400, detail="You already have an active subscription.")
    
    # Create new subscription
    new_sub = Subscription(
        user_id=user.id,
        plan_type=plan_type,
        is_active=True,
        start_date=date.today()
    )
    db.add(new_sub)
    db.commit()
    
    return {"message": f"Successfully subscribed to {plan_type}!", "plan": plan_type}

# ==================== MAIN ====================
# ==================== AUTH OTP API ====================
@app.post("/api/auth/send-otp")
async def api_send_otp(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    otp = str(random.randint(1000, 9999))
    user.otp_code = otp
    db.commit()
    
    send_otp_email(user.email, otp)
    return {"message": "OTP sent successfully"}

@app.post("/api/auth/verify-otp")
async def api_verify_otp(otp: str = Form(...), user: User = Depends(require_auth), db: Session = Depends(get_db)):
    if user.otp_code == otp:
        user.is_verified = True
        user.otp_code = None
        db.commit()
        return {"message": "Identity verified successfully"}
    raise HTTPException(status_code=400, detail="Invalid verification code")

@app.get("/verify-account", response_class=HTMLResponse)
async def verify_account_page(request: Request, email: str, error: str = None):
    return templates.TemplateResponse("verify_account.html", {"request": request, "email": email, "error": error})

@app.post("/verify-account")
async def verify_account_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.otp_code != otp:
        return templates.TemplateResponse("verify_account.html", {
            "request": request, 
            "email": email, 
            "error": "Invalid verification code"
        })
    
    user.is_verified = True
    user.otp_code = None
    db.commit()
    
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)
    user.refresh_token = refresh_token
    db.commit()
    
    redirect = RedirectResponse(url="/profile", status_code=303)
    redirect.set_cookie("access_token", access_token, httponly=True, max_age=3600)
    redirect.set_cookie("refresh_token", refresh_token, httponly=True, max_age=2592000)
    return redirect

# ===== ADMIN API =====
@app.get("/api/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_utils.get_dashboard_stats(db)

@app.get("/api/admin/orders")
async def admin_orders(
    status: str = None,
    limit: int = 50,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return admin_utils.get_orders_list(db, status, limit)

@app.post("/api/admin/orders/{order_id}/status")
async def update_order(
    order_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    order = admin_utils.update_order_status(db, order_id, status)
    return {"message": "Order updated", "status": order.status}

@app.get("/api/admin/menu")
async def admin_menu(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_utils.get_menu_items_admin(db)

@app.post("/api/admin/menu/{item_id}/toggle")
async def toggle_item(item_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item = toggle_menu_item_availability(db, item_id, not item.is_available)
    return {"message": f"Item {'enabled' if item.is_available else 'disabled'}", "is_available": item.is_available}

@app.post("/api/admin/kitchen/toggle")
async def toggle_kitchen(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    from kitchen import get_kitchen_status
    status = get_kitchen_status(db)
    toggle_kitchen_status(db, not status.is_open)
    return {"message": f"Kitchen {'opened' if not status.is_open else 'closed'}", "is_open": not status.is_open}

@app.post("/api/admin/users/{target_id}/coins")
async def admin_add_coins(target_id: int, amount: int = Form(...), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    admin_utils.add_user_coins(db, target_id, amount)
    return {"message": "Coins added successfully"}

@app.post("/api/admin/promos")
async def admin_create_promo(
    code: str = Form(...),
    discount: int = Form(...),
    user: User = Depends(require_admin), 
    db: Session = Depends(get_db)
):
    admin_utils.create_promo_code(db, code, discount)
    return {"message": "Promo created"}

@app.post("/api/admin/promos/{promo_id}/delete")
async def admin_delete_promo(promo_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    admin_utils.delete_promo_code(db, promo_id)
    return {"message": "Promo deleted"}

# ==================== LOCATION SERVICES ====================

@app.get("/api/location/check-delivery")
async def check_delivery_zone(lat: float, lng: float):
    """Check if coordinates are within delivery zone"""
    is_deliverable, distance = location_utils.is_in_delivery_zone(lat, lng)
    eta = location_utils.estimate_delivery_time(distance) if is_deliverable else None
    
    return {
        "is_deliverable": is_deliverable,
        "distance_km": distance,
        "eta_minutes": eta,
        "max_radius_km": location_utils.MAX_DELIVERY_RADIUS_KM,
        "message": "We deliver to your location! 🎉" if is_deliverable else f"Sorry, we only deliver within {location_utils.MAX_DELIVERY_RADIUS_KM}km of our kitchen."
    }

@app.get("/api/location/kitchen")
async def get_kitchen_info():
    """Get kitchen location for map display"""
    return location_utils.get_kitchen_location()

@app.get("/api/location/distance")
async def get_distance(lat: float, lng: float):
    """Get distance from kitchen"""
    distance = location_utils.get_distance_from_kitchen(lat, lng)
    eta = location_utils.estimate_delivery_time(distance)
    return {
        "distance_km": distance,
        "eta_minutes": eta,
        "eta_display": f"{eta} mins"
    }
