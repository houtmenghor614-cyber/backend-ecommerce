from fastapi import FastAPI, HTTPException, Form, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import shutil
import uuid
import json
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MENGHOR CLOTHES")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload folder
os.makedirs("uploads/products", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ========== DATABASE ==========
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            email TEXT UNIQUE,
            phone_number TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_number TEXT UNIQUE,
            user_id INTEGER,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            payment_transaction_id TEXT,
            shipping_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id),
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER,
            price_at_time REAL,
            selected_color TEXT,
            selected_size TEXT
        )
    ''')

    cursor.execute("SELECT * FROM users WHERE email = 'admin@dynastore.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (full_name, email, phone_number, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
            ('Administrator', 'admin@dynastore.com', '0123456789', 'admin123', 'admin')
        )
        print("✅ Admin created")

    default_cats = ['Men', 'Women', 'Kids', 'Clothes', 'Accessories', 'Shoes']
    for cat in default_cats:
        cursor.execute("SELECT * FROM categories WHERE name = %s", (cat,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO categories (name) VALUES (%s)", (cat,))
            print(f"✅ Category: {cat}")

    conn.commit()
    conn.close()
    print("✅ Database ready!")

init_db()

# ========== ENV CONFIG ==========
KHQR_PROFILE_ID = os.environ.get("KHQR_PROFILE_ID")
KHQR_SECRET_KEY = os.environ.get("KHQR_SECRET_KEY")
KHQR_GATEWAY_URL = os.environ.get("KHQR_GATEWAY_URL")
KHQR_VERIFY_URL = os.environ.get("KHQR_VERIFY_URL")
KHQR_SUCCESS_URL = os.environ.get("KHQR_SUCCESS_URL")

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
    quantity: int
    selected_color: Optional[str] = None
    selected_size: Optional[str] = None

# ✅ FIXED: accepts user_id from frontend
class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    shipping_address: str
    user_id: Optional[int] = None

class PaymentRequest(BaseModel):
    order_id: int

class PaymentVerify(BaseModel):
    transaction_id: str

# ========== KHQR ==========
def create_khqr_payment(transaction_id: str, amount: float, remark: str = ""):
    raw_string = f"{KHQR_SECRET_KEY}{transaction_id}{amount}{KHQR_SUCCESS_URL}{remark}"
    hash_value = hashlib.sha1(raw_string.encode('utf-8')).hexdigest()
    payment_url = f"{KHQR_GATEWAY_URL}/{KHQR_PROFILE_ID}?transaction_id={transaction_id}&amount={amount}&success_url={KHQR_SUCCESS_URL}&hash={hash_value}"
    if remark:
        payment_url += f"&remark={remark}"
    return payment_url

def verify_khqr_transaction(transaction_id: str):
    hash_value = hashlib.sha1(f"{KHQR_SECRET_KEY}{transaction_id}".encode('utf-8')).hexdigest()
    try:
        response = requests.post(
            KHQR_VERIFY_URL,
            data={"transaction_id": transaction_id, "hash": hash_value},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"responseCode": 1, "responseMessage": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"responseCode": 1, "responseMessage": str(e)}

# ========== USERS ==========
@app.post("/api/users/register")
def register(data: RegisterData):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists")

    cursor.execute(
        "INSERT INTO users (full_name, email, phone_number, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
        (data.full_name, data.email, data.phone_number, data.password, 'user')
    )
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/api/users/login")
def login(data: LoginData):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
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
            "role": user["role"]
        }
    }

@app.get("/api/users/")
def get_users():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, email, phone_number, role, created_at FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

# ========== CATEGORIES ==========
@app.get("/api/categories/")
def get_categories():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM categories")
    cats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cats

@app.post("/api/categories/")
def create_category(cat: CategoryCreate):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (%s) RETURNING id", (cat.name,))
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        return {"id": result["id"], "name": cat.name}
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Category already exists")

@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

# ========== PRODUCTS ==========
@app.post("/api/products/")
def create_product(product: ProductCreate):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (title, original_price, discount_price, category_id, description, stock, colors, sizes, size_stock, main_image, sub_images)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (product.title, product.original_price, product.discount_price, product.category_id,
          product.description, product.stock, product.colors, product.sizes, product.size_stock, "", "[]"))
    result = cursor.fetchone()
    conn.commit()
    conn.close()
    return {"id": result["id"], "message": "Product created"}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: ProductCreate):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products
        SET title=%s, original_price=%s, discount_price=%s, category_id=%s,
            description=%s, stock=%s, colors=%s, sizes=%s, size_stock=%s
        WHERE id=%s
    ''', (product.title, product.original_price, product.discount_price, product.category_id,
          product.description, product.stock, product.colors, product.sizes, product.size_stock, product_id))
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

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET main_image = %s WHERE id = %s", (image_url, product_id))
    conn.commit()
    conn.close()
    return {"url": image_url}

@app.post("/api/products/{product_id}/sub-images")
async def upload_sub_images(product_id: int, files: List[UploadFile] = File(...)):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT sub_images FROM products WHERE id = %s", (product_id,))
    result = cursor.fetchone()
    existing = json.loads(result["sub_images"]) if result and result["sub_images"] else []

    for file in files:
        ext = file.filename.split(".")[-1]
        filename = f"sub_{product_id}_{len(existing)}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = f"uploads/products/{filename}"

        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)

        existing.append(f"/uploads/products/{filename}")

    cursor.execute("UPDATE products SET sub_images = %s WHERE id = %s", (json.dumps(existing), product_id))
    conn.commit()
    conn.close()
    return {"urls": existing}

@app.get("/api/products/")
def get_products():
    conn = get_conn()
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
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
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
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

# ========== ORDERS ==========
@app.post("/api/orders/")
def create_order(order: OrderCreate):
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    conn = get_conn()
    cursor = conn.cursor()

    # ✅ FIXED: use real logged-in user's ID, not always admin
    user_id = order.user_id if order.user_id else 1

    total = 0.0

    for item in order.items:
        cursor.execute("SELECT original_price, discount_price, stock, size_stock FROM products WHERE id = %s", (item.product_id,))
        product = cursor.fetchone()
        if not product:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        price = product["discount_price"] if product["discount_price"] else product["original_price"]
        total += price * item.quantity

        if not item.selected_size:
            if product["stock"] < item.quantity:
                conn.close()
                raise HTTPException(status_code=400, detail="Insufficient stock for product")

        if item.selected_size and product["size_stock"]:
            try:
                size_stock = json.loads(product["size_stock"])
                available = size_stock.get(item.selected_size, 0)
                if available < item.quantity:
                    conn.close()
                    raise HTTPException(status_code=400, detail=f"Only {available} items available for size {item.selected_size}")
            except:
                pass

    cursor.execute('''
        INSERT INTO orders (order_number, user_id, total_amount, shipping_address, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', (order_number, user_id, total, order.shipping_address, 'pending'))

    order_id = cursor.fetchone()["id"]

    for item in order.items:
        cursor.execute("SELECT original_price, discount_price, stock, size_stock FROM products WHERE id = %s", (item.product_id,))
        product = cursor.fetchone()
        price = product["discount_price"] if product["discount_price"] else product["original_price"]

        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price_at_time, selected_color, selected_size)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (order_id, item.product_id, item.quantity, price, item.selected_color, item.selected_size))

        if item.selected_size:
            size_stock = json.loads(product["size_stock"]) if product["size_stock"] else {}
            if item.selected_size in size_stock:
                size_stock[item.selected_size] -= item.quantity
                cursor.execute("UPDATE products SET size_stock = %s WHERE id = %s", (json.dumps(size_stock), item.product_id))
        else:
            new_stock = product["stock"] - item.quantity
            cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock, item.product_id))

    conn.commit()
    conn.close()

    return {
        "id": order_id,
        "order_number": order_number,
        "total_amount": total,
        "message": "Order created"
    }

# ✅ NEW: get orders for specific user only (for frontend_user)
@app.get("/api/orders/user/{user_id}")
def get_user_orders(user_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY id DESC", (user_id,))
    orders = []
    for row in cursor.fetchall():
        order = dict(row)
        cursor.execute("""
            SELECT oi.*, p.title as product_title, p.main_image as product_main_image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order['id'],))
        order['items'] = [dict(item) for item in cursor.fetchall()]
        orders.append(order)
    conn.close()
    return orders

# get ALL orders (for frontend_admin only)
@app.get("/api/orders/")
def get_orders():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = []
    for row in cursor.fetchall():
        order = dict(row)
        cursor.execute("""
            SELECT oi.*, p.title as product_title, p.main_image as product_main_image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order['id'],))
        order['items'] = [dict(item) for item in cursor.fetchall()]
        orders.append(order)
    conn.close()
    return orders

@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    order = dict(row)
    cursor.execute("""
        SELECT oi.*, p.title as product_title, p.main_image as product_main_image
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (order_id,))
    order['items'] = [dict(item) for item in cursor.fetchall()]
    conn.close()
    return order

@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: int, status: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    conn.commit()
    conn.close()
    return {"message": f"Status updated to {status}"}

# ========== PAYMENT ==========
@app.post("/api/payment/initiate")
def initiate_payment(payment: PaymentRequest):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = %s", (payment.order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment_url = create_khqr_payment(
        transaction_id=order["order_number"],
        amount=order["total_amount"],
        remark=f"Order_{order['order_number']}"
    )

    return {
        "payment_url": payment_url,
        "order_id": order["id"],
        "amount": order["total_amount"]
    }

@app.post("/api/payment/verify")
def verify_payment(verify: PaymentVerify):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_number = %s", (verify.transaction_id,))
    order = cursor.fetchone()

    if order and order["status"] == "paid":
        conn.close()
        return {
            "verified": True,
            "transaction_id": verify.transaction_id,
            "amount": order["total_amount"],
            "status": "paid"
        }

    result = verify_khqr_transaction(verify.transaction_id)

    if result.get("responseCode") == 0:
        data = result.get("data", {})
        if data.get("status", "").lower() == "success":
            cursor.execute("""
                UPDATE orders
                SET status = 'paid', payment_transaction_id = %s
                WHERE order_number = %s
            """, (data.get("transaction_id"), verify.transaction_id))
            conn.commit()
            conn.close()
            return {
                "verified": True,
                "transaction_id": verify.transaction_id,
                "amount": data.get("amount"),
                "status": "paid"
            }

    conn.close()
    return {"verified": False, "message": "Payment verification failed"}

# ========== HEALTH ==========
@app.get("/")
def root():
    return {"message": "API Running", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))