import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import os
import json

st.set_page_config(layout="wide")

# ==============================
# CONFIG
# ==============================
PORTFOLIO_FILE = "portfolio.json"

# ==============================
# LOAD PORTFOLIO
# ==============================
if "aktien_liste" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            st.session_state.aktien_liste = json.load(f)
    else:
        st.session_state.aktien_liste = []

def save_portfolio():
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(st.session_state.aktien_liste, f)

# ==============================
# HEADER
# ==============================
st.title("📊 Trading Dashboard Pro")

# ==============================
# PORTFOLIO ADD
# ==============================
st.subheader("💼 Aktie hinzufügen")

with st.form("add_form"):
    ticker_input = st.text_input("Ticker (z.B. RHM oder RHM.DE)")
    status = st.selectbox("Status", ["Besitzt", "Beobachtung"])
    submit = st.form_submit_button("Hinzufügen")

if submit and ticker_input:

    ticker = ticker_input.upper().strip()

    # Deutsche Aktien automatisch .DE
    if "." not in ticker and len(ticker) <= 5:
        ticker_test = ticker + ".DE"
    else:
        ticker_test = ticker

    # Prüfen ob Yahoo Daten liefert
    test_df = yf.download(ticker_test, period="5d", interval="1d")

    if test_df.empty:
        st.error("Ticker ungültig oder keine Daten verfügbar.")
    else:
        exists = any(a["ticker"] == ticker_test for a in st.session_state.aktien_liste)
        if not exists:
            st.session_state.aktien_liste.append({
                "ticker": ticker_test,
                "status": status
            })
            save_portfolio()
            st.success(f"{ticker_test} hinzugefügt.")

# ==============================
# PORTFOLIO TABLE
# ==============================
st.subheader("📋 Portfolio")

if st.session_state.aktien_liste:

    table_data = []

    for i, a in enumerate(st.session_state.aktien_liste):

        df = yf.download(a["ticker"], period="2d", interval="1d")

        if not df.empty:
            last = df["Close"].iloc[-1]
            prev = df["Close"].iloc[-2] if len(df) > 1 else last
            change_pct = ((last - prev) / prev) * 100
        else:
            last = None
            change_pct = None

        table_data.append({
            "Ticker": a["ticker"],
            "Status": a["status"],
            "Preis": round(last, 2) if last else None,
            "Tages %": round(change_pct, 2) if change_pct else None
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)

else:
    st.info("Noch keine Aktien im Portfolio.")

# ==============================
# DETAILANSICHT
# ==============================
if st.session_state.aktien_liste:

    selected = st.selectbox(
        "📈 Detailansicht wählen",
        [a["ticker"] for a in st.session_state.aktien_liste]
    )

    df = yf.download(selected, period="6mo", interval="1d")

    if not df.empty:

        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        chart = alt.Chart(df.reset_index()).transform_fold(
            ["Close", "SMA20", "SMA50"],
            as_=["Line", "Value"]
        ).mark_line().encode(
            x="Date:T",
            y="Value:Q",
            color="Line:N"
        ).properties(
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

    else:
        st.warning("Keine historischen Daten verfügbar.")
