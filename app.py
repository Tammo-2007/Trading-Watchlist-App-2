import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import altair as alt

# Optional: RSS-News
try:
    import feedparser
    FEED_AVAILABLE = True
except ModuleNotFoundError:
    FEED_AVAILABLE = False

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")

# --- Initialisierung ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

# --- Kompakte Eingabe ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")

cols = st.columns([2,2,2,2])
with cols[0]:
    ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
with cols[1]:
    price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
with cols[2]:
    shares_input = st.number_input("Stückzahl", min_value=1, step=1)
with cols[3]:
    status_input = st.selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen"):
    if ticker_input and price_input and shares_input:
        st.session_state.portfolio.append({
            "Ticker": ticker_input,
            "Kaufpreis": price_input,
            "Stückzahl": shares_input,
            "Status": status_input,
            "Gebühr": 1.0  # Kaufgebühr
        })
        st.success(f"Aktie {ticker_input} hinzugefügt!")
        st.experimental_rerun()

# --- Portfolio-Tabelle ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio:
    portfolio_df = pd.DataFrame(st.session_state.portfolio)
    prices = []
    values = []
    profits = []
    signals = []

    for idx, row in portfolio_df.iterrows():
        try:
            data = yf.download(row["Ticker"], period="1d")
            current_price = data["Close"].iloc[-1] if not data.empty else 0
        except:
            current_price = 0

        prices.append(current_price)
        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        values.append(pos_value)
        profit = pos_value - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"])
        profits.append(profit)
        # Einfacher Signalplatzhalter
        signals.append("Halten" if profit >= 0 else "SELL")

    portfolio_df["Aktueller Preis"] = prices
    portfolio_df["Positionswert"] = values
    portfolio_df["Gewinn/Verlust"] = profits
    portfolio_df["Signal"] = signals
    st.dataframe(portfolio_df[["Ticker","Aktueller Preis","Positionswert","Gewinn/Verlust","Signal","Status","Gebühr"]], height=250)

    # Auswahl für Kursverlauf
    selected = st.selectbox("Wähle eine Aktie", portfolio_df["Ticker"])
    st.session_state.selected_ticker = selected
else:
    st.info("Keine Aktien im Portfolio.")

# --- Kursverlauf ---
if st.session_state.selected_ticker:
    st.subheader("📈 Kursverlauf")
    try:
        df = yf.download(st.session_state.selected_ticker, period="6mo", interval="1d")
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x='Date:T',
            y='Close:Q',
            tooltip=['Date:T','Close:Q','SMA20:Q','SMA50:Q']
        ).interactive()

        st.altair_chart(chart, use_container_width=True)
    except:
        st.warning("Keine Kursdaten verfügbar.")

# --- RSS-News ---
st.subheader("📰 News")
if FEED_AVAILABLE:
    feed = feedparser.parse("https://www.finanzen.net/rss/news")
    for entry in feed.entries[:5]:
        st.write(f"[{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar (installiere feedparser)")
