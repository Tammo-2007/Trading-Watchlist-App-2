import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

# RSS optional
try:
    import feedparser
    feedparser_available = True
except ModuleNotFoundError:
    feedparser_available = False

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session-State Initialisierung ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- Eingabe: Signaleinstellungen & Aktie hinzufügen ---
with st.expander("🔧 Signaleinstellungen & Aktie hinzufügen", expanded=True):
    col1, col2, col3 = st.columns([3,2,2])
    with col1:
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)", help="Gib das Börsenkürzel der Aktie ein")
    with col2:
        kaufpreis = st.number_input("Kaufpreis (€)", min_value=0.0, step=0.01, format="%.2f", help="Preis pro Aktie beim Kauf")
    with col3:
        st.number_input("Stückzahl", min_value=1, step=1, key="stk", help="Anzahl der gekauften Aktien")
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"], help="Besitzt = im Depot, Beobachtung = Watchlist")

    if st.button("Aktie hinzufügen"):
        if ticker_input.strip() == "":
            st.warning("Bitte einen Ticker eingeben!")
        else:
            st.session_state.portfolio.append({
                "Ticker": ticker_input.upper(),
                "Kaufpreis": kaufpreis,
                "Stückzahl": st.session_state.stk,
                "Status": status,
                "Gebühr": 1.0
            })
            st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
            st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio:
    df = pd.DataFrame(st.session_state.portfolio)

    # Aktuelle Preise abfragen
    current_prices = {}
    for t in df["Ticker"]:
        try:
            data = yf.download(t, period="1d")
            current_prices[t] = data["Close"].iloc[-1] if not data.empty else None
        except:
            current_prices[t] = None

    df["Aktueller Preis"] = df["Ticker"].map(current_prices)
    df["Positionswert"] = df["Stückzahl"] * df["Aktueller Preis"].fillna(0) - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Stückzahl"] * df["Kaufpreis"] + df["Gebühr"])
    df["Signal"] = df["Gewinn/Verlust"].apply(lambda x: "SELL" if x < 0 else "HOLD")

    st.dataframe(df, use_container_width=True)

    # Verkaufsbuttons
    for idx, row in df.iterrows():
        if st.button(f"Verkauf {row['Ticker']}", key=f"sell_{idx}"):
            st.session_state.portfolio.pop(idx)
            st.experimental_rerun()
else:
    st.info("Noch keine Aktien im Portfolio.")

# --- Detailansicht / Chart ---
if st.session_state.portfolio:
    selected_ticker = st.selectbox("📈 Detailansicht wählen", options=[p["Ticker"] for p in st.session_state.portfolio])
    if selected_ticker:
        try:
            df_chart = yf.download(selected_ticker, period="6mo", interval="1d")
            if not df_chart.empty:
                chart = alt.Chart(df_chart.reset_index()).mark_line().encode(
                    x="Date:T",
                    y="Close:Q"
                ).properties(height=300, width=700)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.warning("Keine historischen Daten verfügbar.")
        except:
            st.error("Fehler beim Laden der Kursdaten.")

# --- RSS-News ---
if feedparser_available and st.session_state.portfolio:
    st.subheader("📰 RSS-News")
    feed_url = f"https://finance.yahoo.com/rss/headline?s={selected_ticker}"
    feed = feedparser.parse(feed_url)
    if feed.entries:
        for entry in feed.entries[:5]:
            st.markdown(f"- [{entry.title}]({entry.link})")
    else:
        st.info("Keine News verfügbar.")
elif not feedparser_available:
    st.info("RSS-News nicht verfügbar. Installiere feedparser für News.")
