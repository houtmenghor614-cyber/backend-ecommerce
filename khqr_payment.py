import hashlib
import requests
from config import Config

class KHQRPayment:
    def __init__(self):
        self.profile_id = Config.KHQR_PROFILE_ID
        self.secret_key = Config.KHQR_SECRET_KEY
        self.gateway_url = Config.KHQR_GATEWAY_URL
        self.verify_url = Config.KHQR_VERIFY_URL
        self.success_url = Config.KHQR_SUCCESS_URL

    def create_payment_session(self, transaction_id: str, amount: float, remark: str = "") -> str:
        """
        Create a KHQR payment session and return the redirect URL
        """
        # Create hash: sha1(secret + id + amt + url + remark)
        raw_string = (
            self.secret_key +
            transaction_id +
            str(amount) +
            self.success_url +
            remark
        )
        
        hash_value = hashlib.sha1(raw_string.encode()).hexdigest()
        
        # Build payment URL
        payment_params = {
            "transaction_id": transaction_id,
            "amount": amount,
            "success_url": self.success_url,
            "hash": hash_value,
            "remark": remark
        }
        
        # Remove empty params
        payment_params = {k: v for k, v in payment_params.items() if v}
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in payment_params.items()])
        payment_url = f"{self.gateway_url}/{self.profile_id}?{query_string}"
        
        return payment_url

    def verify_transaction(self, transaction_id: str) -> dict:
        """
        Verify transaction status with KHQR API
        """
        # Create hash: sha1(profile_key + transaction_id)
        hash_value = hashlib.sha1(
            (self.secret_key + transaction_id).encode()
        ).hexdigest()
        
        post_data = {
            "transaction_id": transaction_id,
            "hash": hash_value
        }
        
        try:
            response = requests.post(
                self.verify_url,
                data=post_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"responseCode": 1, "responseMessage": "API Error", "data": None}
        
        except Exception as e:
            return {"responseCode": 1, "responseMessage": str(e), "data": None}

    def is_payment_successful(self, response: dict) -> bool:
        """
        Check if payment was successful
        """
        return (
            response.get('responseCode') == 0 and
            response.get('data', {}).get('status', '').lower() == 'success'
        )

khqr_payment = KHQRPayment()