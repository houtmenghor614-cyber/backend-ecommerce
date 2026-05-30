import requests
import asyncio
from config import Config

async def send_telegram_alert(message: str):
    """Send alert to Telegram bot"""
    bot_token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials not configured")
        print(f"Bot Token exists: {bool(bot_token)}")
        print(f"Chat ID exists: {bool(chat_id)}")
        return None
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    print(f"📤 Sending Telegram message...")
    
    try:
        # Use requests in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, json=payload, timeout=10)
        )
        
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully!")
            return response.json()
        else:
            print(f"❌ Telegram API error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")
        return None

def send_sync_alert(message: str):
    """Synchronous version for testing"""
    import requests
    bot_token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials not configured")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        if response.status_code == 200:
            print("✅ Sync message sent!")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False