import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging

# ==============================
# SETTINGS
# ==============================
WATCHLIST = ["PLTR", "NVDA", "TSLA", "SMCI", "CSG.AS"]
AUTO_REFRESH_SECONDS = 900  # 15 Minuten
RISK_PERCENT_DEFAULT = 1.0

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    filename="trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

st.set_page_config(layout="wide", page_title="Trading Dashboard Pro")

# ==============================
# AUTO REFRESH
# ==============================
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > AUTO_REFRESH_SECONDS:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# ==============================
# DATA LOADING & CACHING
# ==============================
@st.cache_data(ttl=900)
def load_data(ticker):
    daily = yf.download(ticker, period="2y", interval="1d")
    weekly = yf.download(ticker, period="1y", interval="1wk")
    return daily, weekly

# ==============================
# INDICATORS
# ==============================
def calculate_indicators(df):
    df = df.copy()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["GoldenCross"] = (df["MA50"] > df["MA200"]) & (df["MA50"].shift(1) <= df["MA200"].shift(1))
    df["DeathCross"] = (df["MA50"] < df["MA200"]) & (df["MA50"].shift(1) >= df["MA200"].shift(1))

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean().replace(0, np.nan)
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Ichimoku
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
def risk_calc(capital, entry, swing_low, risk_percent):
    stop = swing_low * 0.9
    risk_amount = capital * (risk_percent / 100)
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0, stop
    size = risk_amount / risk_per_share
    return int(size), round(stop, 2)

# ==============================
# DASHBOARD
# ==============================
st.title("📊 Trading Dashboard Pro")

# Dark mode
dark = st.toggle("Dark Mode")
if dark:
    st.markdown("<style>body{background-color:#0E1117;color:white;}</style>", unsafe_allow_html=True)

# Alerts
alerts = []
watch_data = []

for ticker in WATCHLIST:
    daily, weekly = load_data(ticker)
    if daily.empty:
        continue
    daily = calculate_indicators(daily)
    current = daily.iloc[-1]
    if current["GoldenCross"]:
        alerts.append(f"{ticker}: Golden Cross")
    if current["RSI"] < 30:
        alerts.append(f"{ticker}: RSI Oversold")
    perf = ((current["Close"] / daily.iloc[-20]["Close"]) - 1) * 100 if len(daily) > 20 else np.nan
    watch_data.append({
        "Ticker": ticker,
        "Price": round(current["Close"], 2),
        "RSI": round(current["RSI"], 2),
        "MA Status": "Bullish" if current["MA50"] > current["MA200"] else "Bearish",
        "1M %": round(perf, 2)
    })

watch_df = pd.DataFrame(watch_data)
st.subheader("Watchlist")
st.dataframe(watch_df)

# ==============================
# CHARTS
# ==============================
ticker = st.selectbox("Ticker wählen", WATCHLIST)
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

st.caption("Abkürzungen: 1d=Tag, 1wk=Woche, 1mo=Monat, 1y=Jahr")

# ==============================
# RISK MODULE
# ==============================
st.subheader("Risiko-Rechner")
capital = st.number_input("Kapital", value=10000)
risk_percent = st.slider("Risiko %", 0.5, 5.0, RISK_PERCENT_DEFAULT)
if st.button("Berechne Position"):
    entry = daily.iloc[-1]["Close"]
    swing_low = daily["Low"].rolling(20).min().iloc[-1]
    size, stop = risk_calc(capital, entry, swing_low, risk_percent)
    st.success(f"Positionsgröße: {size} Stück | Stop-Loss: {stop}")

# ==============================
# ALERT LOG
# ==============================
st.subheader("Live Alerts")
st.write(alerts[-10:])
