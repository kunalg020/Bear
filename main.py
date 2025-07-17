import requests
import pandas_ta as ta
import pandas as pd
from datetime import datetime
import pytz
import time

# === CONFIGURATION ===
DHAN_CLIENT_ID = "1001926626"
DHAN_ACCESS_TOKEN = "9d6dd31d-da48-41a1-81bb-4db68e6fdb63"
TELEGRAM_BOT_TOKEN = "6560974649:AAFWFSRru0RCqVXzrgrPvTLcsOe-XbR1n_g"
TELEGRAM_CHAT_ID = "6002421352"

NIFTY_50_SYMBOLS = ["RELIANCE", "TCS", "INFY", "ICICIBANK", "HDFCBANK"]

headers = {
    "access-token": DHAN_ACCESS_TOKEN,
    "dhan-client-id": DHAN_CLIENT_ID
}

def is_trading_hours():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    return now.weekday() < 5 and now.hour >= 9 and now.hour < 15

def fetch_quote(symbol):
    url = f"https://api.dhan.co/market/quote?symbol={symbol}&exchangeSegment=NSE_EQ"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("lastTradedPrice", None)
    else:
        print(f"Error fetching quote for {symbol}: {response.status_code}")
        return None

def evaluate_symbol(symbol):
    try:
        ltp = fetch_quote(symbol)
        if ltp is None:
            return False
        
        # Add your LTP-based conditions here. Example:
        if ltp > 500:  # Change condition as needed
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
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

def run_screener():
    matches = []
    for symbol in NIFTY_50_SYMBOLS:
        print(f"Checking {symbol}...")
        if evaluate_symbol(symbol):
            matches.append(symbol)
            send_telegram_message(f"✅ {symbol} matched the real-time screener.")
        time.sleep(1)
    
    if not matches:
        send_telegram_message("📉 No Nifty 50 stocks matched the screener.")
    else:
        send_telegram_message("🎯 Screener hits: " + ", ".join(matches))

if __name__ == "__main__":
    if is_trading_hours():
        run_screener()
    else:
        print("⏰ Outside trading hours. Skipping.")
