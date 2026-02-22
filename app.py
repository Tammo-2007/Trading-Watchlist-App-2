# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ta.trend import SMAIndicator, EMAIndicator, ADXIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import requests

st.set_page_config(page_title="Profi Aktien Dashboard", layout="wide")

# -----------------------------
# Einstellungen / Schalter
# -----------------------------
st.sidebar.header("Einstellungen")
symbol_mode = st.sidebar.radio("Anzeige:", ["Ticker", "Name"])
live_update = st.sidebar.checkbox("Live Update", value=True)
update_interval = st.sidebar.slider("Update Intervall (Sekunden)", 30, 300, 60)

# Beispiel Aktienliste mit Namen
aktien_dict = {
    "RHM.DE": "Rheinmetall",
    "SAP.DE": "SAP",
    "DAI.DE": "Daimler",
    "BMW.DE": "BMW",
    "ALV.DE": "Allianz"
}
symbols = list(aktien_dict.keys())

# -----------------------------
# Aktien auswählen
# -----------------------------
selected = st.multiselect("Aktien auswählen", symbols, default=symbols[:3])

# -----------------------------
# Daten abrufen
# -----------------------------
def get_stock_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d")
    df = df.dropna()
    return df

# -----------------------------
# Technische Indikatoren berechnen
# -----------------------------
def calculate_indicators(df):
    df["SMA20"] = SMAIndicator(df["Close"], 20).sma_indicator()
    df["EMA20"] = EMAIndicator(df["Close"], 20).ema_indicator()
    macd = MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["RSI"] = RSIIndicator(df["Close"]).rsi()
    bb = BollingerBands(df["Close"])
    df["BB_High"] = bb.bollinger_hband()
    df["BB_Low"] = bb.bollinger_lband()
    df["ADX"] = ADXIndicator(df["High"], df["Low"], df["Close"]).adx()
    df["Volumen"] = df["Volume"]
    return df

# -----------------------------
# Signalberechnung
# -----------------------------
def generate_signal(row):
    score = 0
    if row["Close"] > row["SMA20"]:
        score += 1
    if row["Close"] > row["EMA20"]:
        score += 1
    if row["MACD"] > row["MACD_Signal"]:
        score += 1
    if row["RSI"] < 30:
        score += 1
    if row["Close"] < row["BB_Low"]:
        score += 1
    if row["ADX"] > 25:
        score += 1
    if row["Volumen"] > row["Volumen"].rolling(5).mean().iloc[-1]:
        score += 1
    if score >= 5:
        return "BUY"
    elif score <= 2:
        return "SELL"
    else:
        return "HOLD"

# -----------------------------
# Daten aufbereiten
# -----------------------------
results = []
for sym in selected:
    df = get_stock_data(sym)
    df = calculate_indicators(df)
    last_row = df.iloc[-1]
    signal = generate_signal(last_row)
    stop_loss = last_row["Close"] * 0.95
    results.append({
        "Symbol": sym,
        "Name": aktien_dict[sym],
        "Letzter Preis": last_row["Close"],
        "Signal": signal,
        "Stop-Loss": round(stop_loss,2),
        "RSI": round(last_row["RSI"],2),
        "MACD": round(last_row["MACD"],2)
    })

df_results = pd.DataFrame(results)

# Symbol oder Name anzeigen
if symbol_mode == "Ticker":
    st.dataframe(df_results.drop("Name", axis=1))
else:
    st.dataframe(df_results.drop("Symbol", axis=1))

# -----------------------------
# News-Fenster
# -----------------------------
st.header("Aktien-News (komprimiert)")
def fetch_news(symbol):
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        r = requests.get(url)
        if r.status_code == 200:
            return f"Wichtige News für {symbol} geladen."
        else:
            return f"Keine News für {symbol} verfügbar."
    except:
        return "Fehler beim Laden der News."

for sym in selected:
    st.subheader(f"{aktien_dict[sym]} ({sym})")
    st.write(fetch_news(sym))

# -----------------------------
# Auto-Refresh
# -----------------------------
if live_update:
    import time
    time.sleep(update_interval)
    st.experimental_rerun()
