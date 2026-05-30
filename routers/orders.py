from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from models import User, Order, OrderItem, Product
from schemas import OrderCreate, OrderResponse, OrderItemResponse
from auth import get_current_user, get_current_admin
from services.telegram_bot import send_telegram_alert
import uuid

router = APIRouter(prefix="/api/orders", tags=["Orders"])

def generate_order_number():
    return f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_amount = 0
    order_items_data = []
    
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.title}")
        
        price = product.discount_price if product.discount_price else product.original_price
        item_total = price * item.quantity
        total_amount += item_total
        
        order_items_data.append({
            "product": product,
            "quantity": item.quantity,
            "price": price,
            "color": item.selected_color,
            "size": item.selected_size
        })
        
        product.stock -= item.quantity
    
    order_number = generate_order_number()
    new_order = Order(
        order_number=order_number,
        user_id=current_user.id,
        total_amount=total_amount,
        shipping_address=order_data.shipping_address,
        status="pending"
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"],
            price_at_time=item_data["price"],
            selected_color=item_data["color"],
            selected_size=item_data["size"]
        )
        db.add(order_item)
    
    db.commit()
    
    # Send Telegram alert for new order
    await send_telegram_alert(
        f"🛍️ <b>NEW ORDER CREATED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Order: <code>{order_number}</code>\n"
        f"👤 Customer: {current_user.full_name}\n"
        f"💰 Amount: <b>${total_amount}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 {len(order_data.items)} item(s)\n"
        f"🚚 Shipping: {order_data.shipping_address}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Status: Pending Payment"
    )
    
    db.refresh(new_order)
    
    items = []
    for item_data in order_items_data:
        items.append(OrderItemResponse(
            id=0,
            product_id=item_data["product"].id,
            product_title=item_data["product"].title,
            quantity=item_data["quantity"],
            price_at_time=item_data["price"],
            selected_color=item_data["color"],
            selected_size=item_data["size"]
        ))
    
    return OrderResponse(
        id=new_order.id,
        order_number=new_order.order_number,
        user_id=new_order.user_id,
        total_amount=new_order.total_amount,
        status=new_order.status,
        payment_transaction_id=new_order.payment_transaction_id,
        shipping_address=new_order.shipping_address,
        created_at=new_order.created_at,
        items=items
    )

# ... rest of your orders.py (get_orders, get_order_detail, etc.)