import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide", page_title="Trading Dashboard Pro")

# ==============================
# SESSION STATE
# ==============================
DEFAULT_WATCHLIST = ["PLTR", "NVDA", "TSLA"]

if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_WATCHLIST.copy()

if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["Ticker", "Kaufpreis", "Stückzahl"]
    )

# ==============================
# DATA LOADER
# ==============================
@st.cache_data(ttl=900)
def load_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(how="all")
        return df

    except Exception:
        return pd.DataFrame()

# ==============================
# INDICATORS
# ==============================
def add_indicators(df):
    df = df.copy()

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    df["GoldenCross"] = (
        (df["MA50"] > df["MA200"]) &
        (df["MA50"].shift(1) <= df["MA200"].shift(1))
    )

    return df

# ==============================
# TITLE
# ==============================
st.title("📊 Trading Dashboard Pro")

# ==============================
# WATCHLIST
# ==============================
with st.expander("🔧 Watchlist verwalten"):

    new_ticker = st.text_input("Ticker hinzufügen")

    if st.button("Hinzufügen"):
        ticker = new_ticker.upper()
        if ticker and ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker)
            st.success(f"{ticker} hinzugefügt")

    if st.session_state.watchlist:
        remove = st.selectbox("Ticker löschen", st.session_state.watchlist)
        if st.button("Löschen"):
            st.session_state.watchlist.remove(remove)
            st.success(f"{remove} gelöscht")

# ==============================
# WATCHLIST TABLE
# ==============================
st.subheader("📈 Watchlist Übersicht")

rows = []

for ticker in st.session_state.watchlist:

    df = load_data(ticker)

    if df.empty:
        continue

    df = add_indicators(df)
    last = df.iloc[-1]

    perf_1m = (
        (last["Close"] / df.iloc[-20]["Close"] - 1) * 100
        if len(df) > 20 else np.nan
    )

    rows.append({
        "Ticker": ticker,
        "Preis": round(last["Close"], 2),
        "1M %": round(perf_1m, 2) if pd.notna(perf_1m) else None,
        "RSI": round(last["RSI"], 2) if pd.notna(last["RSI"]) else None,
        "Golden Cross": bool(last["GoldenCross"])
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ==============================
# PORTFOLIO
# ==============================
st.subheader("💰 Portfolio")

with st.expander("Position hinzufügen"):

    if st.session_state.watchlist:

        ticker = st.selectbox("Ticker", st.session_state.watchlist)
        buy = st.number_input("Kaufpreis", value=0.0)
        qty = st.number_input("Stückzahl", value=1)

        if st.button("Speichern"):
            new_row = pd.DataFrame([{
                "Ticker": ticker,
                "Kaufpreis": buy,
                "Stückzahl": qty
            }])

            st.session_state.portfolio = pd.concat(
                [st.session_state.portfolio, new_row],
                ignore_index=True
            )

if not st.session_state.portfolio.empty:

    pf = st.session_state.portfolio.copy()
    pnl_list = []

    for _, row in pf.iterrows():

        df = load_data(row["Ticker"])

        if df.empty:
            pnl_list.append(0)
            continue

        current_price = df["Close"].iloc[-1]
        pnl = (current_price - row["Kaufpreis"]) * row["Stückzahl"]
        pnl_list.append(round(pnl, 2))

    pf["PnL €"] = pnl_list
    st.dataframe(pf, use_container_width=True)

# ==============================
# CHART (Streamlit native)
# ==============================
st.subheader("📊 Chart")

if st.session_state.watchlist:

    chart_ticker = st.selectbox("Ticker wählen", st.session_state.watchlist)
    df = load_data(chart_ticker)

    if not df.empty:

        df = add_indicators(df)

        chart_df = df[["Close", "MA50", "MA200"]].dropna()
        st.line_chart(chart_df)

        st.subheader("RSI")
        st.line_chart(df["RSI"].dropna().tail(100))

    else:
        st.warning("Keine Daten verfügbar")

# ==============================
# RISK CALCULATOR
# ==============================
st.subheader("⚖ Risiko Rechner")

capital = st.number_input("Kapital", value=10000)
risk_percent = st.slider("Risiko %", 0.5, 5.0, 1.0)

if st.button("Berechnen"):

    if not df.empty:

        entry = df["Close"].iloc[-1]
        swing_low = df["Low"].rolling(20).min().iloc[-1]

        stop = swing_low * 0.98
        risk_amount = capital * (risk_percent / 100)
        risk_per_share = entry - stop

        if risk_per_share > 0:
            size = int(risk_amount / risk_per_share)
            st.success(f"Positionsgröße: {size} Stück | Stop: {round(stop,2)}")
        else:
            st.error("Stop liegt über Entry")
