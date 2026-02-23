import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import uuid

# --- Page Config ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
    )

# --- Demo-Aktien einfügen, wenn Portfolio leer ---
if st.session_state.portfolio.empty:
    demo_data = [
        {
            "ID": str(uuid.uuid4()),
            "Ticker": "RHM.DE",
            "Kaufpreis": 50.0,
            "Stückzahl": 10,
            "Stop-Loss": 45.0,
            "Take-Profit": 60.0,
            "Status": "Besitzt",
            "Gebühr": 1.0
        },
        {
            "ID": str(uuid.uuid4()),
            "Ticker": "SAP.DE",
            "Kaufpreis": 120.0,
            "Stückzahl": 5,
            "Stop-Loss": 110.0,
            "Take-Profit": 140.0,
            "Status": "Beobachtung",
            "Gebühr": 1.0
        }
    ]
    st.session_state.portfolio = pd.DataFrame(demo_data)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie hinzufügen", "📈 Kurs & Chart"])

# --- 1️⃣ Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio")
    df = st.session_state.portfolio.copy()

    # --- Aktuelle Preise abrufen ---
    tickers = df["Ticker"].unique().tolist()
    data = yf.download(tickers, period="5d", interval="1d", progress=False)["Close"]
    if isinstance(data, pd.Series):
        latest_prices = pd.Series({tickers[0]: data[-1]})
    else:
        latest_prices = data.iloc[-1]
    df["Aktueller Preis"] = df["Ticker"].map(latest_prices)
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])

    # --- Smarte Signale ---
    def compute_signal(row):
        if row["Aktueller Preis"] <= row["Stop-Loss"]:
            return "SELL"
        elif row["Aktueller Preis"] >= row["Take-Profit"]:
            return "Take-Profit"
        elif row["Gewinn/Verlust"] >= 0:
            return "Halten"
        else:
            return "SELL"
    df["Signal"] = df.apply(compute_signal, axis=1)

    # --- Farbige Signale ---
    def color_signal(val):
        if val == "SELL":
            color = "background-color: #ff4d4d; color:white"
        elif val == "Take-Profit":
            color = "background-color: #4caf50; color:white"
        else:
            color = "background-color: #2196f3; color:white"
        return color

    st.dataframe(df.style.applymap(color_signal, subset=["Signal"]), height=300)

    # --- Löschen mit UUID ---
    st.markdown("### Aktien löschen")
    delete_options = df[["ID","Ticker"]].apply(lambda x: f"{x['Ticker']} ({x['ID'][:6]})", axis=1).tolist()
    delete_choice = st.selectbox("Wähle Aktie zum Löschen", [""] + delete_options)
    if st.button("Löschen"):
        if delete_choice:
            selected_id = delete_choice.split("(")[-1].replace(")","")
            st.session_state.portfolio = df[df["ID"] != selected_id].reset_index(drop=True)
            st.success("Aktie gelöscht!")

# --- 2️⃣ Aktie hinzufügen Tab ---
with tab2:
    st.subheader("Neue Aktie hinzufügen")
    cols = st.columns([2,1,1,1,1,1])
    ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = cols[5].selectbox("Status", ["Besitzt","Beobachtung"])
    fee = st.number_input("Gebühr pro Aktie (€)", min_value=0.0, step=0.1, value=1.0)

    if st.button("Hinzufügen"):
        if ticker_input:
            new_row = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "Ticker": ticker_input,
                "Kaufpreis": price_input,
                "Stückzahl": stk_input,
                "Stop-Loss": stop_loss_input,
                "Take-Profit": take_profit_input,
                "Status": status_input,
                "Gebühr": fee
            }])
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
            st.success(f"Aktie {ticker_input} hinzugefügt!")
        else:
            st.warning("Bitte Ticker eingeben.")

# --- 3️⃣ Chart Tab ---
with tab3:
    st.subheader("Kursverlauf & SMA")
    selected_ticker = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"].unique()))
    timeframe = st.selectbox("Zeitraum", ["1d","1wk","1mo","1y"])
    if selected_ticker:
        period_map = {"1d":"7d","1wk":"6mo","1mo":"2y","1y":"5y"}
        interval_map = {"1d":"15m","1wk":"1d","1mo":"1d","1y":"1wk"}
        data_hist = yf.download(selected_ticker, period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
        if data_hist.empty:
            st.error("Chart konnte nicht geladen werden.")
        else:
            data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
            data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
            df_chart = data_hist.reset_index()

            base = alt.Chart(df_chart).encode(x="Date:T")
            chart = alt.layer(
                base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
            ).resolve_scale(y="shared").properties(height=400)
            st.altair_chart(chart, use_container_width=True)
            st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")
