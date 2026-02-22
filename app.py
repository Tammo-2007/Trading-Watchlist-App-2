import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import ta
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide", page_title="Trading Entscheidungs-Dashboard")
st_autorefresh(interval=60 * 1000, key="refresh")

st.title("📊 Trading Entscheidungs-Dashboard")

# -----------------------------
# Eingabe
# -----------------------------
default_symbols = "RHM.DE,AAPL,MSFT,SPY"
symbols_input = st.text_area("Aktien / ETFs (Komma getrennt)", value=default_symbols)
symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# -----------------------------
# Datenfunktion
# -----------------------------
@st.cache_data(ttl=300)
def load_market_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="6mo")

    if hist.empty:
        return None, None, None

    # Indikatoren
    hist["EMA20"] = ta.trend.ema_indicator(hist["Close"], window=20)
    hist["EMA50"] = ta.trend.ema_indicator(hist["Close"], window=50)
    hist["RSI"] = ta.momentum.rsi(hist["Close"], window=14)
    hist["ATR"] = ta.volatility.average_true_range(
        hist["High"], hist["Low"], hist["Close"], window=14
    )

    # Name
    try:
        name = ticker.info.get("longName", symbol)
    except:
        name = symbol

    return hist, name, hist.iloc[-1]

# -----------------------------
# Score Berechnung
# -----------------------------
def calculate_score(last_row):
    score = 0

    if last_row["Close"] > last_row["EMA20"]:
        score += 1
    if last_row["EMA20"] > last_row["EMA50"]:
        score += 1
    if 40 < last_row["RSI"] < 65:
        score += 1
    if last_row["RSI"] < 30:
        score += 1
    if last_row["Close"] > last_row["EMA50"]:
        score += 1

    return score

# -----------------------------
# Übersicht erstellen
# -----------------------------
overview = []

for symbol in symbols:
    hist, name, last = load_market_data(symbol)
    if hist is None:
        continue

    score = calculate_score(last)

    trend = "Bullisch" if last["EMA20"] > last["EMA50"] else "Bärisch"

    overview.append({
        "Name": name,
        "Symbol": symbol,
        "Kurs": round(last["Close"], 2),
        "Trend": trend,
        "RSI": round(last["RSI"], 1),
        "Score (0-5)": score
    })

overview_df = pd.DataFrame(overview)

# -----------------------------
# Anzeige Übersicht
# -----------------------------
st.subheader("📈 Marktübersicht")

if not overview_df.empty:
    st.dataframe(overview_df.sort_values("Score (0-5)", ascending=False),
                 use_container_width=True)
else:
    st.warning("Keine Daten geladen.")

# -----------------------------
# Detailbereich
# -----------------------------
st.subheader("🔍 Detailanalyse")

if symbols:
    selected_symbol = st.selectbox("Asset auswählen", symbols)
    hist, name, last = load_market_data(selected_symbol)

    if hist is not None:

        col1, col2 = st.columns([2,1])

        with col1:
            st.write(f"### {name}")
            chart_df = hist[["Close", "EMA20", "EMA50"]]
            st.line_chart(chart_df)

        with col2:
            score = calculate_score(last)
            stop_loss = last["Close"] - last["ATR"] * 1.5
            risk_pct = ((last["Close"] - stop_loss) / last["Close"]) * 100

            st.metric("Aktueller Kurs", round(last["Close"],2))
            st.metric("RSI", round(last["RSI"],1))
            st.metric("Score", score)

            st.write("### Stop-Loss Vorschlag")
            st.write(f"{round(stop_loss,2)}")
            st.write(f"Risiko: {round(risk_pct,2)} %")

            if score >= 4:
                st.success("Technisch stark")
            elif score >= 2:
                st.warning("Neutral / Beobachten")
            else:
                st.error("Technisch schwach")
