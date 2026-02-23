import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"]
    )

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")

cols = st.columns([2, 1, 1, 1, 1, 1, 1])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
status_input = cols[5].selectbox("Status", ["Besitzt", "Beobachtung"])
fee = 1.00  # feste Kaufgebühr pro Aktie

if cols[6].button("Aktie hinzufügen"):
    if ticker_input != "":
        new_row = pd.DataFrame([{
            "Ticker": ticker_input,
            "Kaufpreis": price_input,
            "Stückzahl": stk_input,
            "Stop-Loss": stop_loss_input,
            "Take-Profit": take_profit_input,
            "Status": status_input,
            "Gebühr": fee
        }])
        st.session_state.portfolio = pd.concat(
            [st.session_state.portfolio, new_row], ignore_index=True
        )
        st.success(f"Aktie {ticker_input} hinzugefügt!")
        st.experimental_rerun()
    else:
        st.warning("Bitte einen Ticker eingeben.")

# --- Portfolio ---
st.subheader("📋 Portfolio")

if st.session_state.portfolio.empty:
    st.info("Keine Aktien im Portfolio.")
else:
    portfolio_df = st.session_state.portfolio.copy()
    
    # Aktuellen Kurs abrufen
    def get_current_price(ticker):
        try:
            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            if data.empty:
                return None
            return data["Close"][-1]
        except:
            return None

    current_prices = []
    pos_values = []
    profits = []
    signals = []
    
    for idx, row in portfolio_df.iterrows():
        current = get_current_price(row["Ticker"])
        current_prices.append(current if current is not None else 0)
        pos_val = (current if current is not None else 0) * row["Stückzahl"] - row["Gebühr"]
        pos_values.append(pos_val)
        profit = pos_val - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"])
        profits.append(profit)
        signals.append("Halten" if profit >= 0 else "SELL")

    portfolio_df["Aktueller Preis"] = current_prices
    portfolio_df["Positionswert"] = pos_values
    portfolio_df["Gewinn/Verlust"] = profits
    portfolio_df["Signal"] = signals
    
    # Tabelle anzeigen
    st.dataframe(portfolio_df[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]])

    # Einzelne Aktie löschen
    ticker_to_delete = st.selectbox("Aktie löschen", [""] + list(portfolio_df["Ticker"]))
    if st.button("Löschen"):
        if ticker_to_delete != "":
            st.session_state.portfolio = portfolio_df[portfolio_df["Ticker"] != ticker_to_delete].reset_index(drop=True)
            st.success(f"Aktie {ticker_to_delete} gelöscht!")
            st.experimental_rerun()

# --- Kursverlauf ---
st.subheader("📈 Kursverlauf")

selected_ticker = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"].unique()))
timeframe = st.selectbox("Zeitraum", ["1d", "1wk", "1mo", "1y"], help="1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")
st.caption("Abkürzungen: 1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")

if selected_ticker:
    data_hist = yf.download(selected_ticker, period="1y", interval="1d", progress=False)
    if data_hist.empty:
        st.error("Chart konnte nicht geladen werden. Prüfe den Ticker.")
    else:
        chart = alt.Chart(data_hist.reset_index()).mark_line().encode(
            x="Date:T",
            y="Close:Q",
            tooltip=["Date:T", "Close:Q"]
        ).properties(height=300, width=700)
        st.altair_chart(chart, use_container_width=True)
