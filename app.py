# ==============================
# IMPORTS
# ==============================
import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import os
import json

st.set_page_config(layout="wide")

PORTFOLIO_FILE = "portfolio.json"

# ==============================
# LOAD PORTFOLIO
# ==============================
if "portfolio" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            st.session_state.portfolio = json.load(f)
    else:
        st.session_state.portfolio = []

def save_portfolio():
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(st.session_state.portfolio, f)

# ==============================
# HEADER
# ==============================
st.title("📊 Trading Dashboard Pro")

# ==============================
# ADD STOCK
# ==============================
st.subheader("💼 Aktie hinzufügen")

with st.form("add_stock"):
    ticker = st.text_input("Ticker (z.B. RHM.DE)")
    buy_price = st.number_input("Kaufpreis (€)", min_value=0.0, step=0.1)
    quantity = st.number_input("Stückzahl", min_value=1, step=1)
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])
    submitted = st.form_submit_button("Hinzufügen")

if submitted and ticker:

    ticker = ticker.upper().strip()

    test_df = yf.download(ticker, period="5d", interval="1d")

    if test_df.empty:
        st.error("Ticker ungültig oder keine Daten verfügbar.")
    else:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "buy_price": buy_price,
            "quantity": quantity,
            "status": status
        })
        save_portfolio()
        st.success(f"{ticker} hinzugefügt.")

# ==============================
# PORTFOLIO VIEW
# ==============================
st.subheader("📋 Portfolio")

total_value = 0
total_invested = 0

if st.session_state.portfolio:

    for i, stock in enumerate(st.session_state.portfolio):

        col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,2,2,1])

        ticker = stock["ticker"]
        df = yf.download(ticker, period="3mo", interval="1d")

        if not df.empty and "Close" in df.columns:

            current_price = float(df["Close"].iloc[-1])
            invested = stock["buy_price"] * stock["quantity"]
            position_value = current_price * stock["quantity"]
            profit = position_value - invested
            profit_pct = (profit / invested) * 100 if invested != 0 else 0

            total_value += position_value
            total_invested += invested

            # Trend Signal
            df["SMA20"] = df["Close"].rolling(20).mean()
            df["SMA50"] = df["Close"].rolling(50).mean()

            sma20 = df["SMA20"].iloc[-1]
            sma50 = df["SMA50"].iloc[-1]

            if pd.notna(sma20) and pd.notna(sma50):
                if sma20 > sma50:
                    signal = "BUY"
                    signal_color = "green"
                elif sma20 < sma50:
                    signal = "SELL"
                    signal_color = "red"
                else:
                    signal = "HOLD"
                    signal_color = "orange"
            else:
                signal = "-"
                signal_color = "gray"

        else:
            current_price = None
            position_value = 0
            profit = 0
            profit_pct = 0
            signal = "-"
            signal_color = "gray"

        col1.write(f"**{ticker}**")
        col2.write(f"{round(current_price,2)} €" if current_price else "-")
        col3.write(f"{round(position_value,2)} €")

        col4.markdown(
            f"<span style='color:{'green' if profit>=0 else 'red'}'>"
            f"{round(profit,2)} € ({round(profit_pct,2)}%)</span>",
            unsafe_allow_html=True
        )

        col5.markdown(
            f"<span style='color:{signal_color}'><b>{signal}</b></span>",
            unsafe_allow_html=True
        )

        if col6.button("❌", key=f"delete_{i}"):
            st.session_state.portfolio.pop(i)
            save_portfolio()
            st.rerun()

    st.divider()

    portfolio_profit = total_value - total_invested
    portfolio_pct = (portfolio_profit / total_invested) * 100 if total_invested != 0 else 0

    st.subheader("💰 Gesamtportfolio")

    colA, colB, colC = st.columns(3)
    colA.metric("Investiert", f"{round(total_invested,2)} €")
    colB.metric("Aktueller Wert", f"{round(total_value,2)} €")
    colC.metric(
        "Gewinn / Verlust",
        f"{round(portfolio_profit,2)} €",
        f"{round(portfolio_pct,2)} %"
    )

else:
    st.info("Noch keine Aktien im Portfolio.")

# ==============================
# DETAIL CHART
# ==============================
if st.session_state.portfolio:

    selected = st.selectbox(
        "📈 Detailansicht",
        [s["ticker"] for s in st.session_state.portfolio]
    )

    df = yf.download(selected, period="6mo", interval="1d")

    if not df.empty and "Close" in df.columns:

        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        chart = alt.Chart(df.reset_index()).transform_fold(
            ["Close", "SMA20", "SMA50"],
            as_=["Linie", "Wert"]
        ).mark_line().encode(
            x="Date:T",
            y="Wert:Q",
            color="Linie:N"
        ).properties(height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.warning("Keine historischen Daten verfügbar.")
