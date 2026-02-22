import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Profi", layout="wide")
st.title("📊 Profi Trading Dashboard - Komplettversion mit Kacheln & Prognose")

# --- Sidebar Einstellungen ---
st.sidebar.header("Anzeigeoptionen")
show_sma = st.sidebar.checkbox("SMA20/50 anzeigen", value=True)
show_rsi = st.sidebar.checkbox("RSI anzeigen", value=True)
show_macd = st.sidebar.checkbox("MACD anzeigen", value=True)
show_ampel = st.sidebar.checkbox("Ampel anzeigen", value=True)
show_news = st.sidebar.checkbox("News anzeigen", value=True)
show_markers = st.sidebar.checkbox("Signale im Chart anzeigen", value=True)

# --- Aktienliste ---
tickers = ["RHM.DE", "BMW.DE", "SAP.DE"]
ticker_names = {"RHM.DE": "Rheinmetall", "BMW.DE": "BMW", "SAP.DE": "SAP"}
selected_ticker = st.selectbox("Wähle eine Aktie", tickers, format_func=lambda x: ticker_names[x])

# --- Daten laden ---
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    df["SMA20"] = ta.trend.SMAIndicator(df["Close"], 20).sma_indicator()
    df["SMA50"] = ta.trend.SMAIndicator(df["Close"], 50).sma_indicator()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    macd = ta.trend.MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["Volumen_Signal"] = df["Volume"].rolling(20).mean()
    return df

df = load_data(selected_ticker)
df_reset = df.reset_index()

# --- Erweiterte Ampel ---
def advanced_signal(row):
    score = 0
    if row["SMA20"] > row["SMA50"]:
        score += 1
    elif row["SMA20"] < row["SMA50"]:
        score -= 1
    if row["RSI"] < 30:
        score += 1
    elif row["RSI"] > 70:
        score -= 1
    if row["MACD"] > row["MACD_signal"]:
        score += 1
    elif row["MACD"] < row["MACD_signal"]:
        score -= 1
    if row["Volume"] > 1.5 * row["Volumen_Signal"]:
        score += 0.5
    if score >= 2:
        return "Stark Kauf"
    elif score <= -2:
        return "Stark Verkauf"
    else:
        return "Halten"

df["Advanced_Signal"] = df.apply(advanced_signal, axis=1)
color_map = {"Stark Kauf": "#4CAF50", "Halten": "#FFC107", "Stark Verkauf": "#F44336"}
signal_map = {"Stark Kauf": 2, "Halten": 1, "Stark Verkauf": 0}

# --- Prognose ---
def forecast_trend(df):
    last_df = df.tail(5)
    score = 0
    for _, row in last_df.iterrows():
        if row["SMA20"] > row["SMA50"]:
            score += 1
        else:
            score -= 1
        if row["RSI"] < 30:
            score += 1
        elif row["RSI"] > 70:
            score -= 1
        if row["MACD"] > row["MACD_signal"]:
            score += 1
        else:
            score -= 1
        if row["Volume"] > 1.5 * row["Volumen_Signal"]:
            score += 0.5
    avg_score = score / len(last_df)
    if avg_score >= 1:
        return "📈 Wahrscheinlich steigend"
    elif avg_score <= -1:
        return "📉 Wahrscheinlich fallend"
    else:
        return "➡️ Seitwärts"

tendenz = forecast_trend(df)
color_map_forecast = {
    "📈 Wahrscheinlich steigend": "#4CAF50",
    "➡️ Seitwärts": "#FFC107",
    "📉 Wahrscheinlich fallend": "#F44336"
}

# --- Layout Kacheln ---
kpi1, kpi2 = st.columns([2,1])
with kpi1:
    st.subheader("📈 Kurs + SMA + Signale")
    chart = alt.Chart(df_reset).mark_line(color="blue").encode(x="Date:T", y="Close:Q")
    if show_sma:
        chart += alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T", y="SMA20:Q")
        chart += alt.Chart(df_reset).mark_line(color="purple").encode(x="Date:T", y="SMA50:Q")
    if show_markers:
        chart += alt.Chart(df_reset).mark_circle(size=100).encode(
            x="Date:T",
            y="Close:Q",
            color=alt.Color("Advanced_Signal:N", scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values()))),
            tooltip=["Date:T", "Close:Q", "Advanced_Signal:N"]
        )
    st.altair_chart(chart.interactive(), use_container_width=True)

with kpi2:
    st.subheader("📊 Indikatoren")
    indicator_chart = None
    if show_rsi:
        chart_rsi = alt.Chart(df_reset).mark_line(color="green").encode(x="Date:T", y="RSI:Q")
        indicator_chart = chart_rsi if indicator_chart is None else indicator_chart + chart_rsi
    if show_macd:
        chart_macd = alt.Chart(df_reset).mark_line(color="red").encode(x="Date:T", y="MACD:Q")
        chart_signal = alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T", y="MACD_signal:Q")
        indicator_chart = chart_macd + chart_signal if indicator_chart is None else indicator_chart + chart_macd + chart_signal
    if indicator_chart:
        st.altair_chart(indicator_chart, use_container_width=True)

# --- Untere Kacheln: Ampel, Prognose, News ---
col1, col2 = st.columns(2)

with col1:
    if show_ampel:
        st.subheader("🟢 Erweiterte Ampel")
        last_signal = df["Advanced_Signal"].iloc[-1]
        st.markdown(
            f"<div style='background-color:{color_map[last_signal]};padding:20px;text-align:center;font-size:30px;border-radius:10px;color:white;'>{last_signal}</div>",
            unsafe_allow_html=True
        )

        st.subheader("🔮 Prognose (nächste 3 Tage)")
        st.markdown(
            f"<div style='background-color:{color_map_forecast[tendenz]};padding:20px;text-align:center;font-size:25px;border-radius:10px;color:white;'>{tendenz}</div>",
            unsafe_allow_html=True
        )

with col2:
    if show_news:
        st.subheader("📰 Wichtigste News")
        ticker_obj = yf.Ticker(selected_ticker)
        news = ticker_obj.news
        if not news:
            st.write("Keine aktuellen Nachrichten verfügbar.")
        else:
            for article in news[:5]:
                with st.expander(article['title']):
                    st.markdown(f"*Quelle: {article.get('publisher','unbekannt')}*")
                    st.markdown(f"[Link zur Meldung]({article.get('link','-')})")
    if show_ampel:
        st.subheader("🟡 Historie der letzten 20 Signale")
        df_hist = df[["Date", "Advanced_Signal"]].tail(20).copy()
        df_hist["Signal_Code"] = df_hist["Advanced_Signal"].map(signal_map)
        df_hist_display = df_hist.set_index("Date")[["Signal_Code"]]
        st.dataframe(df_hist_display.style.background_gradient(cmap="RdYlGn", axis=None))
