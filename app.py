import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

st.set_page_config(page_title="Trading Dashboard Profi", layout="wide")
st.title("📊 Profi Trading Dashboard mit Portfolio-Status")

# --- Session State initialisieren ---
if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = []

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
        df["SMA20"] = ta.trend.SMAIndicator(df["Close"], 20).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(df["Close"], 50).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
        macd = ta.trend.MACD(df["Close"])
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)
        return df
    except:
        return pd.DataFrame()

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
        score += 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        score += 1 if macd > macd_signal else (-1 if macd < macd_signal else 0)
        score += 0.5 if vol > 1.5*vol_signal else 0
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
        score += 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        score += 1 if macd > macd_signal else -1
        score += 0.5 if vol > 1.5*vol_signal else 0
    avg_score = score / max(len(last5),1)
    if avg_score >= 1:
        return "📈 Wahrscheinlich steigend"
    elif avg_score <= -1:
        return "📉 Wahrscheinlich fallend"
    else:
        return "➡️ Seitwärts"

# --- Sidebar: Aktien verwalten + Regler ---
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
            st.session_state.aktien_liste.append({
                "Ticker": t,
                "Name": n,
                "Status": new_status
            })
        else:
            st.sidebar.info("Ticker bereits in der Liste")

# --- Portfolio-Übersicht ---
st.header("📋 Portfolio-Übersicht")
to_delete = []
for i, a in enumerate(st.session_state.aktien_liste):
    cols = st.columns([0.05,0.4,0.2,0.15,0.2])
    selected = cols[0].checkbox("", key=f"chk_{i}")
    status_color = "🟢" if a["Status"]=="Besitzt" else "🟡"
    try:
        df_test = yf.Ticker(a["Ticker"]).history(period="1d")
        has_data = not df_test.empty
    except:
        has_data = False
    label_color = "red" if not has_data else "black"
    cols[1].markdown(f"<span style='color:{label_color}'>{a['Name']} ({a['Ticker']})</span>", unsafe_allow_html=True)
    cols[2].write(f"{status_color} {a['Status']}")
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
    if not df_selected.empty:
        df_selected["Advanced_Signal"] = df_selected.apply(advanced_signal, axis=1)
        df_reset = df_selected.reset_index()
        tendenz = forecast_trend(df_selected)

        st.subheader(f"📈 Kurs + Signale für {selected_ticker}")
        chart = alt.Chart(df_reset).mark_line(color="blue").encode(x="Date:T", y="Close:Q")
        chart += alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T", y="SMA20:Q")
        chart += alt.Chart(df_reset).mark_line(color="purple").encode(x="Date:T", y="SMA50:Q")
        chart += alt.Chart(df_reset).mark_circle(size=100).encode(
            x="Date:T",
            y="Close:Q",
            color=alt.Color("Advanced_Signal:N"),
            tooltip=["Date:T","Close:Q","Advanced_Signal:N"]
        )
        st.altair_chart(chart.interactive(), use_container_width=True)
        st.write("Trend:", tendenz)
    else:
        st.warning(f"Für diese Aktie sind keine aktuellen Kursdaten verfügbar oder Ticker ungültig. Prüfe YFinance: [Link](https://finance.yahoo.com/quote/{selected_ticker})")
else:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
