import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# RSS-Feed
try:
    import feedparser
    rss_available = True
except ModuleNotFoundError:
    rss_available = False

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

# Initialisierung des Portfolios
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- Obere kompakte Eingabe ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2,1,1,1,1])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)")
kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
stk = cols[2].number_input("Stückzahl", min_value=1, step=1)
status = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"])

if cols[4].button("Aktie hinzufügen"):
    if ticker_input.strip() == "":
        st.warning("Bitte einen Ticker eingeben!")
    else:
        st.session_state.portfolio.append({
            "Ticker": ticker_input.upper(),
            "Kaufpreis": kaufpreis,
            "Stückzahl": stk,
            "Status": status,
            "Gebühr": 1.0
        })
        st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
        st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio:
    df_port = pd.DataFrame(st.session_state.portfolio)
    # Aktueller Preis abrufen
    def fetch_price(ticker):
        try:
            data = yf.Ticker(ticker).history(period="1d")
            return float(data['Close'].iloc[-1])
        except:
            return None

    df_port["Aktueller Preis"] = df_port["Ticker"].apply(fetch_price)
    df_port["Positionswert"] = df_port["Aktueller Preis"] * df_port["Stückzahl"]
    df_port["Gewinn/Verlust"] = df_port["Positionswert"] - (df_port["Kaufpreis"] * df_port["Stückzahl"] + df_port["Gebühr"])
    df_port["Signal"] = df_port["Gewinn/Verlust"].apply(lambda x: "SELL" if x < 0 else "HOLD")

    st.dataframe(df_port[["Ticker","Aktueller Preis","Positionswert","Gewinn/Verlust","Signal","Status"]], use_container_width=True)
else:
    st.info("Keine Aktien im Portfolio")

# --- Detailansicht für Charts ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", [a["Ticker"] for a in st.session_state.portfolio] if st.session_state.portfolio else [])

if selected_ticker:
    data = yf.download(selected_ticker, period="6mo", interval="1d")
    if not data.empty:
        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()
        chart = alt.Chart(data.reset_index()).mark_line().encode(
            x='Date:T',
            y='Close:Q',
            tooltip=['Date:T', 'Close:Q']
        )
        chart += alt.Chart(data.reset_index()).mark_line(color='orange').encode(x='Date:T', y='SMA20:Q')
        chart += alt.Chart(data.reset_index()).mark_line(color='green').encode(x='Date:T', y='SMA50:Q')
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning(f"Für {selected_ticker} sind keine Kursdaten verfügbar.")

# --- RSS-News ---
st.subheader("📰 News")
if rss_available:
    feed_url = f"https://finance.yahoo.com/rss/headline?s={selected_ticker}" if selected_ticker else "https://finance.yahoo.com/rss/topstories"
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:5]:
        st.markdown(f"[{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar (installiere feedparser)")
