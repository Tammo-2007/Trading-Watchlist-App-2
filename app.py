import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import yaml
import json
import os
import logging
import time
from datetime import datetime

# ==============================
# CONFIG & LOGGING
# ==============================

logging.basicConfig(
    filename="trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

st.set_page_config(layout="wide")

# ==============================
# AUTO REFRESH 15 MIN
# ==============================

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 900:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# ==============================
# LOAD CONFIG
# ==============================

with open("config.yaml") as f:
    config = yaml.safe_load(f)

watchlist = config["watchlist"]

# ==============================
# CACHE
# ==============================

CACHE_FILE = "data_cache.json"

def load_data(ticker):

    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    if ticker in cache:
        daily = pd.read_json(cache[ticker]["daily"])
        weekly = pd.read_json(cache[ticker]["weekly"])
    else:
        daily = yf.download(ticker, period="2y", interval="1d")
        weekly = yf.download(ticker, period="1y", interval="1wk")

        cache[ticker] = {
            "daily": daily.to_json(),
            "weekly": weekly.to_json()
        }

        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)

    return daily, weekly

# ==============================
# INDICATORS
# ==============================

def calculate_indicators(df):

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    df["GoldenCross"] = (df["MA50"] > df["MA200"]) & \
                        (df["MA50"].shift(1) <= df["MA200"].shift(1))

    df["DeathCross"] = (df["MA50"] < df["MA200"]) & \
                       (df["MA50"].shift(1) >= df["MA200"].shift(1))

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()

    high9 = df["High"].rolling(9).max()
    low9 = df["Low"].rolling(9).min()
    df["Tenkan"] = (high9 + low9) / 2

    high26 = df["High"].rolling(26).max()
    low26 = df["Low"].rolling(26).min()
    df["Kijun"] = (high26 + low26) / 2

    df["Senkou_A"] = ((df["Tenkan"] + df["Kijun"]) / 2).shift(26)

    high52 = df["High"].rolling(52).max()
    low52 = df["Low"].rolling(52).min()
    df["Senkou_B"] = ((high52 + low52) / 2).shift(26)

    return df

# ==============================
# RISK CALCULATOR
# ==============================

def risk_calc(capital, entry, swing_low):
    stop = swing_low * 0.9
    risk_per_share = entry - stop
    size = capital * 0.01 / risk_per_share
    return int(size), round(stop, 2)

# ==============================
# DASHBOARD
# ==============================

st.title("📊 Trading Dashboard Pro")

dark = st.toggle("Dark Mode")

if dark:
    st.markdown(
        """
        <style>
        body { background-color: #0E1117; color: white; }
        </style>
        """,
        unsafe_allow_html=True
    )

watch_data = []
alerts = []

for ticker in watchlist:

    daily, weekly = load_data(ticker)
    daily = calculate_indicators(daily)

    current = daily.iloc[-1]

    if current["GoldenCross"]:
        alerts.append(f"{ticker} Golden Cross")

    if current["RSI"] < 30:
        alerts.append(f"{ticker} RSI Oversold")

    perf = ((current["Close"] / daily.iloc[-20]["Close"]) - 1) * 100

    try:
        info = yf.Ticker(ticker).info
        pe = info.get("trailingPE")
        debt = info.get("debtToEquity")
    except:
        pe = None
        debt = None

    watch_data.append({
        "Ticker": ticker,
        "Price": round(current["Close"],2),
        "RSI": round(current["RSI"],2),
        "MA Status": "Bullish" if current["MA50"] > current["MA200"] else "Bearish",
        "1M %": round(perf,2),
        "P/E": pe,
        "Debt/Equity": debt
    })

watch_df = pd.DataFrame(watch_data)

st.subheader("Watchlist")
st.dataframe(watch_df)

# ==============================
# CHARTS
# ==============================

ticker = st.selectbox("Ticker wählen", watchlist)
daily, weekly = load_data(ticker)
daily = calculate_indicators(daily)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Monat (Ichimoku)")
    st.line_chart(daily[["Close","Tenkan","Kijun"]].tail(30))

with col2:
    st.subheader("Woche (MA)")
    st.line_chart(weekly[["Close"]])

with col3:
    st.subheader("Tag (RSI/MACD)")
    st.line_chart(daily[["RSI","MACD"]].tail(60))

# ==============================
# RISK MODULE
# ==============================

st.subheader("Risiko-Rechner")

capital = st.number_input("Kapital", value=10000)
if st.button("Berechne Position"):

    entry = daily.iloc[-1]["Close"]
    swing_low = daily["Low"].rolling(20).min().iloc[-1]

    size, stop = risk_calc(capital, entry, swing_low)

    st.success(f"Positionsgröße: {size} Stück | Stop-Loss: {stop}")

# ==============================
# ALERT LOG
# ==============================

st.subheader("Live Alerts")
st.write(alerts[-10:])
