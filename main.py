import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime, timedelta

# === CONFIGURATION ===
Dhan_API_KEY = "1001926626"
Dhan_ACCESS_TOKEN = "9d6dd31d-da48-41a1-81bb-4db68e6fdb63"
TELEGRAM_BOT_TOKEN = "6560974649:AAFWFSRru0RCqVXzrgrPvTLcsOe-XbR1n_g"
TELEGRAM_CHAT_ID = "6002421352"
NIFTY_50_SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

headers = {
    "access-token": Dhan_ACCESS_TOKEN,
    "dhan-client-id": Dhan_API_KEY
}

def fetch_ohlc(symbol, interval, limit):
    url = f"https://api.dhan.co/market/quotes/historical"
    params = {
        "securityId": symbol,
        "exchangeSegment": "NSE_EQ",
        "instrumentType": "EQUITY",
        "interval": interval,
        "limit": limit
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        return pd.DataFrame(data["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    else:
        print(f"Error fetching OHLC for {symbol}: {response.status_code}")
        return pd.DataFrame()

def evaluate_symbol(symbol):
    try:
        df_d = fetch_ohlc(symbol, "1d", 100)
        if df_d.empty:
            return False
        df_d.ta.kc(length=21, scalar=1, append=True)
        df_d["EMA_88"] = ta.ema(df_d["close"], length=88)
        df_d["RSI"] = ta.rsi(df_d["close"], length=14)

        if df_d.iloc[-1]["close"] > df_d.iloc[-1]["KC_Upper_21_1.0"]:
            return False
        if df_d.iloc[-1]["close"] > df_d.iloc[-1]["EMA_88"]:
            return False
        if df_d.iloc[-1]["RSI"] > 40:
            return False

        df_h = fetch_ohlc(symbol, "1h", 100)
        if df_h.empty:
            return False
        df_h.ta.kc(length=21, scalar=1, append=True)
        df_h["RSI"] = ta.rsi(df_h["close"], length=14)

        above_mid = df_h[
            (df_h["close"] > df_h["KC_Lower_21_1.0"]) &
            (df_h["close"] < df_h["KC_Mid_21_1.0"])
        ]
        below_lower = df_h[df_h["close"] < df_h["KC_Lower_21_1.0"]]
        rsi_up = df_h[(df_h["RSI"] > 40) & (df_h["RSI"] < 50)]
        rsi_down = df_h[df_h["RSI"] < 40]

        if not above_mid.empty and not below_lower.empty and not rsi_up.empty and not rsi_down.empty:
            return True
    except Exception as e:
        print(f"Error evaluating {symbol}: {e}")
    return False

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, data=data)

def run_screener():
    matches = []
    for symbol in NIFTY_50_SYMBOLS:
        print(f"Checking {symbol}...")
        if evaluate_symbol(symbol):
            matches.append(symbol)
            send_telegram_message(f"{symbol} matched the screener conditions!")
        time.sleep(1)
    if not matches:
        send_telegram_message("📉 No stocks matched the screener today.")
    else:
        send_telegram_message("✅ Screener matched: " + ", ".join(matches))

def is_trading_hours():
    now_utc = datetime.utcnow()
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    start = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = ist_now.replace(hour=15, minute=30, second=0, microsecond=0)
    if ist_now.weekday() >= 5:
        return False
    return start <= ist_now <= end

if __name__ == "__main__":
    if is_trading_hours():
        run_screener()
    else:
        print("⏰ Outside trading hours. Skipping.")
