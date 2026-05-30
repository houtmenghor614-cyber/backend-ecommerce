import hashlib
import requests

PROFILE_ID = "4CT8AuGLx8OkUhCqNdKJhekxw2LULqYa"
SECRET_KEY = "7UJsB5fih2TSc8PhSlnusVRThEXQjHO7"
API_URL = f"https://khqr.cc/api/{PROFILE_ID}/payment-gateway/v1/payments/qr-api"
SUCCESS_URL = "http://localhost:3000/payment/success"

transaction_id = f"TEST_{int(__import__('time').time())}"
amount = "0.01"
remark = "Test Payment"

# Create hash
raw_string = f"{SECRET_KEY}{transaction_id}{amount}{SUCCESS_URL}{remark}"
hash_value = hashlib.sha1(raw_string.encode()).hexdigest()

print("=" * 60)
print("Testing KHQR with NEW SECRET KEY")
print(f"Profile ID: {PROFILE_ID}")
print(f"Secret Key: {SECRET_KEY[:10]}...")
print(f"Hash: {hash_value}")
print("=" * 60)

data = {
    "transaction_id": transaction_id,
    "amount": amount,
    "success_url": SUCCESS_URL,
    "remark": remark,
    "hash": hash_value
}

response = requests.post(API_URL, data=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    result = response.json()
    if result.get('responseCode') == 0:
        print("\n✅ SUCCESS! New credentials work!")
        print(f"QR URL: {result['data'].get('qr_url')}")
    else:
        print(f"\n❌ Error: {result.get('responseMessage')}")
else:
    print(f"\n❌ HTTP Error: {response.status_code}")