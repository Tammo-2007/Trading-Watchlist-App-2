import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Profi", layout="wide")
st.title("📊 Profi Trading Dashboard mit Portfolio-Status")

# --- Sidebar: Aktien eintragen & Status ---
st.sidebar.header("Aktien eintragen / Status wählen")

if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = []

new_ticker = st.sidebar.text_input("Ticker (z.B. RHM.DE)")
new_name = st.sidebar.text_input("Name (z.B. Rheinmetall)")
new_status = st.sidebar.selectbox("Status", ["Beobachtung", "Besitzt"])

if st.sidebar.button("Aktie hinzufügen") and new_ticker and new_name:
    st.session_state.aktien_liste.append({
        "Ticker": new_ticker,
        "Name": new_name,
        "Status": new_status
    })

# Aktuelle Liste
st.sidebar.subheader("Aktuelle Aktien:")
for a in st.session_state.aktien_liste:
    st.sidebar.write(f"{a['Ticker']} → {a['Name']} ({a['Status']})")

# Wenn Liste leer, Standardaktien
if len(st.session_state.aktien_liste) == 0:
    tickers = ["RHM.DE","BMW.DE","SAP.DE"]
    ticker_names = {"RHM.DE":"Rheinmetall","BMW.DE":"BMW","SAP.DE":"SAP"}
    ticker_status = {t:"Beobachtung" for t in tickers}
else:
    tickers = [a["Ticker"] for a in st.session_state.aktien_liste]
    ticker_names = {a["Ticker"]:a["Name"] for a in st.session_state.aktien_liste}
    ticker_status = {a["Ticker"]:a["Status"] for a in st.session_state.aktien_liste}

selected_ticker = st.selectbox("Wähle eine Aktie", tickers, format_func=lambda x: ticker_names[x])

# --- Sidebar Anzeigeoptionen ---
st.sidebar.header("Anzeigeoptionen")
show_sma = st.sidebar.checkbox("SMA20/50 anzeigen", value=True)
show_rsi = st.sidebar.checkbox("RSI anzeigen", value=True)
show_macd = st.sidebar.checkbox("MACD anzeigen", value=True)
show_ampel = st.sidebar.checkbox("Ampel anzeigen", value=True)
show_news = st.sidebar.checkbox("News anzeigen", value=True)
show_markers = st.sidebar.checkbox("Signale im Chart anzeigen", value=True)

# --- Daten laden ---
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    if "Close" not in df.columns:
        st.error(f"Fehler: 'Close'-Daten für {ticker} nicht gefunden.")
        return pd.DataFrame()

    close_series = df["Close"].copy().dropna()
    try:
        df["SMA20"] = ta.trend.SMAIndicator(close_series, 20).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(close_series, 50).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(close_series, 14).rsi()
        macd = ta.trend.MACD(close_series)
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
    except:
        df["SMA20"]=df["SMA50"]=df["RSI"]=df["MACD"]=df["MACD_signal"]=0
    if "Volume" in df.columns:
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean()
    else:
        df["Volume"]=df["Volumen_Signal"]=0

    # Alle numerischen Spalten float
    for col in ["SMA20","SMA50","RSI","MACD","MACD_signal","Volume","Volumen_Signal"]:
        if col in df.columns and isinstance(df[col], pd.Series):
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col]=0

    return df

df = load_data(selected_ticker)
df_reset = df.reset_index()

# --- Erweiterte Ampel ---
def advanced_signal(row):
    try:
        sma20 = float(row.get("SMA20",0))
        sma50 = float(row.get("SMA50",0))
        rsi = float(row.get("RSI",50))
        macd = float(row.get("MACD",0))
        macd_signal = float(row.get("MACD_signal",0))
        volume = float(row.get("Volume",0))
        vol_signal = float(row.get("Volumen_Signal",0))

        score = 0
        score += 1 if sma20 > sma50 else (-1 if sma20 < sma50 else 0)
        score += 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        score += 1 if macd > macd_signal else (-1 if macd < macd_signal else 0)
        score += 0.5 if volume > 1.5*vol_signal else 0

        if score>=2: return "Stark Kauf"
        elif score<=-2: return "Stark Verkauf"
        else: return "Halten"
    except:
        return "Halten"

df["Advanced_Signal"]=df.apply(advanced_signal, axis=1)
color_map={"Stark Kauf":"#4CAF50","Halten":"#FFC107","Stark Verkauf":"#F44336"}
signal_map={"Stark Kauf":2,"Halten":1,"Stark Verkauf":0}

# --- Prognose ---
def forecast_trend(df):
    last_df = df.tail(5)
    score=0
    for _,row in last_df.iterrows():
        sma20=float(row.get("SMA20",0))
        sma50=float(row.get("SMA50",0))
        rsi=float(row.get("RSI",50))
        macd=float(row.get("MACD",0))
        macd_signal=float(row.get("MACD_signal",0))
        volume=float(row.get("Volume",0))
        vol_signal=float(row.get("Volumen_Signal",0))

        score += 1 if sma20>sma50 else -1
        score += 1 if rsi<30 else (-1 if rsi>70 else 0)
        score += 1 if macd>macd_signal else -1
        score += 0.5 if volume>1.5*vol_signal else 0
    avg_score = score/max(len(last_df),1)
    if avg_score>=1: return "📈 Wahrscheinlich steigend"
    elif avg_score<=-1: return "📉 Wahrscheinlich fallend"
    else: return "➡️ Seitwärts"

tendenz = forecast_trend(df)
color_map_forecast={"📈 Wahrscheinlich steigend":"#4CAF50","➡️ Seitwärts":"#FFC107","📉 Wahrscheinlich fallend":"#F44336"}

# --- Charts ---
kpi1,kpi2=st.columns([2,1])
with kpi1:
    st.subheader("📈 Kurs + SMA + Signale")
    chart = alt.Chart(df_reset).mark_line(color="blue").encode(x="Date:T",y="Close:Q")
    if show_sma:
        chart += alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T",y="SMA20:Q")
        chart += alt.Chart(df_reset).mark_line(color="purple").encode(x="Date:T",y="SMA50:Q")
    if show_markers:
        chart += alt.Chart(df_reset).mark_circle(size=100).encode(
            x="Date:T",
            y="Close:Q",
            color=alt.Color("Advanced_Signal:N",scale=alt.Scale(domain=list(color_map.keys()),range=list(color_map.values()))),
            tooltip=["Date:T","Close:Q","Advanced_Signal:N"]
        )
    st.altair_chart(chart.interactive(),use_container_width=True)

with kpi2:
    st.subheader("📊 Indikatoren")
    indicator_chart=None
    if show_rsi:
        chart_rsi = alt.Chart(df_reset).mark_line(color="green").encode(x="Date:T",y="RSI:Q")
        indicator_chart = chart_rsi if indicator_chart is None else indicator_chart+chart_rsi
    if show_macd:
        chart_macd = alt.Chart(df_reset).mark_line(color="red").encode(x="Date:T",y="MACD:Q")
        chart_signal = alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T",y="MACD_signal:Q")
        indicator_chart = chart_macd+chart_signal if indicator_chart is None else indicator_chart+chart_macd+chart_signal
    if indicator_chart:
        st.altair_chart(indicator_chart,use_container_width=True)

# --- Untere Kacheln ---
col1,col2=st.columns(2)
with col1:
    if show_ampel:
        st.subheader("🟢 Erweiterte Ampel")
        last_signal = df["Advanced_Signal"].iloc[-1] if "Advanced_Signal" in df.columns else "Keine Daten"
        st.markdown(f"<div style='background-color:{color_map.get(last_signal,'#CCCCCC')};padding:20px;text-align:center;font-size:30px;border-radius:10px;color:white;'>{last_signal}</div>",unsafe_allow_html=True)

        st.subheader("🔮 Prognose (nächste 3 Tage)")
        st.markdown(f"<div style='background-color:{color_map_forecast.get(tendenz,'#CCCCCC')};padding:20px;text-align:center;font-size:25px;border-radius:10px;color:white;'>{tendenz}</div>",unsafe_allow_html=True)

with col2:
    if show_news:
        st.subheader("📰 Wichtigste News")
        ticker_obj=yf.Ticker(selected_ticker)
        news=getattr(ticker_obj,"news",[])
        if not news:
            st.write("Keine aktuellen Nachrichten verfügbar.")
        else:
            for article in news[:5]:
                title=article.get('title','Kein Titel verfügbar')
                publisher=article.get('publisher','unbekannt')
                link=article.get('link','#')
                with st.expander(title):
                    st.markdown(f"*Quelle: {publisher}*")
                    st.markdown(f"[Link zur Meldung]({link})")

    if show_ampel:
        st.subheader("🟡 Historie der letzten 20 Signale")
        if "Advanced_Signal" in df_reset.columns:
            df_hist=df_reset[["Date","Advanced_Signal"]].tail(20).copy()
            df_hist["Signal_Code"]=df_hist["Advanced_Signal"].map(signal_map)
            df_hist_display=df_hist.set_index("Date")[["Signal_Code"]]
            st.dataframe(df_hist_display.style.background_gradient(cmap="RdYlGn",axis=None))
        else:
            st.write("Keine Signaldaten verfügbar.")
