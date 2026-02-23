import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import feedparser

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")

# ---------- SESSION STATE ----------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# ---------- SIGNAL & AKTIE HINZUFÜGEN ----------
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")

cols = st.columns([2,1,1,1])
with cols[0]:
    ticker_input = st.text_input("Ticker (z.B. RHM.DE)", "").upper()
with cols[1]:
    buy_price = st.number_input("Kaufpreis (€)", min_value=0.0, step=0.01)
with cols[2]:
    quantity = st.number_input("Stückzahl", min_value=1, step=1)
with cols[3]:
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen") and ticker_input:
    # Kaufgebühr 1€
    st.session_state.portfolio.append({
        "Ticker": ticker_input,
        "Kaufpreis": buy_price,
        "Stückzahl": quantity,
        "Status": status,
        "Gebühr": 1.0
    })
    st.success(f"Aktie {ticker_input} hinzugefügt!")
    st.experimental_rerun()

# ---------- PORTFOLIO TABELLE ----------
st.subheader("📋 Portfolio")
if st.session_state.portfolio:
    df_port = pd.DataFrame(st.session_state.portfolio)
    
    # Kursdaten abrufen
    aktuelle_preise = []
    gewinn_verlust = []
    signal = []

    for i, row in df_port.iterrows():
        try:
            data = yf.download(row["Ticker"], period="1d", interval="1d")
            if not data.empty:
                price = data["Close"].iloc[-1]
                aktuelle_preise.append(price)
                pos_value = price * row["Stückzahl"] - row["Gebühr"]
                profit = pos_value - (row["Kaufpreis"]*row["Stückzahl"])
                gewinn_verlust.append(f"{profit:.2f} € ({profit/row['Kaufpreis']/row['Stückzahl']*100:.2f}%)")
                signal.append("Halten")  # hier kann man SMA/RSI/Signal Logik einbauen
            else:
                aktuelle_preise.append(None)
                gewinn_verlust.append("Keine Daten")
                signal.append("Keine Daten")
        except:
            aktuelle_preise.append(None)
            gewinn_verlust.append("Fehler")
            signal.append("Fehler")
    
    df_port["Aktueller Preis"] = aktuelle_preise
    df_port["Gewinn/Verlust"] = gewinn_verlust
    df_port["Signal"] = signal

    # Tabelle anzeigen
    st.dataframe(df_port[["Ticker","Aktueller Preis","Stückzahl","Gewinn/Verlust","Signal","Status"]], use_container_width=True)

    # Aktionen: Verkaufen
    for i, row in df_port.iterrows():
        if st.button(f"Verkaufen {row['Ticker']}", key=f"sell_{i}"):
            st.session_state.portfolio.pop(i)
            st.success(f"{row['Ticker']} verkauft!")
            st.experimental_rerun()
else:
    st.info("Keine Aktien im Portfolio.")

# ---------- KURSVERLAUF CHART ----------
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", [row["Ticker"] for row in st.session_state.portfolio] if st.session_state.portfolio else [])

if selected_ticker:
    try:
        df = yf.download(selected_ticker, period="6mo", interval="1d")
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x="Date",
            y="Close",
            tooltip=["Date", "Close", "SMA20", "SMA50"]
        ).properties(width=800, height=300)  # fixierte Größe

        st.altair_chart(chart, use_container_width=True)
    except:
        st.error(f"Für {selected_ticker} sind keine Kursdaten verfügbar.")

# ---------- RSS-NEWS ----------
st.subheader("📰 News")
rss_sources = [
    f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={selected_ticker}&region=US&lang=en",
    f"https://www.finanzen.net/rss/{selected_ticker}.rss",
]

news_found = False
for url in rss_sources:
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            news_found = True
            for entry in feed.entries[:5]:
                st.markdown(f"[{entry.title}]({entry.link})")
            break
    except:
        continue

if not news_found:
    st.info("RSS-News nicht verfügbar oder feedparser nicht installiert.")
