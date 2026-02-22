import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ----------------------------
# Auto Refresh (60 Sekunden)
# ----------------------------
st_autorefresh(interval=60 * 1000, key="refresh")

# ----------------------------
# Seitenlayout
# ----------------------------
st.set_page_config(page_title="Trading Watchlist", layout="wide")

st.title("📈 Trading Watchlist")

# ----------------------------
# Eingabe der Symbole
# ----------------------------
default_symbols = "AAPL,MSFT,TSLA,AMZN"

symbols_input = st.text_area(
    "Aktien oder ETFs (Komma getrennt)",
    value=default_symbols
)

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# ----------------------------
# Daten laden
# ----------------------------
@st.cache_data(ttl=60)
def load_data(ticker_list):
    results = []

    for ticker in ticker_list:
        try:
            data = yf.Ticker(ticker).history(period="5d")

            if len(data) < 2:
                continue

            last_close = data["Close"].iloc[-1]
            prev_close = data["Close"].iloc[-2]

            change = last_close - prev_close
            change_pct = (change / prev_close) * 100

            signal = "Kauf" if change > 0 else "Verkauf"

            results.append({
                "Symbol": ticker,
                "Letzter Kurs": round(last_close, 2),
                "Veränderung": round(change, 2),
                "Veränderung %": round(change_pct, 2),
                "Signal": signal
            })

        except Exception:
            results.append({
                "Symbol": ticker,
                "Letzter Kurs": np.nan,
                "Veränderung": np.nan,
                "Veränderung %": np.nan,
                "Signal": "Fehler"
            })

    return pd.DataFrame(results)


df = load_data(symbols)

# ----------------------------
# Styling
# ----------------------------
def style_signal(val):
    if val == "Kauf":
        return "color: green; font-weight: bold;"
    if val == "Verkauf":
        return "color: red; font-weight: bold;"
    if val == "Fehler":
        return "color: orange; font-weight: bold;"
    return ""

# ----------------------------
# Anzeige
# ----------------------------
if not df.empty:
    st.dataframe(df.style.applymap(style_signal, subset=["Signal"]),
                 use_container_width=True)
else:
    st.warning("Keine gültigen Daten gefunden.")

# ----------------------------
# Chart Auswahl
# ----------------------------
st.subheader("📊 Chart")

if symbols:
    selected_symbol = st.selectbox("Symbol auswählen", symbols)

    try:
        chart_data = yf.Ticker(selected_symbol).history(period="1mo")

        st.line_chart(chart_data["Close"])

    except Exception:
        st.error("Chart konnte nicht geladen werden.")
