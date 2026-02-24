import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide", page_title="Trading Dashboard Pro")

# ==============================
# SETTINGS
# ==============================
DEFAULT_WATCHLIST = ["PLTR", "NVDA", "TSLA"]

if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_WATCHLIST.copy()

if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl"
    ])

# ==============================
# DATA LOADER (MultiIndex FIX)
# ==============================
@st.cache_data(ttl=900)
def load_data(ticker):
    df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna(how="all")
    return df

# ==============================
# INDICATORS
# ==============================
def calculate_indicators(df):
    df = df.copy()

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    df["GoldenCross"] = (
        (df["MA50"] > df["MA200"]) &
        (df["MA50"].shift(1) <= df["MA200"].shift(1))
    )

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ==============================
# TITLE
# ==============================
st.title("📊 Trading Dashboard Pro")

# ==============================
# WATCHLIST MANAGEMENT
# ==============================
with st.expander("🔧 Watchlist verwalten"):

    new_ticker = st.text_input("Ticker hinzufügen")

    if st.button("Hinzufügen"):
        ticker = new_ticker.upper()
        if ticker and ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker)
            st.success(f"{ticker} hinzugefügt")

    remove_ticker = st.selectbox("Ticker löschen", st.session_state.watchlist)

    if st.button("Löschen"):
        st.session_state.watchlist.remove(remove_ticker)
        st.success(f"{remove_ticker} gelöscht")

# ==============================
# WATCHLIST OVERVIEW
# ==============================
st.subheader("📈 Watchlist Übersicht")

watch_data = []

for ticker in st.session_state.watchlist:
    df = load_data(ticker)

    if df.empty:
        continue

    df = calculate_indicators(df)
    current = df.iloc[-1]

    perf_1m = (
        (current["Close"] / df.iloc[-20]["Close"] - 1) * 100
        if len(df) > 20 else np.nan
    )

    golden = bool(current["GoldenCross"]) if pd.notna(current["GoldenCross"]) else False

    watch_data.append({
        "Ticker": ticker,
        "Preis": round(current["Close"], 2),
        "1M %": round(perf_1m, 2) if pd.notna(perf_1m) else None,
        "RSI": round(current["RSI"], 2) if pd.notna(current["RSI"]) else None,
        "Golden Cross": golden
    })

watch_df = pd.DataFrame(watch_data)
st.dataframe(watch_df, use_container_width=True)

# ==============================
# PORTFOLIO
# ==============================
st.subheader("💰 Portfolio")

with st.expander("Position hinzufügen"):
    p_ticker = st.selectbox("Ticker", st.session_state.watchlist)
    p_buy = st.number_input("Kaufpreis", value=0.0)
    p_qty = st.number_input("Stückzahl", value=1)

    if st.button("Position speichern"):
        new_row = pd.DataFrame([{
            "Ticker": p_ticker,
            "Kaufpreis": p_buy,
            "Stückzahl": p_qty
        }])

        st.session_state.portfolio = pd.concat(
            [st.session_state.portfolio, new_row],
            ignore_index=True
        )

if not st.session_state.portfolio.empty:

    portfolio_df = st.session_state.portfolio.copy()
    pnl_values = []

    for _, row in portfolio_df.iterrows():
        df = load_data(row["Ticker"])
        if not df.empty:
            current_price = df["Close"].iloc[-1]
            pnl = (current_price - row["Kaufpreis"]) * row["Stückzahl"]
            pnl_values.append(round(pnl, 2))
        else:
            pnl_values.append(0)

    portfolio_df["PnL €"] = pnl_values
    st.dataframe(portfolio_df, use_container_width=True)

# ==============================
# CHART SECTION
# ==============================
st.subheader("📊 Chart")

chart_ticker = st.selectbox("Ticker wählen", st.session_state.watchlist)
df = load_data(chart_ticker)

if not df.empty:
    df = calculate_indicators(df)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA50"],
        mode="lines",
        name="MA50"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA200"],
        mode="lines",
        name="MA200"
    ))

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("RSI")
    st.line_chart(df["RSI"].tail(100))

else:
    st.warning("Keine Daten verfügbar")

# ==============================
# RISK CALCULATOR
# ==============================
st.subheader("⚖ Risiko Rechner")

capital = st.number_input("Kapital", value=10000)
risk_percent = st.slider("Risiko %", 0.5, 5.0, 1.0)

if st.button("Berechnen"):
    entry = df["Close"].iloc[-1]
    swing_low = df["Low"].rolling(20).min().iloc[-1]

    stop = swing_low * 0.98
    risk_amount = capital * (risk_percent / 100)
    risk_per_share = entry - stop

    if risk_per_share > 0:
        size = int(risk_amount / risk_per_share)
        st.success(f"Positionsgröße: {size} Stück | Stop: {round(stop,2)}")
    else:
        st.error("Stop liegt über Entry – prüfen")
