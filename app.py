import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# Automatische Aktualisierung
# -----------------------------
# alle 60 Sekunden neu laden
st_autorefresh(interval=60 * 1000, key="datarefresh")

# -----------------------------
# Titel
# -----------------------------
st.title("Trading Watchlist")

# -----------------------------
# Aktienliste
# -----------------------------
# Du kannst hier deine eigenen Symbole eintragen
default_tickers = ["AAPL", "TSLA", "MSFT", "AMZN"]
tickers_input = st.text_area(
    "Aktien-Symbole (durch Komma getrennt)", 
    value=",".join(default_tickers)
)
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# -----------------------------
# Daten abrufen
# -----------------------------
@st.cache_data
def get_data(symbols):
    all_data = []
    for symbol in symbols:
        try:
            data = yf.Ticker(symbol).history(period="5d")
            if data.empty:
                continue
            last_close = data["Close"].iloc[-1]
            prev_close = data["Close"].iloc[-2]
            signal = "Kauf" if last_close > prev_close else "Verkauf"
            all_data.append({
                "Symbol": symbol,
                "Letzter Schluss": last_close,
                "Vorheriger Schluss": prev_close,
                "Signal": signal
            })
        except Exception as e:
            all_data.append({
                "Symbol": symbol,
                "Letzter Schluss": np.nan,
                "Vorheriger Schluss": np.nan,
                "Signal": "Fehler"
            })
    return pd.DataFrame(all_data)

df_results = get_data(tickers)

# -----------------------------
# Styling Funktion für Signale
# -----------------------------
def style_signal(val):
    color = ""
    if val == "Kauf":
        color = "green"
    elif val == "Verkauf":
        color = "red"
    elif val == "Fehler":
        color = "orange"
    return f"color: {color}; font-weight: bold"

# -----------------------------
# Ausgabe
# -----------------------------
st.dataframe(df_results.style.applymap(style_signal, subset=["Signal"]))
