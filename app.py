import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime

# --- Initialisierung ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"
    ])

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1, 1, 1])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)", "")
price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
status_input = cols[5].selectbox("Status", ["Besitzt", "Beobachtung"])

add_btn = st.button("Aktie hinzufügen")

if add_btn and ticker_input:
    new_row = pd.DataFrame([{
        "Ticker": ticker_input.upper(),
        "Kaufpreis": price_input,
        "Stückzahl": stk_input,
        "Stop-Loss": stop_loss_input,
        "Take-Profit": take_profit_input,
        "Status": status_input,
        "Gebühr": 1.00  # Kaufgebühr
    }])
    st.session_state.portfolio = pd.concat(
        [st.session_state.portfolio, new_row], ignore_index=True
    )
    st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
    st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio.empty:
    st.info("Noch keine Aktien im Portfolio.")
else:
    df = st.session_state.portfolio.copy()
    current_prices = []
    pos_values = []
    profits = []
    signals = []

    for i, row in df.iterrows():
        try:
            data = yf.Ticker(row["Ticker"]).history(period="1d")
            current_price = data["Close"].iloc[-1] if not data.empty else 0
        except:
            current_price = 0

        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        profit = pos_value - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"])
        signal = "Halten" if profit >= 0 else "SELL"

        current_prices.append(current_price)
        pos_values.append(pos_value)
        profits.append(profit)
        signals.append(signal)

    df["Aktueller Preis"] = current_prices
    df["Positionswert"] = pos_values
    df["Gewinn/Verlust"] = profits
    df["Signal"] = signals

    # Portfolio-Tabelle mit Löschfunktion
    for i, row in df.iterrows():
        cols = st.columns([1, 1, 1, 1, 1, 1])
        cols[0].write(row["Ticker"])
        cols[1].write(f"{row['Aktueller Preis']:.2f} €")
        cols[2].write(f"{row['Positionswert']:.2f} €")
        cols[3].write(f"{row['Gewinn/Verlust']:.2f} €")
        cols[4].write(row["Signal"])
        if cols[5].button("❌ Löschen", key=f"del_{i}"):
            st.session_state.portfolio.drop(i, inplace=True)
            st.session_state.portfolio.reset_index(drop=True, inplace=True)
            st.experimental_rerun()

# --- Chart ---
st.subheader("📈 Kursverlauf")
chart_ticker = st.selectbox("Aktie wählen", df["Ticker"] if not st.session_state.portfolio.empty else [""])
timeframe = st.selectbox("Zeitraum", ["1d", "1wk", "1mo", "1y"], help="1d=Tag, 1wk=Woche, 1mo=Monat, 1y=Jahr")

if chart_ticker:
    try:
        hist = yf.Ticker(chart_ticker).history(period=timeframe)
        hist.reset_index(inplace=True)
        chart = alt.Chart(hist).mark_line().encode(
            x="Date",
            y="Close",
            tooltip=["Date", "Close"]
        ).properties(
            width=700, height=300
        )
        st.altair_chart(chart, use_container_width=True)
        st.markdown("**Abkürzungen:** 1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")
    except:
        st.warning("Chart konnte nicht geladen werden.")
