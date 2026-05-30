import requests
import json

# First, login to get token
login_response = requests.post(
    "http://localhost:8000/api/users/login",
    json={"email": "admin@dynastore.com", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit()

token = login_response.json()['access_token']
print(f"✅ Login successful")

# Test payment generation for an existing order
# First, get an order ID
orders_response = requests.get(
    "http://localhost:8000/api/orders/",
    headers={"Authorization": f"Bearer {token}"}
)

if orders_response.status_code == 200:
    orders = orders_response.json()
    if orders:
        order_id = orders[0]['id']
        print(f"Using order ID: {order_id}")
        
        # Test payment generation
        payment_response = requests.post(
            "http://localhost:8000/api/payment/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"order_id": order_id}
        )
        
        print(f"Payment Generation Status: {payment_response.status_code}")
        print(f"Payment Generation Response: {payment_response.text}")
    else:
        print("No orders found. Please create an order first.")
else:
    print(f"Failed to get orders: {orders_response.text}")