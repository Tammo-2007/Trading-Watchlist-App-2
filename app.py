import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import altair as alt
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# Sidebar Setup
# -----------------------------
st.sidebar.title("Watchlist Einstellungen")

# Watchlist Symbole
watchlist = st.sidebar.text_area(
    "Symbole (getrennt durch Komma)", 
    value="AAPL,MSFT,GOOGL,TSLA"
).upper().replace(" ", "").split(",")

# Timeframe & Period
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1h", "30m", "15m"])
period = st.sidebar.selectbox("Period", ["7d", "14d", "1mo", "3mo"])

# Auto-refresh Intervall
refresh_interval = st.sidebar.number_input(
    "Auto Refresh (Sekunden)", min_value=10, value=60, step=10
)

# Download CSV Button
download_csv = st.sidebar.button("Download aktuelle Daten")

# -----------------------------
# Daten abrufen
# -----------------------------
@st.cache_data(ttl=60)
def fetch_data(symbols, period="7d", interval="1h"):
    all_data = {}
    for symbol in symbols:
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            df['Symbol'] = symbol
            all_data[symbol] = df
        except Exception as e:
            st.warning(f"Fehler bei {symbol}: {e}")
    return all_data

data_dict = fetch_data(watchlist, period=period, interval=timeframe)

# -----------------------------
# Signale berechnen
# -----------------------------
def compute_signals(df):
    df = df.copy()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["Signal"] = np.where(df["MA10"] > df["MA20"], "BUY", "SELL")
    return df

df_list = []
for sym, df in data_dict.items():
    df_signal = compute_signals(df)
    df_signal["Symbol"] = sym
    df_list.append(df_signal)

df_results = pd.concat(df_list)
df_results = df_results.reset_index()  # Datum als Spalte

# -----------------------------
# Styling & Ausgabe
# -----------------------------
def style_signal(val):
    color = ""
    if val == "BUY":
        color = "green"
    elif val == "SELL":
        color = "red"
    return f"background-color: {color}; color:white; font-weight:bold"

st.title("📊 Trading Watchlist")
st.dataframe(df_results.style.applymap(style_signal, subset=["Signal"]))

# -----------------------------
# Chart pro Symbol
# -----------------------------
st.subheader("📈 Chart")
symbol_to_plot = st.selectbox("Symbol für Chart", watchlist)
if symbol_to_plot in data_dict:
    df_chart = data_dict[symbol_to_plot].reset_index()
    chart = alt.Chart(df_chart).mark_line().encode(
        x='Datetime:T',
        y='Close:Q'
    ).properties(width=700, height=400)
    st.altair_chart(chart)

# -----------------------------
# CSV Download
# -----------------------------
if download_csv:
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="watchlist_data.csv",
        mime="text/csv"
    )

# -----------------------------
# Auto Refresh
# -----------------------------
st_autorefresh(interval=refresh_interval * 1000, key="watchlist_refresh")

# -----------------------------
# Optional: Gewinn/Verlust Berechnung (Portfolio)
# -----------------------------
st.subheader("💰 Portfolio Übersicht")
df_portfolio = df_results.groupby("Symbol").agg(
    Open=('Open', 'last'),
    Close=('Close', 'last')
).reset_index()
df_portfolio["PnL"] = df_portfolio["Close"] - df_portfolio["Open"]
df_portfolio["PnL (%)"] = (df_portfolio["PnL"] / df_portfolio["Open"]) * 100
st.dataframe(df_portfolio.style.format({"PnL": "{:.2f}", "PnL (%)": "{:.2f}%"}))
