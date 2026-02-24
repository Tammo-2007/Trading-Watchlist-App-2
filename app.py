import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging

# ==============================
# SETTINGS
# ==============================
WATCHLIST_DEFAULT = ["PLTR", "NVDA", "TSLA", "SMCI", "CSG.AS"]
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
# SESSION STATE INITIALIZATION
# ==============================
if "watchlist" not in st.session_state:
    st.session_state.watchlist = WATCHLIST_DEFAULT.copy()

if "alerts" not in st.session_state:
    st.session_state.alerts = []

if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "StopLoss", "TakeProfit", "Status"
    ])

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
    df["GoldenCross"] = ((df["MA50"] > df["MA200"]) & (df["MA50"].shift(1) <= df["MA200"].shift(1)))
    df["DeathCross"] = ((df["MA50"] < df["MA200"]) & (df["MA50"].shift(1) >= df["MA200"].shift(1)))

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

# ==============================
# WATCHLIST MANAGEMENT
# ==============================
with st.expander("🔧 Aktie hinzufügen / löschen"):
    new_ticker = st.text_input("Neuer Ticker")
    buy_price = st.number_input("Kaufpreis (€)", value=0.0)
    qty = st.number_input("Stückzahl", min_value=1, value=1)
    stop = st.number_input("Stop-Loss €", value=0.0)
    take = st.number_input("Take-Profit €", value=0.0)
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])

    if st.button("Hinzufügen"):
        st.session_state.portfolio = pd.concat([
            st.session_state.portfolio,
            pd.DataFrame([{
                "Ticker": new_ticker.upper(),
                "Kaufpreis": buy_price,
                "Stückzahl": qty,
                "StopLoss": stop,
                "TakeProfit": take,
                "Status": status
            }])
        ], ignore_index=True)
        if new_ticker.upper() not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker.upper())
        st.success(f"{new_ticker.upper()} hinzugefügt!")

    del_ticker = st.selectbox("Ticker löschen", st.session_state.watchlist)
    if st.button("Löschen"):
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["Ticker"] != del_ticker]
        st.session_state.watchlist = [t for t in st.session_state.watchlist if t != del_ticker]
        st.success(f"{del_ticker} gelöscht!")

# ==============================
# PORTFOLIO TABLE
# ==============================
st.subheader("📋 Portfolio")
st.dataframe(st.session_state.portfolio)

# ==============================
# CHARTS
# ==============================
chart_ticker = st.selectbox("Ticker wählen für Charts", st.session_state.watchlist)
daily, weekly = load_data(chart_ticker)
daily = calculate_indicators(daily)
weekly = calculate_indicators(weekly)

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
# ALERTS
# ==============================
st.subheader("Live Alerts")
st.session_state.alerts.clear()
for ticker in st.session_state.watchlist:
    daily, _ = load_data(ticker)
    daily = calculate_indicators(daily)
    current = daily.iloc[-1]

    golden = current.get("GoldenCross")
    if isinstance(golden, pd.Series):
        golden = golden.iloc[-1] if len(golden) > 0 else False
    if pd.notna(golden) and golden:
        st.session_state.alerts.append(f"{ticker}: Golden Cross")

    rsi = current.get("RSI")
    if isinstance(rsi, pd.Series):
        rsi = rsi.iloc[-1] if len(rsi) > 0 else np.nan
    if pd.notna(rsi) and rsi < 30:
        st.session_state.alerts.append(f"{ticker}: RSI Oversold")

st.write(st.session_state.alerts[-10:])
