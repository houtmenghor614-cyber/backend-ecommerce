from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse
from auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_admin
from services.telegram_bot import send_telegram_alert

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    new_user = User(
        full_name=user_data.full_name,
        gender=user_data.gender,
        phone_number=user_data.phone_number,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        is_google_user=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    await send_telegram_alert(f"🆕 New user registered: {new_user.full_name} ({new_user.email})")
    
    return new_user

@router.post("/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    print(f"Login attempt for: {user_data.email}")  # Debug
    
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user:
        print("User not found")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user_data.password, user.password_hash):
        print("Password incorrect")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user.id})
    
    print(f"Login successful for: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role,
            "picture": user.picture,
            "is_google_user": user.is_google_user
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    users = db.query(User).all()
    return users