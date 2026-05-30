from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User, Order
from schemas import PaymentRequest, PaymentVerify, PaymentResponse
from auth import get_current_user
from services.khqr_payment import khqr_payment
from services.telegram_bot import send_telegram_alert
import json

router = APIRouter(prefix="/api/payment", tags=["Payment"])

@router.post("/initiate", response_model=PaymentResponse)
async def initiate_payment(
    payment_data: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.id == payment_data.order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order cannot be paid")
    
    # Create KHQR payment session
    payment_url = khqr_payment.create_payment_session(
        transaction_id=order.order_number,
        amount=order.total_amount,
        remark=f"Order #{order.order_number}"
    )
    
    return PaymentResponse(
        payment_url=payment_url,
        order_id=order.id,
        amount=order.total_amount
    )

@router.post("/verify")
async def verify_payment(
    verify_data: PaymentVerify,
    db: Session = Depends(get_db)
):
    result = khqr_payment.verify_transaction(verify_data.transaction_id)
    
    if khqr_payment.is_payment_successful(result):
        data = result.get("data", {})
        
        order = db.query(Order).filter(
            Order.order_number == verify_data.transaction_id
        ).first()
        
        if order and order.status == "pending":
            order.status = "paid"
            order.payment_transaction_id = data.get("transaction_id")
            db.commit()
            
            user = db.query(User).filter(User.id == order.user_id).first()
            await send_telegram_alert(
                f"✅ Payment Successful!\n"
                f"Order: {order.order_number}\n"
                f"Customer: {user.full_name if user else 'N/A'}\n"
                f"Amount: ${data.get('amount')}\n"
                f"Transaction ID: {data.get('transaction_id')}"
            )
            
            return {
                "verified": True,
                "order_id": order.id,
                "amount": data.get("amount"),
                "status": "paid"
            }
    
    return {
        "verified": False,
        "message": "Payment verification failed"
    }

@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
        transaction_id = data.get("transaction_id")
        status = data.get("status")
        amount = data.get("amount")
        
        if status == "success" and transaction_id:
            order = db.query(Order).filter(
                Order.order_number == transaction_id
            ).first()
            
            if order and order.status == "pending":
                order.status = "paid"
                order.payment_transaction_id = data.get("payment_id", transaction_id)
                db.commit()
                
                user = db.query(User).filter(User.id == order.user_id).first()
                await send_telegram_alert(
                    f"💰 Payment Received via Webhook!\n"
                    f"Order: {order.order_number}\n"
                    f"Customer: {user.full_name if user else 'N/A'}\n"
                    f"Amount: ${amount}"
                )
                
                return {"status": "success", "message": "Order updated"}
        
        return {"status": "pending", "message": "No action taken"}
    except Exception as e:
        return {"status": "error", "message": str(e)}