import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import altair as alt

st.set_page_config(page_title="Trading Dashboard Profi", layout="wide")
st.title("📊 Profi Trading Dashboard mit Portfolio-Status")

# --- Session-State initialisieren ---
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
def load_data(ticker):
    df = pd.DataFrame()
    intervals = ["1d","1wk","1mo"]
    periods = ["6mo","1y","max"]
    for interval in intervals:
        for period in periods:
            try:
                df = yf.download(ticker, period=period, interval=interval, progress=False)
                if not df.empty and "Close" in df:
                    close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
                    df["SMA20"] = ta.trend.SMAIndicator(close_series, 20).sma_indicator()
                    df["SMA50"] = ta.trend.SMAIndicator(close_series, 50).sma_indicator()
                    df["RSI"] = ta.momentum.RSIIndicator(close_series, 14).rsi()
                    macd = ta.trend.MACD(close_series)
                    df["MACD"] = macd.macd()
                    df["MACD_signal"] = macd.macd_signal()
                    df["Volume"] = pd.to_numeric(df.get("Volume", 0), errors='coerce').fillna(0)
                    df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)
                    return df
            except:
                continue
    return pd.DataFrame()

def advanced_signal(row):
    try:
        sma20 = float(row.get("SMA20", 0))
        sma50 = float(row.get("SMA50", 0))
        rsi = float(row.get("RSI", 50))
        macd = float(row.get("MACD", 0))
        macd_signal = float(row.get("MACD_signal", 0))
        vol = float(row.get("Volume", 0))
        vol_signal = float(row.get("Volumen_Signal", 0))
        score = 0
        score += 1 if sma20 > sma50 else (-1 if sma20 < sma50 else 0)
        score += 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        score += 1 if macd > macd_signal else (-1 if macd < macd_signal else 0)
        score += 0.5 if vol > 1.5*vol_signal else 0
        return "Stark Kauf" if score >= 2 else ("Stark Verkauf" if score <= -2 else "Halten")
    except:
        return "Halten"

def forecast_trend(df):
    if df.empty:
        return "Daten fehlen"
    last_df = df.tail(5)
    score = 0
    for _, row in last_df.iterrows():
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
    avg_score = score / max(len(last_df),1)
    return "📈 Wahrscheinlich steigend" if avg_score >= 1 else ("📉 Wahrscheinlich fallend" if avg_score <= -1 else "➡️ Seitwärts")

# --- Sidebar: Aktien verwalten ---
st.sidebar.header("Aktien verwalten")
new_ticker = st.sidebar.text_input("Ticker (z.B. RHM oder CSG.AS)")
new_name = st.sidebar.text_input("Name (optional)")
new_status = st.sidebar.selectbox("Status", ["Beobachtung","Besitzt"])

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
    cols[1].write(f"{a['Name']} ({a['Ticker']})")
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

    df_selected = load_data(selected_ticker)
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
        st.warning(f"Für diese Aktie sind noch keine Kursdaten verfügbar oder Ticker ungültig. Prüfe YFinance: [Link](https://finance.yahoo.com/quote/{selected_ticker})")
else:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
