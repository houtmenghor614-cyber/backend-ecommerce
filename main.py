from fastapi import FastAPI, HTTPException, Form, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
import shutil
import uuid
import json
import hashlib
import requests
from datetime import datetime
import secrets

app = FastAPI(title="MENGHOR CLOTHES")

# CORS - Allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create folders
os.makedirs("backup", exist_ok=True)
os.makedirs("uploads/products", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

DB_PATH = "backup/file.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT UNIQUE,
            phone_number TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            original_price REAL,
            discount_price REAL,
            category_id INTEGER,
            description TEXT,
            stock INTEGER,
            colors TEXT,
            sizes TEXT,
            size_stock TEXT,
            main_image TEXT,
            sub_images TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Orders table with all shipping fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            user_id INTEGER,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            payment_transaction_id TEXT,
            shipping_address TEXT,
            full_name TEXT,
            phone_number TEXT,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Order items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            product_title TEXT,
            quantity INTEGER,
            price_at_time REAL,
            selected_color TEXT,
            selected_size TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')
    
    # Insert admin if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@dynastore.com'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (full_name, email, phone_number, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                       ('Administrator', 'admin@dynastore.com', '0123456789', 'admin123', 'admin'))
        print("✅ Admin created")
    
    # Insert default categories
    default_cats = ['Men', 'Women', 'Kids', 'Clothes', 'Accessories', 'Shoes']
    for cat in default_cats:
        cursor.execute("SELECT * FROM categories WHERE name = ?", (cat,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
            print(f"✅ Category: {cat}")
    
    conn.commit()
    conn.close()
    print("✅ Database ready!")

init_db()

# ========== MODELS ==========
class LoginData(BaseModel):
    email: str
    password: str

class RegisterData(BaseModel):
    full_name: str
    email: str
    phone_number: str
    password: str
    confirm_password: str

class CategoryCreate(BaseModel):
    name: str

class ProductCreate(BaseModel):
    title: str
    original_price: float
    discount_price: Optional[float] = 0
    category_id: int
    description: Optional[str] = ""
    stock: int = 0
    colors: Optional[str] = ""
    sizes: Optional[str] = ""
    size_stock: Optional[str] = "{}"

class OrderItemCreate(BaseModel):
    product_id: int
    product_title: Optional[str] = None
    quantity: int
    selected_color: Optional[str] = None
    selected_size: Optional[str] = None
    price: Optional[float] = None

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    full_name: str
    phone_number: str
    shipping_address: str
    city: str
    total_amount: float

class PaymentRequest(BaseModel):
    order_id: int

class PaymentVerify(BaseModel):
    transaction_id: str

# ========== KHQR CONFIGURATION ==========
KHQR_PROFILE_ID = "Y0xL0p6WlNruUhlnj51p4c7TYtT6wDQ4"
KHQR_SECRET_KEY = "fTh93txXT8eqqhgn3cKbOuekASFkbxWx"
KHQR_BASE_URL = "https://khqr.cc/api"
KHQR_RETURN_URL = "https://ecommerce-clothes-theta.vercel.app/payment-callback"

def create_khqr_payment(transaction_id: str, amount: float, customer_name: str = "", phone: str = ""):
    """Create KHQR payment URL"""
    try:
        # Generate hash for security
        raw_string = f"{KHQR_SECRET_KEY}{transaction_id}{amount}{KHQR_RETURN_URL}"
        hash_value = hashlib.sha1(raw_string.encode('utf-8')).hexdigest()
        
        # Build payment URL
        payment_url = f"{KHQR_BASE_URL}/payment/request/{KHQR_PROFILE_ID}?transaction_id={transaction_id}&amount={amount}&return_url={KHQR_RETURN_URL}&hash={hash_value}"
        
        if customer_name:
            payment_url += f"&customer_name={customer_name}"
        if phone:
            payment_url += f"&customer_phone={phone}"
        
        return payment_url
        
    except Exception as e:
        print(f"Error creating payment: {e}")
        return f"https://khqr.cc/payment/{KHQR_PROFILE_ID}?amount={amount}&transaction_id={transaction_id}"

def verify_khqr_transaction(transaction_id: str):
    """Verify payment status with KHQR"""
    try:
        # Generate verification hash
        raw_string = f"{KHQR_SECRET_KEY}{transaction_id}"
        hash_value = hashlib.sha1(raw_string.encode('utf-8')).hexdigest()
        
        # Call verification API
        verify_url = f"{KHQR_BASE_URL}/payment/verify/{KHQR_PROFILE_ID}"
        
        response = requests.post(
            verify_url,
            json={
                "transaction_id": transaction_id,
                "hash": hash_value
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Verification result: {result}")
            return result
        
        return {"status": "failed", "message": "Verification failed"}
        
    except Exception as e:
        print(f"Verification error: {e}")
        return {"status": "error", "message": str(e)}

# ========== USERS ==========
@app.post("/api/users/register")
def register(data: RegisterData):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists")
    
    cursor.execute("INSERT INTO users (full_name, email, phone_number, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                   (data.full_name, data.email, data.phone_number, data.password, 'user'))
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/api/users/login")
def login(data: LoginData):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (data.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or user["password_hash"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": f"token_{user['id']}",
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user["phone_number"],
            "role": user["role"]
        }
    }

@app.get("/api/users/")
def get_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, email, phone_number, role, created_at FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

# ========== CATEGORIES ==========
@app.get("/api/categories/")
def get_categories():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM categories ORDER BY id")
    cats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cats

@app.post("/api/categories/")
def create_category(cat: CategoryCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (cat.name,))
        conn.commit()
        cat_id = cursor.lastrowid
        conn.close()
        return {"id": cat_id, "name": cat.name}
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Category exists")

@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

# ========== PRODUCTS ==========
@app.post("/api/products/")
def create_product(product: ProductCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (title, original_price, discount_price, category_id, description, stock, colors, sizes, size_stock, main_image, sub_images)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (product.title, product.original_price, product.discount_price, product.category_id, product.description, product.stock, product.colors, product.sizes, product.size_stock, "", "[]"))
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return {"id": product_id, "message": "Product created"}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: ProductCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products 
        SET title=?, original_price=?, discount_price=?, category_id=?, description=?, stock=?, colors=?, sizes=?, size_stock=?
        WHERE id=?
    ''', (product.title, product.original_price, product.discount_price, product.category_id, product.description, product.stock, product.colors, product.sizes, product.size_stock, product_id))
    conn.commit()
    conn.close()
    return {"message": "Product updated"}

@app.post("/api/products/{product_id}/main-image")
async def upload_main_image(product_id: int, file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]
    filename = f"main_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = f"uploads/products/{filename}"
    
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    image_url = f"/uploads/products/{filename}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET main_image = ? WHERE id = ?", (image_url, product_id))
    conn.commit()
    conn.close()
    
    return {"url": image_url}

@app.post("/api/products/{product_id}/sub-images")
async def upload_sub_images(product_id: int, files: List[UploadFile] = File(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sub_images FROM products WHERE id = ?", (product_id,))
    result = cursor.fetchone()
    existing = json.loads(result[0]) if result and result[0] else []
    
    for file in files:
        ext = file.filename.split(".")[-1]
        filename = f"sub_{product_id}_{len(existing)}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = f"uploads/products/{filename}"
        
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        existing.append(f"/uploads/products/{filename}")
    
    cursor.execute("UPDATE products SET sub_images = ? WHERE id = ?", (json.dumps(existing), product_id))
    conn.commit()
    conn.close()
    
    return {"urls": existing}

@app.get("/api/products/")
def get_products():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, c.name as category_name 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        ORDER BY p.id DESC
    """)
    products = []
    for row in cursor.fetchall():
        p = dict(row)
        if p.get('sub_images'):
            try:
                p['sub_images'] = json.loads(p['sub_images'])
            except:
                p['sub_images'] = []
        else:
            p['sub_images'] = []
        products.append(p)
    
    conn.close()
    return products

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    product = dict(row)
    if product.get('sub_images'):
        try:
            product['sub_images'] = json.loads(product['sub_images'])
        except:
            product['sub_images'] = []
    else:
        product['sub_images'] = []
    conn.close()
    return product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

# ========== ORDERS ==========
@app.post("/api/orders/")
def create_order(order: OrderCreate):
    # Generate unique order number
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get or create user (for now use default user)
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    user = cursor.fetchone()
    user_id = user[0] if user else 1
    
    # Calculate total from items if not provided
    total = order.total_amount
    
    # Insert order with all shipping information
    cursor.execute('''
        INSERT INTO orders (order_number, user_id, total_amount, shipping_address, status, full_name, phone_number, city)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_number, user_id, total, order.shipping_address, 'pending', order.full_name, order.phone_number, order.city))
    
    order_id = cursor.lastrowid
    
    # Insert order items
    for item in order.items:
        # Get product price if not provided
        if not item.price:
            cursor.execute("SELECT original_price, discount_price FROM products WHERE id = ?", (item.product_id,))
            product = cursor.fetchone()
            if product:
                item.price = product[1] if product[1] else product[0]
        
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, product_title, quantity, price_at_time, selected_color, selected_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, item.product_id, item.product_title, item.quantity, item.price, item.selected_color, item.selected_size))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Order created: {order_number} - Total: ${total}")
    
    return {
        "id": order_id,
        "order_number": order_number,
        "total_amount": total,
        "message": "Order created successfully"
    }

@app.get("/api/orders/")
def get_orders():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = []
    for row in cursor.fetchall():
        order = dict(row)
        cursor.execute("""
            SELECT * FROM order_items WHERE order_id = ?
        """, (order['id'],))
        order['items'] = [dict(item) for item in cursor.fetchall()]
        orders.append(order)
    
    conn.close()
    return orders

@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = dict(cursor.fetchone())
    
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    order['items'] = [dict(item) for item in cursor.fetchall()]
    
    conn.close()
    return order

@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return {"message": f"Status updated to {status}"}

# ========== PAYMENT ==========
@app.post("/api/payment/initiate")
def initiate_payment(payment: PaymentRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (payment.order_id,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    print(f"💰 Initiating payment for order: {order['order_number']} - Amount: ${order['total_amount']}")
    
    # Create payment URL with customer info
    payment_url = create_khqr_payment(
        transaction_id=order["order_number"],
        amount=order["total_amount"],
        customer_name=order["full_name"] or "Customer",
        phone=order["phone_number"] or ""
    )
    
    return {
        "payment_url": payment_url,
        "order_id": order["id"],
        "order_number": order["order_number"],
        "amount": order["total_amount"]
    }

@app.post("/api/payment/verify")
def verify_payment(verify: PaymentVerify):
    print(f"🔍 Verifying payment for transaction: {verify.transaction_id}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if order already marked as paid
    cursor.execute("SELECT * FROM orders WHERE order_number = ?", (verify.transaction_id,))
    order = cursor.fetchone()
    
    if order and order["status"] == "paid":
        conn.close()
        return {
            "verified": True,
            "transaction_id": verify.transaction_id,
            "amount": order["total_amount"],
            "status": "paid",
            "message": "Payment already verified"
        }
    
    # Verify with KHQR
    result = verify_khqr_transaction(verify.transaction_id)
    
    # Check if payment was successful
    if result.get("status") == "success" or result.get("responseCode") == 0:
        # Update order status to paid
        cursor.execute("""
            UPDATE orders 
            SET status = 'paid', 
                payment_transaction_id = ? 
            WHERE order_number = ?
        """, (verify.transaction_id, verify.transaction_id))
        conn.commit()
        
        # Get updated order
        cursor.execute("SELECT * FROM orders WHERE order_number = ?", (verify.transaction_id,))
        updated_order = cursor.fetchone()
        conn.close()
        
        print(f"✅ Payment verified for order: {verify.transaction_id}")
        
        return {
            "verified": True,
            "transaction_id": verify.transaction_id,
            "amount": updated_order["total_amount"] if updated_order else 0,
            "status": "paid",
            "message": "Payment confirmed successfully"
        }
    
    conn.close()
    
    print(f"❌ Payment verification failed for: {verify.transaction_id}")
    
    return {
        "verified": False,
        "transaction_id": verify.transaction_id,
        "status": "pending",
        "message": "Payment not confirmed yet. Please check again later."
    }

# ========== HEALTH ==========
@app.get("/")
def root():
    return {"message": "MENGHOR STORE API Running", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)