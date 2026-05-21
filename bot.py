
import requests
import time

TOKEN = "8010481571:AAGjCJGEIbw461W4fvn3RIkob9dh-StDVYg"
CHAT_ID = "1048213900"

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
