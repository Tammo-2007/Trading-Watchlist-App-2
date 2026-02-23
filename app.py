import streamlit as st
import yfinance as yf
import pandas as pd

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State Initialisierung ---
if "portfolio" not in st.session_state or st.session_state.portfolio is None:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])

# --- Kompakte Zeile: Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1])  # vier Spalten nebeneinander

ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
buy_price = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
shares = cols[2].number_input("Stückzahl", min_value=1, step=1)
status = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen") and ticker_input:
    fee = 1.0  # feste Kaufgebühr
    st.session_state.portfolio = pd.concat([
        st.session_state.portfolio,
        pd.DataFrame([{
            "Ticker": ticker_input,
            "Kaufpreis": buy_price,
            "Stückzahl": shares,
            "Status": status,
            "Gebühr": fee
        }])
    ], ignore_index=True)
    st.success(f"Aktie {ticker_input} hinzugefügt!")

# --- Portfolio Tabelle ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio is None or st.session_state.portfolio.empty:
    st.info("Keine Aktien im Portfolio.")
else:
    df = st.session_state.portfolio.copy()
    
    # Aktueller Kurs
    def get_price(ticker):
        try:
            data = yf.download(ticker, period="1d", progress=False)
            if not data.empty:
                return float(data["Close"].iloc[-1])
        except:
            return 0
        return 0

    df["Aktueller Preis"] = df["Ticker"].apply(get_price)
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])
    df["Signal"] = df["Gewinn/Verlust"].apply(lambda x: "Halten" if x >= 0 else "SELL")

    st.dataframe(df[["Ticker","Kaufpreis","Stückzahl","Status","Aktueller Preis","Positionswert","Gewinn/Verlust","Signal"]])
