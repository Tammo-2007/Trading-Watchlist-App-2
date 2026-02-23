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
def ticker_valid(ticker):
    if not ticker:
        return False
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        return not df.empty
    except:
        return False

def get_company_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get("shortName", ticker)
    except:
        return ticker

@st.cache_data
def load_data(ticker):
    try:
        # --- Versuch 1: letzte 6 Monate ---
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if "Close" in df and not df["Close"].dropna().empty:
            close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
        else:
            # --- Versuch 2: 1 Jahr ---
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if "Close" in df and not df["Close"].dropna().empty:
                close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
            else:
                # --- Versuch 3: maximal verfügbar ---
                df = yf.download(ticker, period="max", interval="1d", progress=False)
                if "Close" in df and not df["Close"].dropna().empty:
                    close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
                else:
                    return pd.DataFrame()  # wirklich keine Daten

        # --- Technische Indikatoren ---
        df["SMA20"] = ta.trend.SMAIndicator(close_series, 20).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(close_series, 50).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(close_series, 14).rsi()
        macd = ta.trend.MACD(close_series)
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["Volume"] = pd.to_numeric(df.get("Volume", 0), errors='coerce').fillna(0)
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)

        # Sicherstellen, dass alle numerischen Spalten korrekt sind
        for col in ["SMA20","SMA50","RSI","MACD","MACD_signal","Volume","Volumen_Signal"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except Exception as e:
        return pd.DataFrame()

# --- Signale & Trend ---
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
        score += 0.5 if vol > 1.5 * vol_signal else 0
        return "Stark Kauf" if score >= 2 else ("Stark Verkauf" if score <= -2 else "Halten")
    except:
        return "Halten"

def forecast_trend(df):
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
        score += 0.5 if vol > 1.5 * vol_signal else 0
    avg_score = score / max(len(last_df), 1)
    return "📈 Wahrscheinlich steigend" if avg_score >= 1 else ("📉 Wahrscheinlich fallend" if avg_score <= -1 else "➡️ Seitwärts")

# --- Sidebar: Aktien verwalten ---
st.sidebar.header("Aktien verwalten")
new_ticker = st.sidebar.text_input("Ticker (z.B. RHM.DE)")
new_name = st.sidebar.text_input("Name (optional)")
new_status = st.sidebar.selectbox("Status", ["Beobachtung", "Besitzt"])

if st.sidebar.button("Aktie hinzufügen"):
    if not new_ticker and not new_name:
        st.sidebar.warning("Bitte mindestens Ticker oder Name eingeben")
    else:
        name_to_use = new_name if new_name else get_company_name(new_ticker)
        st.session_state.aktien_liste.append({
            "Ticker": new_ticker.upper() if new_ticker else "",
            "Name": name_to_use,
            "Status": new_status
        })

# --- Portfolio-Übersicht ---
st.header("📋 Portfolio-Übersicht")
portfolio_data = []

for a in st.session_state.aktien_liste:
    ticker, name, status = a["Ticker"], a["Name"], a["Status"]
    trend = "Daten fehlen"
    last_signal = "–"
    df = load_data(ticker) if ticker else pd.DataFrame()
    if not df.empty:
        df["Advanced_Signal"] = df.apply(advanced_signal, axis=1)
        trend = forecast_trend(df)
        last_signal = df["Advanced_Signal"].iloc[-1]
    portfolio_data.append({
        "Ticker": ticker if ticker else name,
        "Name": name,
        "Status": status,
        "Signal": last_signal,
        "Trend": trend
    })

st.dataframe(pd.DataFrame(portfolio_data))

# --- Interaktive Analyse ---
st.header("📊 Interaktive Aktien-Analyse")
if st.session_state.aktien_liste:
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
        tendenz = forecast_trend(df_selected)
        df_reset = df_selected.reset_index()

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
    else:
        st.info("Für diese Aktie sind noch keine Kursdaten verfügbar oder Ticker ungültig.")
else:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
