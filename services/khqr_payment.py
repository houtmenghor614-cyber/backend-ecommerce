import hashlib
import httpx
import hmac
from urllib.parse import urlencode
from config import Config

class KHQRPayment:
    def __init__(self):
        self.profile_id = Config.KHQR_PROFILE_ID
        self.secret_key = Config.KHQR_SECRET_KEY
        self.gateway_url = Config.KHQR_GATEWAY_URL
        self.verify_url = Config.KHQR_VERIFY_URL
        self.success_url = Config.KHQR_SUCCESS_URL
    
    def generate_hash(self, transaction_id: str, amount: float, remark: str = "") -> str:
        """Generate SHA1 hash for payment request"""
        raw_string = f"{self.secret_key}{transaction_id}{amount}{self.success_url}{remark}"
        return hashlib.sha1(raw_string.encode()).hexdigest()
    
    def generate_verify_hash(self, transaction_id: str) -> str:
        """Generate SHA1 hash for verification"""
        raw_string = f"{self.profile_id}{transaction_id}"
        return hashlib.sha1(raw_string.encode()).hexdigest()
    
    def create_payment_session(self, transaction_id: str, amount: float, remark: str = ""):
        """Create KHQR payment session and return URL"""
        hash_value = self.generate_hash(transaction_id, amount, remark)
        
        payment_data = {
            "transaction_id": transaction_id,
            "amount": amount,
            "success_url": self.success_url,
            "remark": remark,
            "hash": hash_value
        }
        
        query_string = urlencode(payment_data)
        payment_url = f"{self.gateway_url}/{self.profile_id}?{query_string}"
        
        return payment_url
    
    async def verify_transaction(self, transaction_id: str):
        """Verify transaction status with KHQR"""
        hash_value = self.generate_verify_hash(transaction_id)
        
        post_data = {
            "transaction_id": transaction_id,
            "hash": hash_value
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.verify_url, data=post_data)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"responseCode": 1, "responseMessage": "Verification failed"}
        except Exception as e:
            return {"responseCode": 1, "responseMessage": str(e)}
    
    def is_payment_successful(self, result: dict) -> bool:
        """Check if payment was successful"""
        return (
            result.get("responseCode") == 0 and
            result.get("data", {}).get("status", "").lower() == "success"
        )

# Create singleton instance
khqr_payment = KHQRPayment()