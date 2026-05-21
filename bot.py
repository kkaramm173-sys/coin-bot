
import requests
import time

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

while True:
    try:
        # placeholder signal
        send_message("Bot çalışıyor...")
        time.sleep(60)
    except Exception as e:
        send_message(f"Hata: {e}")
        time.sleep(60)
