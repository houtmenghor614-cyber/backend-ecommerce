import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY   = os.getenv("SECRET_KEY", "your_secret_key_change_this_in_production")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backup/file.db")

    # ✅ Fixed: os.getenv("VARIABLE_NAME", "default_value")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8858171591:AAG8dXI4vglgzoIJM6pruFxaMN6FUTa4E_I")
    TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "5724123597")

    UPLOAD_DIR = "uploads/products"

    # KHQR Payment
    KHQR_PROFILE_ID   = os.getenv("KHQR_PROFILE_ID",   "Y0xL0p6WlNruUhlnj51p4c7TYtT6wDQ4")
    KHQR_SECRET_KEY   = os.getenv("KHQR_SECRET_KEY",   "fTh93txXT8eqqhgn3cKbOuekASFkbxWx")
    KHQR_GATEWAY_URL  = os.getenv("KHQR_GATEWAY_URL",  "https://khqr.cc/api/payment/request")
    KHQR_VERIFY_URL   = os.getenv("KHQR_VERIFY_URL",   "https://khqr.cc/api/4CT8AuGLx8OkUhCqNdKJhekxw2LULqYa/payment-gateway/v1/payments/check-trans")
    KHQR_SUCCESS_URL  = os.getenv("KHQR_SUCCESS_URL",  "https://backend-ecommerce-6hef.onrender.com")

    # Google OAuth
    GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

    @classmethod
    def ensure_upload_dir(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs("backup", exist_ok=True)

Config.ensure_upload_dir()