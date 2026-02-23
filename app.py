import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")
st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State korrekt initialisieren ---
if "portfolio" not in st.session_state or not isinstance(st.session_state.portfolio, pd.DataFrame):
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 2, 2, 1])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)")
purchase_price = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
stk = cols[2].number_input("Stückzahl", min_value=1, step=1)
status = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen"):
    if ticker_input:
        new_row = pd.DataFrame([{
            "Ticker": ticker_input.upper(),
            "Kaufpreis": purchase_price,
            "Stückzahl": stk,
            "Status": status,
            "Gebühr": 1.00  # Kaufgebühr
        }])
        st.session_state.portfolio = pd.concat(
            [st.session_state.portfolio, new_row], ignore_index=True
        )
        st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
        st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
portfolio = st.session_state.portfolio

if not portfolio.empty:
    # Aktueller Preis und Gewinn/Verlust berechnen
    current_prices = []
    pos_values = []
    profits = []
    signals = []

    for idx, row in portfolio.iterrows():
        try:
            df_price = yf.download(row["Ticker"], period="1d", interval="1d", progress=False)
            current_price = df_price["Close"].iloc[-1]
        except:
            current_price = 0.0
        current_prices.append(current_price)

        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        pos_values.append(pos_value)

        profit = pos_value - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"])
        profits.append(profit)

        signals.append("Halten" if profit >= 0 else "SELL")

    portfolio_display = portfolio.copy()
    portfolio_display["Aktueller Preis"] = current_prices
    portfolio_display["Positionswert"] = pos_values
    portfolio_display["Gewinn/Verlust"] = profits
    portfolio_display["Signal"] = signals

    st.dataframe(portfolio_display[[
        "Ticker", "Kaufpreis", "Stückzahl", "Gebühr", "Aktueller Preis",
        "Positionswert", "Gewinn/Verlust", "Signal", "Status"
    ]])
else:
    st.info("Portfolio ist leer. Füge Aktien hinzu!")

# --- Kursverlauf (Altair Chart) ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Wähle eine Aktie", [""] + list(portfolio["Ticker"]))

if selected_ticker:
    try:
        df_chart = yf.download(selected_ticker, period="6mo", interval="1d", progress=False)
        if not df_chart.empty:
            df_chart.reset_index(inplace=True)
            chart = alt.Chart(df_chart).mark_line().encode(
                x="Date",
                y="Close"
            ).properties(width=800, height=300, title=f"Kursverlauf {selected_ticker}")
            st.altair_chart(chart, use_container_width=False)
        else:
            st.warning("Keine historischen Daten verfügbar.")
    except:
        st.error("Fehler beim Abrufen der historischen Daten.")
