import requests
from config import Config

class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text, parse_mode="HTML"):
        """Send a message to the admin"""
        if not self.token or not self.chat_id:
            print("Telegram bot not configured")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.ok
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    def send_order_notification(self, order_data):
        """Send detailed order notification to admin"""
        message = self.format_order_message(order_data)
        return self.send_message(message)

    def format_order_message(self, order_data):
        """Format order details into a nice message"""
        items_text = ""
        for item in order_data.get('items', []):
            items_text += f"""
┌ • <b>{item.get('product_title', 'N/A')}</b>
│   ├ Quantity: {item.get('quantity', 0)}
│   ├ Price: ${item.get('price_at_time', 0)}
│   ├ Size: {item.get('selected_size', 'N/A')}
│   └ Color: {item.get('selected_color', 'N/A')}
"""
        
        message = f"""
🎉 <b>NEW ORDER RECEIVED!</b> 🎉

━━━━━━━━━━━━━━━━━━━━━
<b>🆔 ORDER INFORMATION</b>
━━━━━━━━━━━━━━━━━━━━━
<b>Order ID:</b> <code>{order_data.get('order_number', 'N/A')}</code>
<b>Order Date:</b> {order_data.get('created_at', 'N/A')}
<b>Order Status:</b> ✅ PAID

━━━━━━━━━━━━━━━━━━━━━
<b>👤 CUSTOMER DETAILS</b>
━━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> {order_data.get('customer_name', 'N/A')}
<b>Email:</b> {order_data.get('customer_email', 'N/A')}
<b>Phone:</b> {order_data.get('customer_phone', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━
<b>📍 SHIPPING ADDRESS</b>
━━━━━━━━━━━━━━━━━━━━━
{order_data.get('shipping_address', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━
<b>📦 ORDER ITEMS</b>
━━━━━━━━━━━━━━━━━━━━━
{items_text}
━━━━━━━━━━━━━━━━━━━━━
<b>💰 TOTAL AMOUNT:</b> ${order_data.get('total_amount', 0)}

<b>💳 Payment Method:</b> KHQR
<b>🔑 Transaction ID:</b> <code>{order_data.get('payment_transaction_id', 'N/A')}</code>

━━━━━━━━━━━━━━━━━━━━━
✅ <b>Payment has been confirmed!</b>
📦 Please prepare the order for shipping.
━━━━━━━━━━━━━━━━━━━━━
"""
        return message

    def send_payment_confirmation(self, user_name, amount, order_number):
        """Send simple payment confirmation"""
        message = f"""
✅ <b>PAYMENT CONFIRMED!</b>

👤 Customer: {user_name}
💰 Amount: ${amount}
🆔 Order: <code>{order_number}</code>

💳 Payment has been successfully processed.
"""
        return self.send_message(message)

# Create singleton instance
telegram_bot = TelegramBot()