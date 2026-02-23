# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])
if "equity_peak" not in st.session_state:
    st.session_state.equity_peak = 0

# --- Kompaktes Eingabefenster ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1, 1])
ticker = cols[0].text_input("Ticker (z.B. RHM.DE)")
kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
stueckzahl = cols[2].number_input("Stückzahl", min_value=1, step=1)
stop_loss = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
take_profit = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
status = st.radio("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen") and ticker:
    gebuehr = 1.0  # Kaufgebühr
    new_row = pd.DataFrame([{
        "Ticker": ticker.upper(),
        "Kaufpreis": kaufpreis,
        "Stückzahl": stueckzahl,
        "Status": status,
        "Gebühr": gebuehr,
        "Stop-Loss": stop_loss,
        "Take-Profit": take_profit
    }])
    st.session_state.portfolio = pd.concat(
        [st.session_state.portfolio, new_row], ignore_index=True
    )
    st.success(f"Aktie {ticker.upper()} hinzugefügt!")
    st.experimental_rerun()

# --- Portfolio Tabelle ---
st.subheader("📋 Portfolio")
if not st.session_state.portfolio.empty:
    df = st.session_state.portfolio.copy()

    # Aktuelle Kurse abrufen
    df["Aktueller Preis"] = df["Ticker"].apply(
        lambda t: yf.Ticker(t).history(period="1d")["Close"].iloc[-1] if not yf.Ticker(t).history(period="1d").empty else 0
    )
    # Positionswert & Gewinn/Verlust berechnen
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])
    df["Signal"] = df["Gewinn/Verlust"].apply(lambda x: "Halten" if x >= 0 else "SELL")

    # Tabelle anzeigen
    st.dataframe(df[[
        "Ticker", "Kaufpreis", "Stückzahl", "Status",
        "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal"
    ]])

    # Einzelne Aktie löschen
    st.subheader("🗑️ Aktie löschen")
    ticker_to_delete = st.selectbox("Wähle Aktie zum Löschen", df["Ticker"])
    if st.button("Löschen"):
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio.Ticker != ticker_to_delete]
        st.success(f"Aktie {ticker_to_delete} gelöscht!")
        st.experimental_rerun()

# --- Kursverlauf ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Aktie wählen", st.session_state.portfolio["Ticker"] if not st.session_state.portfolio.empty else [])
if selected_ticker:
    data = yf.Ticker(selected_ticker).history(period="6mo")
    if not data.empty:
        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()
        chart = alt.Chart(data.reset_index()).mark_line().encode(
            x="Date:T",
            y="Close:Q",
            tooltip=["Date:T", "Close:Q"]
        )
        sma20 = alt.Chart(data.reset_index()).mark_line(color="orange").encode(x="Date:T", y="SMA20:Q")
        sma50 = alt.Chart(data.reset_index()).mark_line(color="red").encode(x="Date:T", y="SMA50:Q")
        st.altair_chart(chart + sma20 + sma50, use_container_width=True)
    else:
        st.warning("Keine historischen Daten verfügbar.")

# --- RSS-News ---
st.subheader("📰 News")
try:
    import feedparser
    feed_url = "https://finance.yahoo.com/rss/"
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:5]:
        st.markdown(f"- [{entry.title}]({entry.link})")
except ModuleNotFoundError:
    st.info("RSS-News nicht verfügbar (installiere feedparser)")
