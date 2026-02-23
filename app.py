import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import datetime
import json
import os

# --- RSS-News optional ---
try:
    import feedparser
    FEED_AVAILABLE = True
except ImportError:
    FEED_AVAILABLE = False

# --- Portfolio-Datei ---
PORTFOLIO_FILE = "portfolio.json"

# --- Portfolio laden ---
if "aktien_liste" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            st.session_state.aktien_liste = json.load(f)
    else:
        st.session_state.aktien_liste = []

# --- Portfolio speichern ---
def save_portfolio():
    with open(PORTFOLIO_FILE,"w") as f:
        json.dump(st.session_state.aktien_liste, f)

# --- App Header ---
st.header("📊 Kompaktes Trading Dashboard – Alles auf einen Blick")

# --- Signal Einstellungen ---
st.subheader("🔧 Einstellungen für Signale")
SMA20_period = st.slider("SMA20 Periode", 5, 50, 20, help="Kurzfristiger gleitender Durchschnitt")
SMA50_period = st.slider("SMA50 Periode", 10, 200, 50, help="Langfristiger gleitender Durchschnitt")
vol_factor = st.slider("Volumen Faktor", 0.5, 3.0, 1.0, help="Multiplikator für Volumensignale")
RSI_weight = st.slider("RSI Gewicht", 0, 2, 1, help="Gewichtung RSI im Score")
MACD_weight = st.slider("MACD Gewicht", 0, 2, 1, help="Gewichtung MACD im Score")

# --- Portfolio verwalten ---
st.subheader("💼 Portfolio verwalten")
with st.form("portfolio_form"):
    ticker_or_name = st.text_input("Ticker oder Name", help="Trage Ticker z.B. RHM.DE oder den Namen ein")
    name_optional = st.text_input("Name (optional)")
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])
    add_button = st.form_submit_button("Hinzufügen")
    
    if add_button and ticker_or_name:
        # Prüfen, ob bereits vorhanden
        found = any(a["ticker"].upper() == ticker_or_name.upper() for a in st.session_state.aktien_liste)
        if not found:
            st.session_state.aktien_liste.append({
                "ticker": ticker_or_name.upper(),
                "name": name_optional,
                "status": status
            })
            save_portfolio()
        st.experimental_rerun()

# --- Portfolio Übersicht ---
st.subheader("📋 Portfolio")
if st.session_state.aktien_liste:
    for i, a in enumerate(st.session_state.aktien_liste):
        col1, col2, col3 = st.columns([3,1,1])
        display_name = a["name"] if a["name"] else a["ticker"]
        col1.text(f"{display_name} ({a['ticker']})")
        col2.text("🟢 Besitzt" if a["status"]=="Besitzt" else "🟡 Beobachtung")
        # Löschen
        if col3.button("❌", key=f"del_{i}"):
            st.session_state.aktien_liste.pop(i)
            save_portfolio()
            st.experimental_rerun()
else:
    st.info("Keine Aktien im Portfolio. Bitte füge zuerst eine Aktie hinzu.")

# --- Aktien auswählen (nur wenn vorhanden) ---
if st.session_state.aktien_liste:
    selected_ticker = st.selectbox(
        "Wähle eine Aktie",
        [a["ticker"] for a in st.session_state.aktien_liste]
    )

    # --- Kursdaten laden ---
    @st.cache_data
    def load_data(ticker):
        df = yf.download(ticker, period="6mo", interval="1d")
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df["SMA20"] = df["Close"].rolling(SMA20_period).mean()
        df["SMA50"] = df["Close"].rolling(SMA50_period).mean()
        return df

    df = load_data(selected_ticker)
    st.subheader("💰 Aktueller Kurs & Trend")

    if df is None or df.empty:
        st.warning(f"Für {selected_ticker} sind noch keine Kursdaten verfügbar oder Ticker ungültig.")
    else:
        st.text(f"{selected_ticker} Preis: {df['Close'].iloc[-1]:.2f} €")
        
        # --- Chart für letzte 3 Monate ---
        end_date = df["Date"].max()
        start_date = end_date - pd.Timedelta(days=90)
        df_plot = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
        
        chart = alt.Chart(df_plot).transform_fold(
            ["Close","SMA20","SMA50"], as_=["Serie","Wert"]
        ).mark_line().encode(
            x=alt.X("Date:T", title="Datum", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Wert:Q", title="Preis"),
            color="Serie:N",
            tooltip=["Date:T","Serie:N","Wert:Q"]
        ).properties(
            width=800,
            height=400
        )  # kein .interactive() → kein Zoom/Scroll
        st.altair_chart(chart, use_container_width=False)

    # --- RSS-News ---
    st.subheader("📰 RSS-News")
    if FEED_AVAILABLE:
        feeds = [
            "https://www.finanzfluss.de/feed/",
            "https://www.finanztipps.de/feed/",
            "https://www.focus.de/finanzen/rss.xml"
        ]
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                st.markdown(f"- [{entry.title}]({entry.link})")
    else:
        st.info("RSS-News nicht verfügbar (installiere feedparser)")
