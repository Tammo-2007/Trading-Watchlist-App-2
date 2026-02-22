import streamlit as st
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator
from textblob import TextBlob
import requests

st.set_page_config(page_title="Trading Watchlist", layout="wide")

# -----------------------------
# Einstellungen
# -----------------------------
st.title("📈 Trading Watchlist App")

# Ticker-Liste mit Anzeige-Namen
tickers = {
    "RHM.DE": "Rheinmetall",
    "HEI.DE": "Heidelberg Materials",
    "SAP.DE": "SAP",
    # Hier weitere Ticker ergänzen
}

# Auswahl
selected_tickers = st.multiselect(
    "Wähle Aktien aus deiner Watchlist:",
    options=list(tickers.keys()),
    default=list(tickers.keys())
)

# Umschalter für Indikatoren
show_sma = st.checkbox("SMA20 anzeigen", value=True)
show_ema = st.checkbox("EMA50 anzeigen", value=True)

# -----------------------------
# Funktion: Indikatoren berechnen
# -----------------------------
def calculate_indicators(df):
    if "Close" not in df.columns:
        raise ValueError("DataFrame muss eine 'Close'-Spalte enthalten.")

    close_series = df["Close"]
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
    close_series = close_series.squeeze()
    if close_series.empty:
        raise ValueError("Close-Daten sind leer.")

    if show_sma:
        df["SMA20"] = SMAIndicator(close_series, window=20).sma_indicator()
    if show_ema:
        df["EMA50"] = EMAIndicator(close_series, window=50).ema_indicator()
    return df

# -----------------------------
# Daten laden
# -----------------------------
@st.cache_data
def get_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    df = calculate_indicators(df)
    return df

data_dict = {}
for ticker in selected_tickers:
    data_dict[ticker] = get_data(ticker)

# -----------------------------
# Anzeige
# -----------------------------
for ticker in selected_tickers:
    st.subheader(f"{tickers[ticker]} ({ticker})")
    df = data_dict[ticker]
    st.dataframe(df)

# -----------------------------
# News-Fenster
# -----------------------------
st.subheader("📰 Wichtige Nachrichten")
def get_news(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/news?p={ticker}"
    r = requests.get(url)
    df_news = pd.DataFrame(columns=["Titel", "Beschreibung"])
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        articles = soup.find_all("li")
        for a in articles[:5]:
            title = a.get_text()
            # Kurze Zusammenfassung
            summary = TextBlob(title).sentences[0]
            df_news = pd.concat([df_news, pd.DataFrame([{"Titel": title, "Beschreibung": summary}])])
    except Exception as e:
        df_news = pd.DataFrame([{"Titel": "Fehler beim Laden der News", "Beschreibung": str(e)}])
    return df_news

for ticker in selected_tickers:
    st.markdown(f"**{tickers[ticker]}**")
    news_df = get_news(ticker)
    st.table(news_df)

st.markdown("---")
st.markdown("💡 Hinweis: Indikatoren dienen nur zur Unterstützung und ersetzen keine Anlageberatung.")
