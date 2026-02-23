import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

# RSS News
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ModuleNotFoundError:
    FEEDPARSER_AVAILABLE = False

st.set_page_config(page_title="Trading Dashboard Kompakt", layout="wide")
st.title("📊 Kompaktes Trading Dashboard – Alles auf einen Blick")

# --- Session State ---
if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = []

# --- Einstellungen für Signale ---
st.subheader("🔧 Einstellungen für Signale")
col1, col2, col3 = st.columns(3)
sma20_period = col1.slider("SMA20 Periode", 5,50,20, help="Kurzfristiger gleitender Durchschnitt")
sma50_period = col2.slider("SMA50 Periode", 10,200,50, help="Mittelfristiger gleitender Durchschnitt")
vol_factor = col3.slider("Volumen Faktor",0.5,3.0,1.5, help="Multiplikator für Volumen-Signale")

col4, col5 = st.columns(2)
trend_weight_rsi = col4.slider("RSI Gewicht",0,2,1, help="Gewichtung des RSI im Trend")
trend_weight_macd = col5.slider("MACD Gewicht",0,2,1, help="Gewichtung des MACD im Trend")

# --- Portfolio Verwaltung ---
st.subheader("💼 Portfolio verwalten")
col_t, col_n, col_s, col_b = st.columns([2,3,2,1])
new_input = col_t.text_input("Ticker oder Name", help="z.B. RHM oder Rheinmetall")
new_name = col_n.text_input("Name (optional)")
new_status = col_s.selectbox("Status", ["Beobachtung","Besitzt"])
if col_b.button("Hinzufügen"):
    inp = new_input.strip()
    if "." not in inp and len(inp)<5:  # kurzer Ticker, .DE ergänzen
        ticker = inp.upper() + ".DE"
    else:
        ticker = inp.upper()
    name = new_name.strip() if new_name else ticker
    if ticker and not any(a["Ticker"]==ticker for a in st.session_state.aktien_liste):
        st.session_state.aktien_liste.append({"Ticker": ticker, "Name": name, "Status": new_status})

# --- Portfolio Übersicht ---
st.subheader("📋 Portfolio")
to_delete = []
for i,a in enumerate(st.session_state.aktien_liste):
    cols = st.columns([0.05,0.5,0.2,0.15])
    selected = cols[0].checkbox("", key=f"chk_{i}", help="Markiere zum Auswählen der Aktie")
    cols[1].write(f"{a['Name']} ({a['Ticker']})")
    cols[2].write(f"{'🟢' if a['Status']=='Besitzt' else '🟡'} {a['Status']}")
    if cols[3].button("Löschen", key=f"del_{i}", help="Klicke zum Löschen dieser Aktie"):
        to_delete.append(i)

if to_delete:
    for i in reversed(to_delete):
        st.session_state.aktien_liste.pop(i)

# --- Aktie auswählen ---
if st.session_state.aktien_liste:
    ticker_options = [a["Ticker"] for a in st.session_state.aktien_liste]
    selected_ticker = st.selectbox("Wähle eine Aktie", ticker_options, help="Hier die Aktie auswählen für Analyse")

    # Kursdaten abrufen
    df = yf.Ticker(selected_ticker).history(period="6mo")
    if not df.empty:
        df["SMA20"] = ta.trend.SMAIndicator(df["Close"], sma20_period).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(df["Close"], sma50_period).sma_indicator()

        st.subheader("💰 Aktueller Kurs & Trend")
        current_price = df["Close"].iloc[-1]
        st.metric(label=f"{selected_ticker} Preis", value=f"{current_price:.2f} €")

        # Advanced Signal
        df_clean = df.dropna(subset=["SMA20","SMA50"])
        if not df_clean.empty:
            last = df_clean.tail(1).iloc[0]
            score = 0
            score += 1 if last["SMA20"]>last["SMA50"] else -1
            rsi = ta.momentum.RSIIndicator(df["Close"],14).rsi().dropna().iloc[-1]
            macd = ta.trend.MACD(df["Close"]).macd().dropna().iloc[-1]
            macd_signal = ta.trend.MACD(df["Close"]).macd_signal().dropna().iloc[-1]
            score += trend_weight_rsi*(1 if rsi<30 else (-1 if rsi>70 else 0))
            score += trend_weight_macd*(1 if macd>macd_signal else -1)
            signal = "Stark Kauf" if score>=2 else ("Stark Verkauf" if score<=-2 else "Halten")
            st.write(f"**Advanced Signal:** {signal}")
        else:
            st.warning("Nicht genügend Daten für Advanced Signal")

        # Historischer Chart mit Tooltips
        df_reset = df.reset_index()
        df_plot = df_reset[["Date","Close","SMA20","SMA50"]].dropna()
        if not df_plot.empty and len(df_plot)>1:
            chart = alt.Chart(df_plot).transform_fold(
                ["Close","SMA20","SMA50"], as_=["Serie","Wert"]
            ).mark_line().encode(
                x=alt.X("Date:T", title="Datum"),
                y=alt.Y("Wert:Q", title="Preis"),
                color="Serie:N",
                tooltip=["Date:T","Serie:N","Wert:Q"]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Nicht genügend Daten für Chartanzeige")

        # News
        if FEEDPARSER_AVAILABLE:
            st.subheader("📰 News")
            RSS_FEEDS = {
                "Finanzfluss": "https://www.finanzfluss.de/feed/",
                "Finanztipps": "https://www.finanztipps.de/rss/news.xml",
                "Focus Money": "https://www.focus.de/finanzen/rss/finanzen-rss.xml"
            }
            for name,url in RSS_FEEDS.items():
                feed = feedparser.parse(url)
                with st.expander(name):
                    count=0
                    for e in feed.entries:
                        if selected_ticker.split('.')[0].upper() in e.get("title","").upper():
                            st.write(f"- [{e.get('title')}]({e.get('link')})")
                            count+=1
                            if count>=5: break
        else:
            st.warning("RSS-News nicht verfügbar (installiere feedparser)")
    else:
        st.warning("Keine Kursdaten verfügbar")
else:
    st.info("Bitte trage Aktien ein, um Analysen zu sehen.")
