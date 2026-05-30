from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class UserRoleEnum(str, Enum):
    user = "user"
    admin = "admin"

class OrderStatusEnum(str, Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

# User Schemas
class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    gender: Optional[GenderEnum] = None
    phone_number: str = Field(..., pattern=r"^[0-9]{8,15}$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    gender: Optional[GenderEnum]
    phone_number: Optional[str]
    email: EmailStr
    role: UserRoleEnum
    picture: Optional[str] = None
    is_google_user: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

# Category Schemas
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class CategoryResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Product Schemas
class ProductCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    original_price: float = Field(..., gt=0)
    discount_price: Optional[float] = Field(None, gt=0)
    category_id: int
    description: Optional[str] = None
    colors: Optional[List[str]] = None
    sizes: Optional[List[str]] = None
    stock: int = Field(default=0, ge=0)

class ProductResponse(BaseModel):
    id: int
    title: str
    original_price: float
    discount_price: Optional[float]
    description: Optional[str]
    main_image: Optional[str]
    sub_images: Optional[List[str]]
    colors: Optional[List[str]]
    sizes: Optional[List[str]]
    category_id: int
    category_name: Optional[str]
    stock: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Order Schemas
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    selected_color: Optional[str] = None
    selected_size: Optional[str] = None

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    shipping_address: str = Field(..., min_length=5)

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_title: Optional[str]
    quantity: int
    price_at_time: float
    selected_color: Optional[str]
    selected_size: Optional[str]
    
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    order_number: str
    user_id: int
    total_amount: float
    status: OrderStatusEnum
    payment_transaction_id: Optional[str]
    shipping_address: Optional[str]
    created_at: datetime
    items: List[OrderItemResponse] = []
    
    class Config:
        from_attributes = True

# Payment Schemas
class PaymentRequest(BaseModel):
    order_id: int

class PaymentVerify(BaseModel):
    transaction_id: str

class PaymentResponse(BaseModel):
    payment_url: str
    order_id: int
    amount: float