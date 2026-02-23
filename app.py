import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

# Feedparser optional einbinden
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ModuleNotFoundError:
    FEEDPARSER_AVAILABLE = False

st.set_page_config(page_title="Trading Dashboard Profi", layout="wide")
st.title("📊 Profi Trading Dashboard mit Portfolio-Status")

# --- Session State ---
if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = []

# --- Sidebar: Schieberegler & Einstellungen ---
st.sidebar.header("Einstellungen")
sma20_period = st.sidebar.slider("SMA20 Periode", 5, 50, 20)
sma50_period = st.sidebar.slider("SMA50 Periode", 10, 200, 50)
vol_factor = st.sidebar.slider("Volumen Faktor für Signal", 0.5, 3.0, 1.5)
trend_weight_rsi = st.sidebar.slider("RSI Gewicht im Trend", 0, 2, 1)
trend_weight_macd = st.sidebar.slider("MACD Gewicht im Trend", 0, 2, 1)

# --- Hilfsfunktionen ---
def normalize_ticker(ticker):
    ticker = ticker.strip().upper()
    if ticker and "." not in ticker:
        ticker += ".DE"
    return ticker

def get_company_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get("shortName", ticker)
    except:
        return ticker

@st.cache_data
def load_data(ticker, interval="1d", period="6mo"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty or "Close" not in df:
            return pd.DataFrame()
        df["SMA20"] = ta.trend.SMAIndicator(df["Close"], sma20_period).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(df["Close"], sma50_period).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
        macd = ta.trend.MACD(df["Close"])
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def load_today_price(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="1m")
        if df.empty:
            return None
        return df["Close"].iloc[-1]
    except:
        return None

# --- News Quellen ---
RSS_FEEDS = {
    "Finanzfluss": "https://www.finanzfluss.de/feed/",
    "Finanztipps": "https://www.finanztipps.de/rss/news.xml",
    "Focus Money": "https://www.focus.de/finanzen/rss/finanzen-rss.xml"
}

def get_rss_news(feed_url, ticker):
    if not FEEDPARSER_AVAILABLE:
        return []
    try:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries:
            if ticker.split('.')[0].upper() in entry.get("title","").upper() or \
               ticker.split('.')[0].upper() in entry.get("summary","").upper():
                items.append({"title": entry.get("title",""), "link": entry.get("link","")})
        return items
    except:
        return []

def get_google_news(ticker):
    if not FEEDPARSER_AVAILABLE:
        return []
    try:
        search_query = f"{ticker} OR {get_company_name(ticker)}"
        url = f"https://news.google.com/rss/search?q={search_query}"
        feed = feedparser.parse(url)
        items = [{"title": e.get("title",""), "link": e.get("link","")} for e in feed.entries]
        return items
    except:
        return []

# --- Advanced Signal & Trend (unverändert) ---
def advanced_signal(row):
    try:
        score = 0
        sma20 = float(row.get("SMA20", 0))
        sma50 = float(row.get("SMA50", 0))
        rsi = float(row.get("RSI", 50))
        macd = float(row.get("MACD", 0))
        macd_signal = float(row.get("MACD_signal", 0))
        vol = float(row.get("Volume", 0))
        vol_signal = float(row.get("Volumen_Signal", 0))
        score += 1 if sma20 > sma50 else (-1 if sma20 < sma50 else 0)
        score += trend_weight_rsi * (1 if rsi < 30 else (-1 if rsi > 70 else 0))
        score += trend_weight_macd * (1 if macd > macd_signal else (-1 if macd < macd_signal else 0))
        score += 0.5 if vol > vol_factor*vol_signal else 0
        if score >= 2:
            return "Stark Kauf"
        elif score <= -2:
            return "Stark Verkauf"
        else:
            return "Halten"
    except:
        return "Halten"

def forecast_trend(df):
    if df.empty:
        return "Daten fehlen"
    last5 = df.tail(5)
    score = 0
    for _, row in last5.iterrows():
        sma20 = float(row.get("SMA20", 0))
        sma50 = float(row.get("SMA50", 0))
        rsi = float(row.get("RSI", 50))
        macd = float(row.get("MACD", 0))
        macd_signal = float(row.get("MACD_signal", 0))
        vol = float(row.get("Volume", 0))
        vol_signal = float(row.get("Volumen_Signal", 0))
        score += 1 if sma20 > sma50 else -1
        score += trend_weight_rsi * (1 if rsi < 30 else (-1 if rsi > 70 else 0))
        score += trend_weight_macd * (1 if macd > macd_signal else -1)
        score += 0.5 if vol > vol_factor*vol_signal else 0
    avg_score = score / max(len(last5),1)
    if avg_score >= 1:
        return "📈 Wahrscheinlich steigend"
    elif avg_score <= -1:
        return "📉 Wahrscheinlich fallend"
    else:
        return "➡️ Seitwärts"

# --- Aktienverwaltung & Portfolio (unverändert) ---
st.sidebar.header("Aktien verwalten")
new_ticker = st.sidebar.text_input("Ticker (z.B. RHM oder CSG.AS)")
new_name = st.sidebar.text_input("Name (optional)")
new_status = st.sidebar.selectbox("Status", ["Beobachtung","Besitzt"])
interval = st.sidebar.selectbox("Chart Intervall", ["1d","1wk","1mo"])
period = st.sidebar.selectbox("Historischer Zeitraum", ["1mo","6mo","1y","5y","max"])

if st.sidebar.button("Aktie hinzufügen"):
    if not new_ticker and not new_name:
        st.sidebar.warning("Bitte mindestens Ticker oder Name eingeben")
    else:
        t = normalize_ticker(new_ticker) if new_ticker else ""
        n = new_name if new_name else (get_company_name(t) if t else "Unbekannt")
        exists = any(a["Ticker"]==t for a in st.session_state.aktien_liste)
        if not exists:
            st.session_state.aktien_liste.append({"Ticker": t, "Name": n, "Status": new_status})
        else:
            st.sidebar.info("Ticker bereits in der Liste")

# --- Portfolio Übersicht ---
st.header("📋 Portfolio-Übersicht")
to_delete = []
for i, a in enumerate(st.session_state.aktien_liste):
    cols = st.columns([0.05,0.4,0.2,0.15,0.2])
    selected = cols[0].checkbox("", key=f"chk_{i}")
    status_color = "🟢" if a["Status"]=="Besitzt" else "🟡"
    price = load_today_price(a["Ticker"])
    has_data = price is not None
    label_color = "red" if not has_data else "black"
    cols[1].markdown(f"<span style='color:{label_color}'>{a['Name']} ({a['Ticker']})</span>", unsafe_allow_html=True)
    cols[2].write(f"{status_color} {a['Status']}")
    if has_data:
        cols[3].write(f"Aktueller Kurs: {price:.2f} €")
    else:
        cols[3].write("Keine aktuellen Daten")
    delete = cols[4].button("Löschen", key=f"del_{i}")
    if delete:
        to_delete.append(i)

if to_delete:
    for i in reversed(to_delete):
        st.session_state.aktien_liste.pop(i)
    st.experimental_rerun()

# --- Interaktive Analyse ---
if st.session_state.aktien_liste:
    st.header("📊 Interaktive Aktien-Analyse")
    ticker_options = [a["Ticker"] if a["Ticker"] else a["Name"] for a in st.session_state.aktien_liste]
    display_labels = [f"{a['Name']} ({a['Ticker']}) [{a['Status']}]" for a in st.session_state.aktien_liste]

    selected_ticker = st.selectbox(
        "Wähle eine Aktie aus deinem Portfolio",
        options=ticker_options,
        format_func=lambda x: display_labels[ticker_options.index(x)]
    )

    df_selected = load_data(selected_ticker, interval=interval, period=period)
    current_price = load_today_price(selected_ticker)
    if current_price:
        st.subheader(f"💰 Aktueller Kurs: {current_price:.2f} €")

    if not df_selected.empty:
        df_selected["Advanced_Signal"] = df_selected.apply(advanced_signal, axis=1)
        df_reset = df_selected.reset_index()
        tendenz = forecast_trend(df_selected)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Historische Charts", "📉 Intraday-Kurs", "📰 News YFinance", "📰 News Extern", "📊 Advanced Signal & Trend"])

        # Tab 4: Externe News (fehlertolerant)
        with tab4:
            st.subheader("Externe News")
            if not FEEDPARSER_AVAILABLE:
                st.warning("RSS-News sind nicht verfügbar. Installiere `feedparser`, um externe News zu sehen.")
            else:
                all_external_news = {}
                for name, url in RSS_FEEDS.items():
                    all_external_news[name] = get_rss_news(url, selected_ticker)
                all_external_news["Google News"] = get_google_news(selected_ticker)
                for source, articles in all_external_news.items():
                    with st.expander(source):
                        if articles:
                            for a in articles[:5]:
                                st.write(f"- [{a['title']}]({a['link']})")
                        else:
                            st.write("Keine News verfügbar")
    else:
        st.warning(f"Für diese Aktie sind keine historischen Kursdaten verfügbar. Prüfe YFinance: [Link](https://finance.yahoo.com/quote/{selected_ticker})")
else:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
