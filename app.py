import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import feedparser
from datetime import datetime

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"
    ])

if "selected_chart" not in st.session_state:
    st.session_state.selected_chart = "1d"

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1, 1, 1])
ticker = cols[0].text_input("Ticker (z.B. RHM.DE)", help="Börsenkürzel der Aktie eingeben.")
kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, help="Preis, zu dem du die Aktie gekauft hast.")
stk = cols[2].number_input("Stückzahl", min_value=1, step=1, help="Anzahl der gekauften Aktien.")
stop_loss = cols[3].number_input(
    "Stop-Loss €",
    min_value=0.0,
    step=0.01,
    help="Verkaufsgrenze, um Verluste zu begrenzen."
)
take_profit = cols[4].number_input(
    "Take-Profit €",
    min_value=0.0,
    step=0.01,
    help="Zielpreis für Gewinnmitnahme."
)
status = cols[5].selectbox(
    "Status",
    ["Besitzt", "Beobachtung"],
    help="Besitzt = Aktie im Depot, Beobachtung = nur Watchlist."
)

if st.button("Aktie hinzufügen") and ticker:
    new_row = pd.DataFrame([{
        "Ticker": ticker.upper(),
        "Kaufpreis": kaufpreis,
        "Stückzahl": stk,
        "Stop-Loss": stop_loss,
        "Take-Profit": take_profit,
        "Status": status,
        "Gebühr": 1.00
    }])
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
    st.success(f"Aktie {ticker.upper()} hinzugefügt!")
    st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
if not st.session_state.portfolio.empty:
    df = st.session_state.portfolio.copy()
    current_prices = []
    positions = []
    profits = []
    signals = []
    
    for i, row in df.iterrows():
        try:
            data = yf.Ticker(row["Ticker"]).history(period="1d")
            current_price = data["Close"][-1] if not data.empty else 0
        except:
            current_price = 0
        current_prices.append(current_price)
        
        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        positions.append(pos_value)
        
        profit = pos_value - row["Kaufpreis"]*row["Stückzahl"] - row["Gebühr"]
        profits.append(profit)
        
        if profit >= 0:
            signals.append("Halten")
        else:
            signals.append("SELL")
    
    df["Aktueller Preis"] = current_prices
    df["Positionswert"] = positions
    df["Gewinn/Verlust"] = profits
    df["Signal"] = signals
    
    # Löschen-Funktion
    def delete_row(index):
        st.session_state.portfolio = st.session_state.portfolio.drop(index).reset_index(drop=True)
    
    for i, row in df.iterrows():
        cols = st.columns([1,1,1,1,1,1,1])
        cols[0].write(row["Ticker"])
        cols[1].write(f"{row['Aktueller Preis']:.2f} €")
        cols[2].write(f"{row['Positionswert']:.2f} €")
        cols[3].write(f"{row['Gewinn/Verlust']:.2f} €")
        cols[4].write(row["Signal"])
        if cols[5].button("🗑️", key=f"del_{i}"):
            delete_row(i)
            st.experimental_rerun()
else:
    st.info("Keine Aktien im Portfolio.")

# --- Chart mit Zeitrahmen ---
st.subheader("📈 Kursverlauf")
chart_ticker = st.selectbox("Aktie wählen", st.session_state.portfolio["Ticker"] if not st.session_state.portfolio.empty else [])
timeframe = st.radio("Zeitraum", ["Tag", "Woche", "Monat", "Jahr"], horizontal=True,
                     help="Zeitraum für Chartanzeige: Tag=1d, Woche=5d, Monat=1mo, Jahr=1y")

if chart_ticker:
    period_map = {"Tag":"1d","Woche":"5d","Monat":"1mo","Jahr":"1y"}
    try:
        hist = yf.Ticker(chart_ticker).history(period=period_map[timeframe])
        if not hist.empty:
            chart_data = hist.reset_index()
            chart = alt.Chart(chart_data).mark_line().encode(
                x="Date",
                y="Close",
                tooltip=["Date", "Close"]
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Keine historischen Daten verfügbar.")
    except:
        st.error("Chart konnte nicht geladen werden.")

# --- RSS-News ---
st.subheader("📰 News")
rss_url = "https://www.finanzen.net/rss/aktien"
try:
    feed = feedparser.parse(rss_url)
    for entry in feed.entries[:5]:
        st.markdown(f"- [{entry.title}]({entry.link})")
except:
    st.warning("RSS-News nicht verfügbar (installiere feedparser).")
