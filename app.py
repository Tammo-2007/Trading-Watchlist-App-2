import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- RSS optional ---
try:
    import feedparser
    rss_available = True
except ImportError:
    rss_available = False

# --- App Einstellungen ---
st.set_page_config(page_title="📊 Kompaktes Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1])

ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)", key="ticker")
kaufpreis_input = cols[1].number_input("Kaufpreis (€)", min_value=0.0, step=0.01, format="%.2f", key="price")
stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1, key="stk")
status_input = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"], key="status")

if st.button("Aktie hinzufügen"):
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    st.session_state.portfolio.append({
        "Ticker": ticker_input.upper(),
        "Kaufpreis": kaufpreis_input,
        "Stückzahl": stk_input,
        "Status": status_input,
        "Kaufgebühr": 1.0  # feste Gebühr
    })
    st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
    st.experimental_rerun()

# --- Portfolio ---
st.subheader("📋 Portfolio")
if "portfolio" not in st.session_state or len(st.session_state.portfolio) == 0:
    st.info("Keine Aktien im Portfolio.")
else:
    df_port = pd.DataFrame(st.session_state.portfolio)
    df_port["Aktueller Preis"] = df_port["Ticker"].apply(lambda x: yf.Ticker(x).history(period="1d")["Close"][-1] if yf.Ticker(x).history(period="1d").shape[0]>0 else None)
    df_port["Positionswert"] = df_port["Aktueller Preis"] * df_port["Stückzahl"]
    df_port["Gewinn/Verlust"] = df_port["Positionswert"] - (df_port["Kaufpreis"]*df_port["Stückzahl"] + df_port["Kaufgebühr"])
    df_port["Signal"] = ["SELL" if x < 0 else "HOLD" for x in df_port["Gewinn/Verlust"]]

    st.dataframe(df_port[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]])

# --- Kursverlauf ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", [x["Ticker"] for x in st.session_state.portfolio] if "portfolio" in st.session_state else [])
if selected_ticker:
    df = yf.download(selected_ticker, period="6mo", interval="1d")
    if df.empty:
        st.warning(f"Keine historischen Daten für {selected_ticker}")
    else:
        st.line_chart(df["Close"])

# --- RSS-News ---
st.subheader("📰 News")
if rss_available:
    feed_url = st.text_input("RSS Feed URL (optional)", "")
    if feed_url:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:5]:
            st.markdown(f"- [{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar (installiere `feedparser`)")
