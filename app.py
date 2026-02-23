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

# --- Sidebar: Aktien eintragen / bearbeiten ---
st.sidebar.header("Aktien verwalten")
new_ticker = st.sidebar.text_input("Ticker (z.B. RHM.DE)")
new_name = st.sidebar.text_input("Name (optional)")
new_status = st.sidebar.selectbox("Status", ["Beobachtung", "Besitzt"])

if st.sidebar.button("Aktie hinzufügen"):
    if not new_ticker and not new_name:
        st.sidebar.warning("Bitte mindestens Ticker oder Name eingeben")
    else:
        st.session_state.aktien_liste.append({
            "Ticker": new_ticker.upper() if new_ticker else "",
            "Name": new_name if new_name else new_ticker.upper(),
            "Status": new_status
        })

# --- Sidebar: Aktienliste mit Lösch-Button ---
st.sidebar.subheader("Aktuelle Aktien:")
indices_to_delete = []
for i, a in enumerate(st.session_state.aktien_liste):
    cols = st.sidebar.columns([4,1])
    cols[0].write(f"{a['Ticker']} → {a['Name']} ({a['Status']})")
    if cols[1].button("🗑️", key=f"del_{i}"):
        indices_to_delete.append(i)

# Löschung außerhalb der Schleife durchführen
if indices_to_delete:
    for i in sorted(indices_to_delete, reverse=True):
        st.session_state.aktien_liste.pop(i)
    st.experimental_rerun()

# Anzeigeoptionen Sidebar
st.sidebar.header("Anzeigeoptionen")
show_sma = st.sidebar.checkbox("SMA20/50 anzeigen", value=True)
show_rsi = st.sidebar.checkbox("RSI anzeigen", value=True)
show_macd = st.sidebar.checkbox("MACD anzeigen", value=True)
show_ampel = st.sidebar.checkbox("Ampel anzeigen", value=True)
show_markers = st.sidebar.checkbox("Signale im Chart anzeigen", value=True)

# --- Funktion: Daten laden ---
@st.cache_data
def load_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d")
        if "Close" not in df.columns or df.empty:
            return pd.DataFrame()
        close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
        df["SMA20"] = ta.trend.SMAIndicator(close_series, 20).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(close_series, 50).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(close_series, 14).rsi()
        macd = ta.trend.MACD(close_series)
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["Volume"] = pd.to_numeric(df.get("Volume", 0), errors='coerce').fillna(0)
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)
        for col in ["SMA20","SMA50","RSI","MACD","MACD_signal","Volume","Volumen_Signal"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        return df
    except:
        return pd.DataFrame()

# --- Erweiterte Ampel ---
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

# --- Portfolio-Übersicht ---
st.header("📋 Portfolio-Übersicht")
portfolio_data = []
for a in st.session_state.aktien_liste:
    ticker, name, status = a["Ticker"], a["Name"], a["Status"]
    if not ticker: continue
    df = load_data(ticker)
    if df.empty: continue
    df["Advanced_Signal"] = df.apply(advanced_signal, axis=1)
    trend = forecast_trend(df)
    last_signal = df["Advanced_Signal"].iloc[-1]
    portfolio_data.append({"Ticker": ticker, "Name": name, "Status": status, "Signal": last_signal, "Trend": trend})

portfolio_df = pd.DataFrame(portfolio_data)
status_color = {"Besitzt": "#4CAF50", "Beobachtung": "#2196F3"}
signal_color = {"Stark Kauf": "#4CAF50", "Halten": "#FFC107", "Stark Verkauf": "#F44336"}
forecast_color = {"📈 Wahrscheinlich steigend": "#4CAF50", "➡️ Seitwärts": "#FFC107", "📉 Wahrscheinlich fallend": "#F44336"}

def color_row(row):
    return [f'background-color: {status_color.get(row["Status"],"#FFFFFF")}' if col=="Status" else
            f'background-color: {signal_color.get(row["Signal"],"#FFFFFF")}' if col=="Signal" else
            f'background-color: {forecast_color.get(row["Trend"],"#FFFFFF")}' if col=="Trend" else ""
            for col in portfolio_df.columns]

st.dataframe(portfolio_df.style.apply(color_row, axis=1))

# --- Interaktive Aktien-Analyse ---
st.header("📊 Interaktive Aktien-Analyse")
if not st.session_state.aktien_liste:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
else:
    # --- Stabile Portfolio-Auswahl ---
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

        # --- Charts ---
        st.subheader(f"📈 Kurs + Signale für {selected_ticker}")
        chart = alt.Chart(df_reset).mark_line(color="blue").encode(x="Date:T", y="Close:Q")
        if show_sma:
            chart += alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T", y="SMA20:Q")
            chart += alt.Chart(df_reset).mark_line(color="purple").encode(x="Date:T", y="SMA50:Q")
        if show_markers:
            chart += alt.Chart(df_reset).mark_circle(size=100).encode(
                x="Date:T",
                y="Close:Q",
                color=alt.Color("Advanced_Signal:N", scale=alt.Scale(domain=list(signal_color.keys()), range=list(signal_color.values()))),
                tooltip=["Date:T", "Close:Q", "Advanced_Signal:N"]
            )
        st.altair_chart(chart.interactive(), use_container_width=True)

        # --- Indikatoren ---
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

        # --- Ampel & Prognose ---
        st.subheader("🟢 Erweiterte Ampel")
        last_signal = df_selected["Advanced_Signal"].iloc[-1]
        st.markdown(f"<div style='background-color:{signal_color.get(last_signal,'#CCCCCC')};padding:20px;text-align:center;font-size:30px;border-radius:10px;color:white;'>{last_signal}</div>", unsafe_allow_html=True)

        st.subheader("🔮 Prognose (nächste 3 Tage)")
        st.markdown(f"<div style='background-color:{forecast_color.get(tendenz,'#CCCCCC')};padding:20px;text-align:center;font-size:25px;border-radius:10px;color:white;'>{tendenz}</div>", unsafe_allow_html=True)

        # --- Historie ---
        st.subheader("🟡 Historie der letzten 20 Signale")
        df_hist = df_reset[["Date","Advanced_Signal"]].tail(20).copy()
        df_hist["Signal_Code"] = df_hist["Advanced_Signal"].map({"Stark Kauf":2,"Halten":1,"Stark Verkauf":0})
        st.dataframe(df_hist.set_index("Date")[["Signal_Code"]].style.background_gradient(cmap="RdYlGn", axis=None))
