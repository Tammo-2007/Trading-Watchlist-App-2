import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Optional für RSS-News
try:
    import feedparser
    feedparser_installed = True
except ImportError:
    feedparser_installed = False

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# Session State für Portfolio
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1])
with cols[0]:
    ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
with cols[1]:
    buy_price = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
with cols[2]:
    shares = st.number_input("Stückzahl", min_value=1, step=1)
with cols[3]:
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])

add_btn = st.button("Aktie hinzufügen")

if add_btn and ticker_input:
    fee = 1.0  # Kaufgebühr
    st.session_state.portfolio = pd.concat([
        st.session_state.portfolio,
        pd.DataFrame([{
            "Ticker": ticker_input,
            "Kaufpreis": buy_price,
            "Stückzahl": shares,
            "Status": status,
            "Gebühr": fee
        }])
    ], ignore_index=True)
    st.success(f"Aktie {ticker_input} hinzugefügt!")

# --- Portfolio Tabelle ---
st.subheader("📋 Portfolio")
if not st.session_state.portfolio.empty:
    portfolio_df = st.session_state.portfolio.copy()
    
    # Aktuelle Preise holen
    prices = []
    signals = []
    values = []
    profits = []

    for _, row in portfolio_df.iterrows():
        current_price = 0.0
        try:
            data = yf.download(row["Ticker"], period="1d", progress=False)
            if not data.empty:
                current_price = float(data["Close"].iloc[-1])
        except:
            pass
        prices.append(current_price)

        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        values.append(pos_value)

        profit = float(pos_value - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"]))
        profits.append(profit)

        signals.append("Halten" if profit >= 0 else "SELL")

    portfolio_df["Aktueller Preis"] = prices
    portfolio_df["Positionswert"] = values
    portfolio_df["Gewinn/Verlust"] = profits
    portfolio_df["Signal"] = signals

    # Löschen-Funktion
    def delete_row(index):
        st.session_state.portfolio = st.session_state.portfolio.drop(index).reset_index(drop=True)

    for i, row in portfolio_df.iterrows():
        cols = st.columns([2,1,1,1,1,1,1])
        cols[0].write(row["Ticker"])
        cols[1].write(f"{row['Aktueller Preis']:.2f} €")
        cols[2].write(f"{row['Positionswert']:.2f} €")
        cols[3].write(f"{row['Gewinn/Verlust']:.2f} €")
        cols[4].write(row["Signal"])
        if cols[5].button("Löschen", key=f"del_{i}"):
            delete_row(i)
            st.experimental_rerun()

# --- Kursgrafik ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", st.session_state.portfolio["Ticker"].tolist() if not st.session_state.portfolio.empty else [])
if selected_ticker:
    try:
        data = yf.download(selected_ticker, period="6mo", interval="1d", progress=False)
        st.line_chart(data["Close"], height=300)  # feste Höhe, keine Größenänderung
    except:
        st.warning(f"Für {selected_ticker} sind keine historischen Daten verfügbar.")

# --- RSS-News ---
st.subheader("📰 News")
if feedparser_installed:
    for ticker in st.session_state.portfolio["Ticker"].tolist():
        feed_url = f"https://finanzen.net/rss/{ticker}"
        feed = feedparser.parse(feed_url)
        st.write(f"**{ticker} News:**")
        if feed.entries:
            for entry in feed.entries[:5]:
                st.write(f"- [{entry.title}]({entry.link})")
        else:
            st.write("Keine aktuellen News gefunden.")
else:
    st.info("RSS-News nicht verfügbar (installiere `feedparser`).")
