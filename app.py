import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import time

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.title("📊 Trading Dashboard Pro")

# -----------------------
# Session State Init
# -----------------------
if "portfolio" not in st.session_state or not isinstance(st.session_state.portfolio, pd.DataFrame):
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl",
        "StopLoss", "TakeProfit",
        "Status", "Gebühr"
    ])

# -----------------------
# Auto Refresh
# -----------------------
refresh_interval = st.sidebar.selectbox(
    "Auto-Refresh",
    ["Aus", "30 Sekunden", "60 Sekunden"]
)

if refresh_interval != "Aus":
    seconds = int(refresh_interval.split()[0])
    time.sleep(seconds)
    st.rerun()

# -----------------------
# Aktie hinzufügen
# -----------------------
st.subheader("🔧 Aktie hinzufügen")

cols = st.columns(6)
ticker = cols[0].text_input("Ticker (z.B. RHM.DE)")
kaufpreis = cols[1].number_input("Kaufpreis €", min_value=0.01, step=0.01)
stk = cols[2].number_input("Stückzahl", min_value=1, step=1)
sl = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
tp = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
status = cols[5].selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Hinzufügen"):
    if ticker:
        new_row = pd.DataFrame([{
            "Ticker": ticker.upper(),
            "Kaufpreis": kaufpreis,
            "Stückzahl": stk,
            "StopLoss": sl,
            "TakeProfit": tp,
            "Status": status,
            "Gebühr": 1.0
        }])
        st.session_state.portfolio = pd.concat(
            [st.session_state.portfolio, new_row],
            ignore_index=True
        )
        st.success(f"{ticker.upper()} hinzugefügt")

# -----------------------
# Portfolio Berechnung
# -----------------------
st.subheader("📋 Portfolio")

portfolio = st.session_state.portfolio

if not portfolio.empty:

    aktuelle_preise = []
    positionswerte = []
    gewinne = []
    signale = []

    for _, row in portfolio.iterrows():
        try:
            df = yf.download(row["Ticker"], period="1d", progress=False)
            preis = float(df["Close"].iloc[-1])
        except:
            preis = 0.0

        aktuelle_preise.append(preis)

        poswert = preis * row["Stückzahl"]
        positionswerte.append(poswert)

        invest = row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"]
        gewinn = poswert - invest
        gewinne.append(gewinn)

        signal = "Halten"

        if row["StopLoss"] > 0 and preis <= row["StopLoss"]:
            signal = "SELL (Stop-Loss)"
        if row["TakeProfit"] > 0 and preis >= row["TakeProfit"]:
            signal = "TAKE PROFIT"

        signale.append(signal)

    portfolio["Aktueller Preis"] = aktuelle_preise
    portfolio["Positionswert"] = positionswerte
    portfolio["Gewinn"] = gewinne
    portfolio["Signal"] = signale

    # -----------------------
    # KPI Gesamtperformance
    # -----------------------
    gesamt_invest = (portfolio["Kaufpreis"] * portfolio["Stückzahl"]).sum()
    gesamt_wert = portfolio["Positionswert"].sum()
    gesamt_gewinn = gesamt_wert - gesamt_invest

    col1, col2, col3 = st.columns(3)
    col1.metric("Depotwert", f"{gesamt_wert:,.2f} €")
    col2.metric("Investiert", f"{gesamt_invest:,.2f} €")
    col3.metric(
        "Gesamtgewinn",
        f"{gesamt_gewinn:,.2f} €",
        delta=f"{(gesamt_gewinn/gesamt_invest*100 if gesamt_invest>0 else 0):.2f}%"
    )

    # -----------------------
    # Farbige Anzeige
    # -----------------------
    def color_profit(val):
        if val > 0:
            return "color: green"
        if val < 0:
            return "color: red"
        return ""

    styled = portfolio.style.map(color_profit, subset=["Gewinn"])

    st.dataframe(styled, use_container_width=True)

else:
    st.info("Portfolio ist leer.")

# -----------------------
# Chart
# -----------------------
st.subheader("📈 Kursverlauf")

ticker_list = list(portfolio["Ticker"]) if not portfolio.empty else []
selected = st.selectbox("Aktie wählen", ticker_list)

if selected:
    try:
        df_chart = yf.download(selected, period="6mo", progress=False)
        df_chart.reset_index(inplace=True)

        chart = alt.Chart(df_chart).mark_line().encode(
            x="Date",
            y="Close"
        ).properties(
            width=900,
            height=350,
            title=f"{selected} - 6 Monate"
        )

        st.altair_chart(chart)
    except:
        st.warning("Chart konnte nicht geladen werden.")
