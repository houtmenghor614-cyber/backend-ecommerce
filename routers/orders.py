from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, Order, OrderItem, Product
from schemas import OrderCreate, OrderResponse, OrderItemResponse
from auth import get_current_user, get_current_admin
from services.telegram_bot import send_telegram_alert
import uuid
from datetime import datetime

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
    
    await send_telegram_alert(
        f"🛒 New Order Created!\n"
        f"Order: {order_number}\n"
        f"Customer: {current_user.full_name}\n"
        f"Total: ${total_amount}\n"
        f"Status: Pending Payment"
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

@router.get("/", response_model=List[OrderResponse])
async def get_user_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    
    result = []
    for order in orders:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        item_responses = []
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            item_responses.append(OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=product.title if product else None,
                quantity=item.quantity,
                price_at_time=item.price_at_time,
                selected_color=item.selected_color,
                selected_size=item.selected_size
            ))
        
        result.append(OrderResponse(
            id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            total_amount=order.total_amount,
            status=order.status,
            payment_transaction_id=order.payment_transaction_id,
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            items=item_responses
        ))
    
    return result

# Admin endpoint to get all orders
@router.get("/all", response_model=List[OrderResponse])
async def get_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    orders = db.query(Order).all()
    result = []
    for order in orders:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        item_responses = []
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            item_responses.append(OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=product.title if product else None,
                quantity=item.quantity,
                price_at_time=item.price_at_time,
                selected_color=item.selected_color,
                selected_size=item.selected_size
            ))
        
        result.append(OrderResponse(
            id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            total_amount=order.total_amount,
            status=order.status,
            payment_transaction_id=order.payment_transaction_id,
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            items=item_responses
        ))
    
    return result

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    item_responses = []
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        item_responses.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_title=product.title if product else None,
            quantity=item.quantity,
            price_at_time=item.price_at_time,
            selected_color=item.selected_color,
            selected_size=item.selected_size
        ))
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
        payment_transaction_id=order.payment_transaction_id,
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        items=item_responses
    )

@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    valid_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    order.status = status
    db.commit()
    
    await send_telegram_alert(f"📦 Order {order.order_number} status updated to: {status.upper()}")
    
    return {"message": f"Order status updated to {status}"}