import requests

BOT_TOKEN = "8858171591:AAG8dXI4vglgzoIJM6pruFxaMN6FUTa4E_I"
CHAT_ID = "5724123597"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅✅✅ MENGHOR STORE BOT IS WORKING! ✅✅✅\n\nYour payment alerts will appear here.",
    "parse_mode": "HTML"
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    print("\n🎉 SUCCESS! Check your Telegram now!")
else:
    print("\n❌ Failed. Check your token and chat ID.")