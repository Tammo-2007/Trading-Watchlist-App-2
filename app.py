# Streamlit Trading Watchlist Web-App

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from textblob import TextBlob
import feedparser
import ta
from sklearn.ensemble import RandomForestClassifier
import time

st.set_page_config(page_title="Trading Watchlist", layout="wide")

st.title("📊 Trading Watchlist Web-App")

# --- Watchlist Eingabe ---
watchlist_input = st.text_input(
    "Gib Aktien/ETFs ein (Komma getrennt):",
    value="AAPL, MSFT, GOOGL, AMZN"
)
watchlist = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

# --- Intervall ---
interval = st.slider("Intervall (Sekunden)", 5, 120, 30)

# --- Start / Stop Buttons ---
start_btn = st.button("Start Analyse")
stop_placeholder = st.empty()

# --- Platz für Ausgabe ---
output_table = st.empty()

# --- Flag für Stop ---
stop_flag = False

def analyse_watchlist():
    global stop_flag
    results = {}
    
    # RSS Feed
    rss_url = "https://www.finanzen.net/rss/aktien"
    feed = feedparser.parse(rss_url)

    for ticker in watchlist:
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            close = df["Close"].squeeze()
            high = df["High"].squeeze()
            low = df["Low"].squeeze()

            df["RSI"] = ta.momentum.RSIIndicator(close).rsi()
            df["EMA20"] = ta.trend.EMAIndicator(close, window=20).ema_indicator()
            df["EMA50"] = ta.trend.EMAIndicator(close, window=50).ema_indicator()
            df["EMA200"] = ta.trend.EMAIndicator(close, window=200).ema_indicator()
            df["ATR"] = ta.volatility.AverageTrueRange(high, low, close).average_true_range()

            df_clean = df.dropna()
            df_clean["Target"] = (df_clean["Close"].shift(-1) > df_clean["Close"]).astype(int)
            features = ["RSI", "EMA20", "EMA50", "EMA200", "ATR"]
            X = df_clean[features]
            y = df_clean["Target"]

            model = RandomForestClassifier()
            model.fit(X, y)

            latest = df_clean.iloc[-1]
            latest_features = latest[features].values.reshape(1, -1)
            score = round(model.predict_proba(latest_features)[0][1] * 100, 2)
            entry_price = latest["Close"]
            atr = latest["ATR"]
            stop_loss = round(entry_price - (atr * 2), 2)

            # News-Sentiment
            scores = []
            for entry in feed.entries:
                if ticker in entry.title:
                    analysis = TextBlob(entry.title)
                    scores.append(analysis.sentiment.polarity)
            news_score = round(sum(scores)/len(scores)*100, 2) if scores else 0
            combined_score = round(0.7*score + 0.3*news_score, 2)

            if combined_score >= 80:
                signal = "Starkes Kaufsignal"
            elif combined_score >= 60:
                signal = "Beobachten"
            elif combined_score >= 40:
                signal = "Neutral / Vorsichtig"
            else:
                signal = "Verkaufssignal"

            results[ticker] = {
                "KI-Score": score,
                "News-Sentiment": news_score,
                "Kombinierter Score": combined_score,
                "Signal": signal,
                "ATR Stop": stop_loss
            }
        except:
            results[ticker] = {"Fehler": "Daten konnten nicht geladen werden"}
    
    return results

# --- Hauptloop ---
if start_btn:
    stop_flag = False
    while not stop_flag:
        results = analyse_watchlist()
        df_results = pd.DataFrame(results).T
        output_table.dataframe(df_results.style.applymap(
            lambda v: 'background-color: lightgreen' if v=="Starkes Kaufsignal" else
                      'background-color: yellow' if v=="Beobachten" else
                      'background-color: orange' if v=="Neutral / Vorsichtig" else
                      'background-color: red' if v=="Verkaufssignal" else ''
        ))
        stop_placeholder.button("Stop Analyse", on_click=lambda: setattr(globals(), "stop_flag", True))
        time.sleep(interval)
