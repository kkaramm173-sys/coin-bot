import websocket
import json
import requests
import time
from collections import deque, defaultdict

# =========================================================
# TELEGRAM
# =========================================================
TOKEN = "8010481571:AAGjCJGEIbw461W4fvn3RIkob9dh-StDVYg"
CHAT_ID = "1048213900"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# =========================================================
# SETTINGS (STABLE VERSION)
# =========================================================
WINDOW_SECONDS = 10
VOLUME_THRESHOLD = 150000
PRICE_MOVE_THRESHOLD = 0.20
SIGNAL_COOLDOWN = 60
MAX_STREAMS = 20   # ⚠️ FIX: 80 çok fazla

# =========================================================
# COINS (SAFE VERSION)
# =========================================================
def get_symbols():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": False
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        symbols = []
        for coin in data:
            symbols.append(coin["symbol"].upper() + "USDT")

        symbols = list(set(symbols))[:MAX_STREAMS]
        return symbols

    except Exception as e:
        print("CoinGecko Error:", e)
        return []

symbols = get_symbols()
print("Coins:", symbols)

# =========================================================
# DATA STORAGE (LIMITED MEMORY)
# =========================================================
buy_volume = defaultdict(lambda: deque(maxlen=200))
sell_volume = defaultdict(lambda: deque(maxlen=200))
prices = defaultdict(lambda: deque(maxlen=200))
last_signal_time = {}

# =========================================================
# CLEANUP
# =========================================================
def cleanup(symbol):
    now = time.time()

    def clean(q):
        while q and now - q[0][0] > WINDOW_SECONDS:
            q.popleft()

    clean(buy_volume[symbol])
    clean(sell_volume[symbol])
    clean(prices[symbol])

# =========================================================
# ANALYSIS
# =========================================================
def analyze(symbol):
    cleanup(symbol)

    if len(prices[symbol]) < 2:
        return

    total_buy = sum(v for t, v in buy_volume[symbol])
    total_sell = sum(v for t, v in sell_volume[symbol])

    first = prices[symbol][0][1]
    last = prices[symbol][-1][1]

    move = ((last - first) / first) * 100

    now = time.time()
    last_time = last_signal_time.get(symbol, 0)

    if now - last_time < SIGNAL_COOLDOWN:
        return

    # LONG
    if total_buy > VOLUME_THRESHOLD and move > PRICE_MOVE_THRESHOLD and total_buy > total_sell * 1.5:
        msg = f"🟢 LONG {symbol.upper()}\nBuy:{total_buy:.0f}\nSell:{total_sell:.0f}\nMove:{move:.2f}%"
        print(msg)
        send_telegram(msg)
        last_signal_time[symbol] = now

    # SHORT
    elif total_sell > VOLUME_THRESHOLD and move < -PRICE_MOVE_THRESHOLD and total_sell > total_buy * 1.5:
        msg = f"🔴 SHORT {symbol.upper()}\nBuy:{total_buy:.0f}\nSell:{total_sell:.0f}\nMove:{move:.2f}%"
        print(msg)
        send_telegram(msg)
        last_signal_time[symbol] = now

# =========================================================
# WEBSOCKET
# =========================================================
def on_message(ws, message):
    try:
        data = json.loads(message)
        trade = data["data"]

        symbol = trade["s"].lower()
        price = float(trade["p"])
        qty = float(trade["q"])
        value = price * qty
        is_sell = trade["m"]

        now = time.time()

        prices[symbol].append((now, price))

        if is_sell:
            sell_volume[symbol].append((now, value))
        else:
            buy_volume[symbol].append((now, value))

        analyze(symbol)

    except Exception as e:
        print("Message Error:", e)

def on_error(ws, error):
    print("WS Error:", error)

def on_close(ws, code, msg):
    print("WS Closed, reconnecting in 5s...")
    time.sleep(5)
    start()

def on_open(ws):
    print("WebSocket Connected")

# =========================================================
# START
# =========================================================
def start():
    streams = "/".join([f"{s.lower()}@trade" for s in symbols])
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    ws.run_forever()

start()
