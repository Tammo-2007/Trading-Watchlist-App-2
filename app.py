import streamlit as st
import yfinance as yf
import pandas as pd
import time
import feedparser
from textblob import TextBlob
import ta  # technische Indikatoren

st.set_page_config(page_title="Trading Watchlist", layout="wide")

# -----------------------------
# Watchlist
# -----------------------------
watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "RHM.DE"]  # gültige Symbole
interval = 10  # Sekunden zwischen Updates

# -----------------------------
# Stop/Start Buttons
# -----------------------------
stop_flag = st.session_state.get("stop_flag", False)
stop_placeholder = st.empty()
start_placeholder = st.empty()

if stop_placeholder.button("Stop Analyse", key="stop_button"):
    stop_flag = True
    st.session_state["stop_flag"] = True
    st.warning("Analyse gestoppt!")

if start_placeholder.button("Starte Analyse", key="start_button"):
    stop_flag = False
    st.session_state["stop_flag"] = False
    st.success("Analyse gestartet!")

# -----------------------------
# Funktion: Yahoo-Daten holen
# -----------------------------
def get_stock_data(symbol):
    try:
        df = yf.download(symbol, period="2y", interval="1d")
        if df.empty:
            return None
        # Technische Indikatoren
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        df["EMA20"] = ta.trend.EMAIndicator(df["Close"], window=20).ema_indicator()
        df["EMA50"] = ta.trend.EMAIndicator(df["Close"], window=50).ema_indicator()
        df["EMA200"] = ta.trend.EMAIndicator(df["Close"], window=200).ema_indicator()
        df["ATR"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()
        return df
    except Exception as e:
        st.error(f"Fehler bei {symbol}: {e}")
        return None

# -----------------------------
# Funktion: News Sentiment
# -----------------------------
def get_sentiment(symbol):
    rss_url = "https://www.finanzen.net/rss/aktien"
    feed = feedparser.parse(rss_url)
    scores = []
    for entry in feed.entries:
        if symbol in entry.title:
            scores.append(TextBlob(entry.title).sentiment.polarity)
    if scores:
        return round(sum(scores)/len(scores)*100,2)
    else:
        return 0

# -----------------------------
# Ergebnisse vorbereiten
# -----------------------------
results = []
for symbol in watchlist:
    df = get_stock_data(symbol)
    if df is None:
        continue
    sentiment = get_sentiment(symbol)
    latest_close = df["Close"].iloc[-1]
    
    # Beispiel-Signal Logik (kann angepasst werden)
    if df["RSI"].iloc[-1] < 30:
        signal = "Starkes Kaufsignal"
    elif df["RSI"].iloc[-1] < 50:
        signal = "Kauf"
    elif df["RSI"].iloc[-1] < 70:
        signal = "Beobachten"
    else:
        signal = "Verkaufssignal"
    
    results.append({
        "Ticker": symbol,
        "Letzter Kurs": latest_close,
        "RSI": round(df["RSI"].iloc[-1],2),
        "EMA20": round(df["EMA20"].iloc[-1],2),
        "EMA50": round(df["EMA50"].iloc[-1],2),
        "EMA200": round(df["EMA200"].iloc[-1],2),
        "ATR": round(df["ATR"].iloc[-1],2),
        "Sentiment %": sentiment,
        "Signal": signal
    })

df_results = pd.DataFrame(results)

# -----------------------------
# Signalfarben
# -----------------------------
def style_signal(val):
    if val == "Starkes Kaufsignal":
        return 'background-color: lightgreen'
    elif val == "Kauf":
        return 'background-color: green'
    elif val == "Beobachten":
        return 'background-color: yellow'
    elif val == "Neutral / Vorsicht":
        return 'background-color: orange'
    elif val == "Verkaufssignal":
        return 'background-color: red'
    else:
        return ''

# -----------------------------
# Ausgabe
# -----------------------------
st.dataframe(df_results.style.map(style_signal, subset=["Signal"]))

# -----------------------------
# Live Update
# -----------------------------
while not stop_flag:
    st.info("Analyse läuft...")
    time.sleep(interval)
    break  # Entfernen, um dauerhaft laufen zu lassen
