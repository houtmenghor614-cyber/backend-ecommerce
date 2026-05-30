import hashlib
import requests
import json
from config import Config

class KHQRJsonPayment:
    def __init__(self):
        self.profile_id = Config.KHQR_PROFILE_ID
        self.secret_key = Config.KHQR_SECRET_KEY
        self.api_url = Config.KHQR_API_URL
        self.verify_url = Config.KHQR_VERIFY_URL
        self.success_url = Config.KHQR_SUCCESS_URL

    def generate_qr(self, transaction_id: str, amount: float, remark: str = "") -> dict:
        """
        Generate QR code using KHQR JSON API
        """
        amount_str = f"{amount:.2f}"
        
        # Create hash: sha1(secret + id + amt + url + remark)
        raw_string = f"{self.secret_key}{transaction_id}{amount_str}{self.success_url}{remark}"
        hash_value = hashlib.sha1(raw_string.encode()).hexdigest()
        
        # Prepare request data
        request_data = {
            "transaction_id": transaction_id,
            "amount": amount_str,
            "success_url": self.success_url,
            "remark": remark,
            "hash": hash_value
        }
        
        print("=" * 60)
        print("🔐 KHQR JSON API REQUEST")
        print("=" * 60)
        print(f"URL: {self.api_url}")
        print(f"Data: {json.dumps(request_data, indent=2)}")
        print(f"Raw String: {raw_string}")
        print(f"Hash: {hash_value}")
        print("=" * 60)
        
        try:
            response = requests.post(
                self.api_url,
                data=request_data,
                timeout=30,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('responseCode') == 0:
                    return result.get('data', {})
                else:
                    print(f"API Error: {result.get('responseMessage')}")
                    return None
            else:
                print(f"HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Exception: {e}")
            return None

    def verify_transaction(self, transaction_id: str) -> dict:
        """
        Verify transaction status
        """
        # Create verification hash: sha1(profile_id + transaction_id)
        raw_string = f"{self.profile_id}{transaction_id}"
        hash_value = hashlib.sha1(raw_string.encode()).hexdigest()
        
        post_data = {
            "transaction_id": transaction_id,
            "hash": hash_value
        }
        
        print("=" * 60)
        print("🔐 KHQR VERIFY REQUEST")
        print("=" * 60)
        print(f"URL: {self.verify_url}")
        print(f"Data: {post_data}")
        print(f"Raw String: {raw_string}")
        print(f"Hash: {hash_value}")
        print("=" * 60)
        
        try:
            response = requests.post(
                self.verify_url,
                data=post_data,
                timeout=30,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"responseCode": 1, "responseMessage": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"responseCode": 1, "responseMessage": str(e)}

    def is_payment_successful(self, response: dict) -> bool:
        """
        Check if payment was successful
        """
        return (
            response.get('responseCode') == 0 and
            response.get('data', {}).get('status', '').lower() == 'success'
        )

khqr_json = KHQRJsonPayment()