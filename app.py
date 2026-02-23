import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])

# --- Kompakte Signaleinstellungen & Aktie hinzufügen ---
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
            "Gebühr": 1.00  # fixe Kaufgebühr
        }])
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
        st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
        st.experimental_rerun()

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")

if not st.session_state.portfolio.empty:
    portfolio = st.session_state.portfolio.copy()
    
    # Aktuelle Kurse abrufen
    current_prices = []
    positions = []
    profits = []
    signals = []
    
    for idx, row in portfolio.iterrows():
        try:
            df = yf.download(row["Ticker"], period="1d", interval="1d", progress=False)
            if not df.empty:
                current_price = df["Close"].iloc[-1]
            else:
                current_price = 0
        except:
            current_price = 0
        current_prices.append(current_price)
        
        pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
        positions.append(pos_value)
        
        profit = pos_value - row["Kaufpreis"] * row["Stückzahl"] - row["Gebühr"]
        profits.append(profit)
        
        # Einfaches Signal: Gewinn positiv -> Halten, sonst SELL
        if profit >= 0:
            signals.append("Halten")
        else:
            signals.append("SELL")
    
    portfolio["Aktueller Preis"] = current_prices
    portfolio["Positionswert"] = positions
    portfolio["Gewinn/Verlust"] = profits
    portfolio["Signal"] = signals
    
    st.dataframe(portfolio[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]])
else:
    st.info("Portfolio ist leer. Füge Aktien hinzu!")

# --- Kursverlauf (Altair Chart) ---
st.subheader("📈 Kursverlauf")

selected_ticker = st.selectbox("Wähle eine Aktie", [""] + list(st.session_state.portfolio["Ticker"]))
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
