import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import pytz

# === CONFIGURATION ===
DHAN_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5rSWQiOiIiLCJleHAiOjE3NTQ5NzAwMjgsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMjc5OTY4In0.xCXf8u7XL6iWuXs6XbJfXHhUTY7CYtfDFATmZC51jn717cy4uq3VQuzjJyfEqxtDMa-tWswXrnZS0j7FBEFdMA"
DHAN_CLIENT_ID = "1100279968"
TELEGRAM_BOT_TOKEN = "7876303846:AAHsuPJ9PKUSD1rGFM8o2puPQTS9yJ32H0Y"
TELEGRAM_CHAT_ID = "-1051646958"

# Full Nifty 50 list (symbol only; security ID is not needed for intraday API)
NIFTY_50_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "ITC", "SBIN", "KOTAKBANK",
    "HINDUNILVR", "BHARTIARTL", "ASIANPAINT", "HCLTECH", "MARUTI", "BAJFINANCE",
    "ADANIENT", "ADANIPORTS", "TITAN", "NTPC", "POWERGRID", "SUNPHARMA", "AXISBANK",
    "TECHM", "ONGC", "COALINDIA", "JSWSTEEL", "WIPRO", "ULTRACEMCO", "CIPLA",
    "TATAMOTORS", "NESTLEIND", "GRASIM", "BAJAJ-AUTO", "EICHERMOT", "BPCL",
    "DIVISLAB", "HINDALCO", "HEROMOTOCO", "HDFCLIFE", "BRITANNIA", "SBILIFE",
    "INDUSINDBK", "TATASTEEL", "M&M", "BAJAJFINSV", "DRREDDY", "UPL", "SHREECEM",
    "APOLLOHOSP", "ICICIPRULI"
]

def is_trading_hours():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

def fetch_ohlcv_dhan(symbol, interval="1d", limit=100):
    try:
        url = f"https://api.dhan.co/market/v1/chart/intraday/{symbol}/NSE/{interval}?limit={limit}"
        headers = {
            "accept": "application/json",
            "access-token": DHAN_API_KEY,
            "client-id": DHAN_CLIENT_ID
        }
        response = requests.get(url, headers=headers)
        candles = response.json().get("data", [])
        df = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}:", e)
        return pd.DataFrame()

def meets_bearish_criteria(symbol):
    try:
        df_daily = fetch_ohlcv_dhan(symbol, "1d")
        df_1h = fetch_ohlcv_dhan(symbol, "1h")

        if df_daily.empty or df_1h.empty:
            return False

        df_daily.ta.ema(length=88, append=True)
        df_daily.ta.rsi(length=14, append=True)
        df_daily.ta.kc(length=21, scalar=1.0, append=True)

        last = df_daily.iloc[-1]
        if (
            last["close"] > last["KC_Lower_21_1.0"] or
            last["close"] > last["EMA_88"] or
            last["RSI_14"] > 40
        ):
            return False

        df_1h.ta.kc(length=21, scalar=1.0, append=True)
        df_1h.ta.rsi(length=14, append=True)

        prices = df_1h["close"]
        lower = df_1h["KC_Lower_21_1.0"]
        rsi = df_1h["RSI_14"]

        for i in range(len(df_1h) - 3):
            p1, p2, p3 = prices[i], prices[i+1], prices[i+2]
            l1, l2, l3 = lower[i], lower[i+1], lower[i+2]
            r1, r2, r3 = rsi[i], rsi[i+1], rsi[i+2]

            if (
                p1 < l1 and
                p2 > l2 and
                p3 < l3 and
                r1 < 40 and
                40 <= r2 < 50 and
                r3 < 40
            ):
                return True

    except Exception as e:
        print(f"Error evaluating {symbol}: {e}")
    return False

def run_bearish_screener():
    print("🔍 Running Bearish Screener...")
    matched = []
    for symbol in NIFTY_50_SYMBOLS:
        if meets_bearish_criteria(symbol):
            matched.append(symbol)
    if matched:
        msg = "🔻 *Bearish Screener Match:*\n" + "\n".join(matched)
        send_telegram_alert(msg)
    else:
        print("No matches found today.")

if __name__ == "__main__":
    if is_trading_hours():
        run_bearish_screener()
    else:
        print("⏰ Outside trading hours. Skipping.")
