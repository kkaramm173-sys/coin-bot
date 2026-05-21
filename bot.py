# =========================================================
# LIVE MULTI COIN ORDER FLOW SCANNER
# TIMEFRAME YOK
# CANLI TRADE AKISI ANALIZI
# TELEGRAM BILDIRIM
# =========================================================


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

    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

# =========================================================
# AYARLAR
# =========================================================

WINDOW_SECONDS = 10

VOLUME_THRESHOLD = 150000

PRICE_MOVE_THRESHOLD = 0.20

SIGNAL_COOLDOWN = 60

MAX_STREAMS = 80

# =========================================================
# COINGECKO TOP COINLER
# =========================================================

def get_symbols():

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(url, params=params, headers=headers)

        data = r.json()

        symbols = []

        for coin in data:

            symbol = coin["symbol"].upper() + "USDT"

            symbols.append(symbol.lower())

        # tekrar edenleri sil
        symbols = list(set(symbols))

        # websocket fazla yüklenmesin
        symbols = symbols[:MAX_STREAMS]

        return symbols

    except Exception as e:

        print("CoinGecko Error:", e)

        return []

# =========================================================
# COINLER
# =========================================================

symbols = get_symbols()

if len(symbols) == 0:
    raise Exception("Coin listesi alinamadi")

print(f"{len(symbols)} coin yuklendi")

# =========================================================
# VERI
# =========================================================

buy_volume = defaultdict(deque)
sell_volume = defaultdict(deque)
prices = defaultdict(deque)

last_signal_time = {}

# =========================================================
# CLEANUP
# =========================================================

def cleanup(symbol):

    current = time.time()

    while (
        buy_volume[symbol]
        and current - buy_volume[symbol][0][0] > WINDOW_SECONDS
    ):
        buy_volume[symbol].popleft()

    while (
        sell_volume[symbol]
        and current - sell_volume[symbol][0][0] > WINDOW_SECONDS
    ):
        sell_volume[symbol].popleft()

    while (
        prices[symbol]
        and current - prices[symbol][0][0] > WINDOW_SECONDS
    ):
        prices[symbol].popleft()

# =========================================================
# ANALIZ
# =========================================================

def analyze(symbol):

    cleanup(symbol)

    total_buy = sum(v for t, v in buy_volume[symbol])

    total_sell = sum(v for t, v in sell_volume[symbol])

    if len(prices[symbol]) < 2:
        return

    first_price = prices[symbol][0][1]

    last_price = prices[symbol][-1][1]

    move_percent = (
        (last_price - first_price)
        / first_price
    ) * 100

    now = time.time()

    if symbol not in last_signal_time:
        last_signal_time[symbol] = 0

    # spam koruma
    if now - last_signal_time[symbol] < SIGNAL_COOLDOWN:
        return

    # =====================================================
    # LONG SIGNAL
    # =====================================================

    if (
        total_buy > VOLUME_THRESHOLD
        and move_percent > PRICE_MOVE_THRESHOLD
        and total_buy > total_sell * 1.5
    ):

        msg = f"""
🟢 LIVE LONG SIGNAL

Coin: {symbol.upper()}

Buy Volume: {round(total_buy)}

Sell Volume: {round(total_sell)}

Move: %{round(move_percent,2)}

Window: {WINDOW_SECONDS} sec
"""

        print(msg)

        send_telegram(msg)

        last_signal_time[symbol] = now

    # =====================================================
    # SHORT SIGNAL
    # =====================================================

    elif (
        total_sell > VOLUME_THRESHOLD
        and move_percent < -PRICE_MOVE_THRESHOLD
        and total_sell > total_buy * 1.5
    ):

        msg = f"""
🔴 LIVE SHORT SIGNAL

Coin: {symbol.upper()}

Buy Volume: {round(total_buy)}

Sell Volume: {round(total_sell)}

Move: %{round(move_percent,2)}

Window: {WINDOW_SECONDS} sec
"""

        print(msg)

        send_telegram(msg)

        last_signal_time[symbol] = now

# =========================================================
# WEBSOCKET MESAJ
# =========================================================

def on_message(ws, message):

    try:

        data = json.loads(message)

        trade = data["data"]

        symbol = trade["s"].lower()

        price = float(trade["p"])

        qty = float(trade["q"])

        value = price * qty

        is_market_sell = trade["m"]

        current = time.time()

        prices[symbol].append((current, price))

        if is_market_sell:
            sell_volume[symbol].append((current, value))
        else:
            buy_volume[symbol].append((current, value))

        analyze(symbol)

    except Exception as e:

        print("Message Error:", e)

# =========================================================
# HATA
# =========================================================

def on_error(ws, error):
    print("WebSocket Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket Closed")

def on_open(ws):
    print("WebSocket Connected")

# =========================================================
# STREAMLER
# =========================================================

streams = "/".join([f"{s}@trade" for s in symbols])

socket_url = f"wss://fstream.binance.com/stream?streams={streams}"

print("Connecting...")
print(socket_url[:200])

# =========================================================
# START
# =========================================================

ws = websocket.WebSocketApp(
    socket_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open
)

ws.run_forever()
