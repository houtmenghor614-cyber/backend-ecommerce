import hashlib
import requests

PROFILE_ID = "CpINIRWZPgCWGgqPIl6YrwTLAWJ7ysaf"
SECRET_KEY = "4hbioLdcsfPWvqdsAviFpOI4XIFbdZwI"

transaction_id = f"ORD_{int(__import__('time').time())}"
amount = "0.01"
success_url = "http://localhost:3000/payment/success"
remark = "Test Order"

print("=" * 60)
print("Testing KHQR with YOUR NEW CREDENTIALS")
print(f"Profile ID: {PROFILE_ID}")
print(f"Secret Key: {SECRET_KEY[:10]}...")
print(f"Transaction ID: {transaction_id}")
print("=" * 60)

# Create hash
raw_string = f"{SECRET_KEY}{transaction_id}{amount}{success_url}{remark}"
hash_value = hashlib.sha1(raw_string.encode()).hexdigest()

print(f"\nHash: {hash_value}")

# Build payment URL
payment_url = f"https://khqr.cc/api/payment/request/{PROFILE_ID}?transaction_id={transaction_id}&amount={amount}&success_url={success_url}&hash={hash_value}&remark={remark}"

print(f"\nPayment URL: {payment_url}")

try:
    # Don't follow redirects to see the actual response
    response = requests.get(payment_url, allow_redirects=False, timeout=10)
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ SUCCESS! Redirecting to KHQR payment page")
        location = response.headers.get('Location', 'Unknown')
        print(f"Redirect URL: {location}")
        print("\n🎉 Your KHQR payment is working!")
        print("Open this URL in your browser to see the QR code:")
        print(location)
    elif response.status_code == 200:
        print("✅ SUCCESS! KHQR page loaded")
        print("The QR code should be visible on the page")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)