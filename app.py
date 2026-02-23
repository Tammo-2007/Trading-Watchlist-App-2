import streamlit as st
import yfinance as yf
import pandas as pd

# --- RSS optional ---
try:
    import feedparser
    rss_available = True
except ImportError:
    rss_available = False

# --- Seite einstellen ---
st.set_page_config(page_title="📊 Kompaktes Trading Dashboard Pro", layout="wide")
st.title("📊 Kompaktes Trading Dashboard Pro")

# --- session_state initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1])

ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)", key="ticker_input")
kaufpreis_input = cols[1].number_input("Kaufpreis (€)", min_value=0.0, step=0.01, format="%.2f", key="kaufpreis_input")
stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1, key="stk_input")
status_input = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"], key="status_input")

if st.button("Aktie hinzufügen"):
    if ticker_input.strip() == "":
        st.warning("Bitte einen gültigen Ticker eingeben.")
    else:
        # Aktie zum Portfolio hinzufügen
        st.session_state.portfolio.append({
            "Ticker": ticker_input.upper(),
            "Kaufpreis": kaufpreis_input,
            "Stückzahl": stk_input,
            "Status": status_input,
            "Kaufgebühr": 1.0
        })
        st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
        # Neu laden, aber erst nachdem die session_state korrekt gesetzt ist
        st.experimental_rerun()

# --- Portfolio ---
st.subheader("📋 Portfolio")
if len(st.session_state.portfolio) == 0:
    st.info("Keine Aktien im Portfolio.")
else:
    df_port = pd.DataFrame(st.session_state.portfolio)
    
    # Aktueller Preis abrufen (letzter Schlusskurs)
    def get_last_price(ticker):
        try:
            hist = yf.Ticker(ticker).history(period="1d")
            if hist.empty:
                return None
            return hist["Close"].iloc[-1]
        except:
            return None
    
    df_port["Aktueller Preis"] = df_port["Ticker"].apply(get_last_price)
    df_port["Positionswert"] = df_port["Aktueller Preis"] * df_port["Stückzahl"]
    df_port["Gewinn/Verlust"] = df_port["Positionswert"] - (df_port["Kaufpreis"]*df_port["Stückzahl"] + df_port["Kaufgebühr"])
    df_port["Signal"] = df_port["Gewinn/Verlust"].apply(lambda x: "SELL" if x < 0 else "HOLD")

    st.dataframe(df_port[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]])

# --- Kursverlauf ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", [x["Ticker"] for x in st.session_state.portfolio] if st.session_state.portfolio else [])
if selected_ticker:
    df = yf.download(selected_ticker, period="6mo", interval="1d")
    if df.empty:
        st.warning(f"Keine historischen Daten für {selected_ticker}")
    else:
        st.line_chart(df["Close"])

# --- RSS-News ---
st.subheader("📰 News")
if rss_available:
    feed_url = st.text_input("RSS Feed URL (optional)")
    if feed_url:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:5]:
            st.markdown(f"- [{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar (installiere `feedparser`)")
