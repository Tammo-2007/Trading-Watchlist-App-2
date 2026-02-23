# ==============================
# IMPORTS
# ==============================
import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import feedparser
import os
import json

st.set_page_config(layout="wide")

PORTFOLIO_FILE = "portfolio.json"

# ==============================
# SESSION STATE
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
st.title("📊 Kompaktes Trading Dashboard Pro")

# ==============================
# SIGNALS + PORTFOLIO ADD
# ==============================
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
col_a, col_b, col_c, col_d = st.columns(4)

with st.form("add_stock", clear_on_submit=True):
    with col_a:
        ticker = st.text_input("Ticker (z.B. RHM.DE)")
    with col_b:
        buy_price = st.number_input("Kaufpreis (€)", min_value=0.0, step=0.1)
    with col_c:
        quantity = st.number_input("Stückzahl", min_value=1.0, step=1.0)
    with col_d:
        status = st.selectbox("Status", ["Besitzt", "Beobachtung"])
    submitted = st.form_submit_button("Hinzufügen")

if submitted and ticker:
    ticker = ticker.upper().strip()
    df_test = yf.download(ticker, period="5d", interval="1d")
    if df_test.empty:
        st.error("Ticker ungültig oder keine Daten verfügbar.")
    else:
        # Kaufgebühr 1€ pro Trade auf Stückpreis verteilen
        buy_price += 1.0 / quantity
        st.session_state.portfolio.append({
            "ticker": ticker,
            "buy_price": float(buy_price),
            "quantity": float(quantity),
            "status": status
        })
        save_portfolio()
        st.success(f"{ticker} hinzugefügt.")

# ==============================
# PORTFOLIO VIEW
# ==============================
st.subheader("📋 Portfolio")

if st.session_state.portfolio:

    # Spaltenüberschriften
    cols = st.columns([2,2,2,2,2,1])
    cols[0].markdown("**Ticker**")
    cols[1].markdown("**Aktueller Preis**")
    cols[2].markdown("**Positionswert**")
    cols[3].markdown("**Gewinn/Verlust**")
    cols[4].markdown("**Signal**")
    cols[5].markdown("**Aktionen**")

    total_value = 0
    total_invested = 0

    for i, stock in enumerate(st.session_state.portfolio):
        cols = st.columns([2,2,2,2,2,1])
        ticker = stock["ticker"]
        df = yf.download(ticker, period="3mo", interval="1d")

        if not df.empty and "Close" in df.columns:
            current_price = float(df["Close"].iloc[-1])
            invested = stock["buy_price"] * stock["quantity"]
            position_value = current_price * stock["quantity"]
            profit = position_value - invested - 1.0
            profit_pct = (profit / invested) * 100 if invested != 0 else 0
            total_value += position_value
            total_invested += invested

            df["SMA20"] = df["Close"].rolling(20).mean()
            df["SMA50"] = df["Close"].rolling(50).mean()
            sma20 = df["SMA20"].iloc[-1]
            sma50 = df["SMA50"].iloc[-1]
            if pd.notna(sma20) and pd.notna(sma50):
                if sma20 > sma50:
                    signal = "BUY"
                    color_signal = "green"
                elif sma20 < sma50:
                    signal = "SELL"
                    color_signal = "red"
                else:
                    signal = "HOLD"
                    color_signal = "orange"
            else:
                signal = "-"
                color_signal = "gray"
        else:
            current_price = None
            position_value = 0
            profit = 0
            profit_pct = 0
            signal = "-"
            color_signal = "gray"

        # Anzeigen
        cols[0].write(f"{ticker}")
        cols[1].write(f"{round(current_price,2)} €" if current_price else "-")
        cols[2].write(f"{round(position_value,2)} €")
        cols[3].markdown(
            f"<span style='color:{'green' if profit>=0 else 'red'}'>"
            f"{round(profit,2)} € ({round(profit_pct,2)}%)</span>",
            unsafe_allow_html=True
        )
        cols[4].markdown(
            f"<span style='color:{color_signal}'><b>{signal}</b></span>",
            unsafe_allow_html=True
        )

        # Verkauf mit Modal
        if cols[5].button("💵 Verkaufen", key=f"sell_{i}"):
            with st.modal(f"Verkauf {ticker}", True):
                st.markdown(
                    f"**{stock['quantity']} Stück von {ticker}**\n\n"
                    f"Investiert: {round(invested,2)} €\n"
                    f"Aktueller Wert: {round(position_value,2)} €\n"
                    f"Gewinn/Verlust nach 1€ Gebühr: {round(profit,2)} €"
                )
                if st.button("Bestätigen", key=f"confirm_sell_{i}"):
                    st.session_state.portfolio.pop(i)
                    save_portfolio()
                    st.success(f"{ticker} verkauft!")
                    st.experimental_rerun()
                if st.button("Abbrechen", key=f"cancel_sell_{i}"):
                    st.info("Verkauf abgebrochen")

    # Gesamtportfolio
    st.divider()
    portfolio_profit = total_value - total_invested
    portfolio_pct = (portfolio_profit / total_invested) * 100 if total_invested != 0 else 0
    cols_tot = st.columns(3)
    cols_tot[0].metric("Investiert", f"{round(total_invested,2)} €")
    cols_tot[1].metric("Aktueller Wert", f"{round(total_value,2)} €")
    cols_tot[2].metric("Gewinn / Verlust", f"{round(portfolio_profit,2)} €", f"{round(portfolio_pct,2)} %")

else:
    st.info("Noch keine Aktien im Portfolio.")

# ==============================
# DETAILCHART & RSS NEWS
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
            ["Close","SMA20","SMA50"],
            as_=["Linie","Wert"]
        ).mark_line().encode(
            x="Date:T",
            y="Wert:Q",
            color="Linie:N"
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Keine historischen Daten verfügbar.")

    # ==============================
    # RSS NEWS
    # ==============================
    st.subheader(f"📰 RSS-News für {selected}")
    rss_feeds = [
        f"https://finance.yahoo.com/rss/headline?s={selected}",
        f"https://www.finanzen.net/rss/{selected}",
        f"https://www.finanztipps.de/rss"
    ]
    news_found = False
    for feed_url in rss_feeds:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            news_found = True
            for entry in feed.entries[:5]:
                st.markdown(f"- [{entry.title}]({entry.link})")
    if not news_found:
        st.info("Keine RSS-News verfügbar.")
