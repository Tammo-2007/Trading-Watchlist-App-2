import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt
import math

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Mandantenverwaltung ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# Sidebar
with st.sidebar:
    st.subheader("👤 Mandantenverwaltung")
    new_mandant = st.text_input("Neuen Mandanten anlegen")
    if st.button("Mandant hinzufügen") and new_mandant:
        if new_mandant not in st.session_state.mandanten:
            st.session_state.mandanten[new_mandant] = pd.DataFrame(
                columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
            )
            st.session_state.active_mandant = new_mandant
            st.success(f"Mandant '{new_mandant}' angelegt!")
        else:
            st.warning("Mandant existiert bereits!")

    if st.session_state.mandanten:
        mandant_list = list(st.session_state.mandanten.keys())
        st.session_state.active_mandant = st.selectbox("Mandant wählen", mandant_list, index=0)
    else:
        st.warning("Bitte erst einen Mandanten anlegen.")

    # --- Aktie/ETF hinzufügen ---
    if st.session_state.active_mandant:
        st.subheader("➕ Aktie/ETF hinzufügen")
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
        price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
        stk_input = st.number_input("Stückzahl", min_value=1, step=1)
        stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
        take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
        status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
        fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

        if st.button("Hinzufügen"):
            if ticker_input:
                df = st.session_state.mandanten[st.session_state.active_mandant]
                new_row = pd.DataFrame([{
                    "ID": str(uuid.uuid4()),
                    "Ticker": ticker_input,
                    "Kaufpreis": price_input,
                    "Stückzahl": stk_input,
                    "Stop-Loss": stop_loss_input,
                    "Take-Profit": take_profit_input,
                    "Status": status_input,
                    "Gebühr": fee_input
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                st.session_state.mandanten[st.session_state.active_mandant] = df
                st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
                st.experimental_rerun()

# --- Portfolio + Charts ---
if st.session_state.active_mandant:
    portfolio = st.session_state.mandanten[st.session_state.active_mandant]

    # Berechnungen
    if not portfolio.empty:
        tickers = portfolio["Ticker"].tolist()
        latest_prices = {}
        for t in tickers:
            try:
                data = yf.download(t, period="5d", interval="1d", progress=False)
                latest_prices[t] = data["Close"][-1] if not data.empty else None
            except:
                latest_prices[t] = None
        portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda x: latest_prices.get(x, None))

        def compute_values(row):
            price = row["Aktueller Preis"]
            if price is not None and not math.isnan(price):
                positionswert = row["Stückzahl"] * price - row["Gebühr"]
                gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            else:
                positionswert = 0
                gewinn = - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])

        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_volatility(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                if not data.empty:
                    returns = data["Close"].pct_change().dropna()
                    volatility = returns.std()
                    return max(row["Kaufpreis"]*(1-volatility), 0)
                else:
                    return row["Kaufpreis"]*0.95
            except:
                return row["Kaufpreis"]*0.95

        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # Anzeige: Portfolio + Charts nebeneinander
        for _, row in portfolio.iterrows():
            col1, col2 = st.columns([1,2])
            color = "🟢" if row["Gewinn/Verlust"] >=0 else "🔴"
            with col1:
                st.markdown(f"""
                <div style="border:1px solid #ccc; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f7f7f7;">
                <b>{row['Ticker']} {color}</b><br>
                Status: {row['Status']}<br>
                Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                Positionswert: {row['Positionswert']:.2f} €<br>
                Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
                📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
                Gebühr: {row['Gebühr']} € (pro Order)
                </div>
                """, unsafe_allow_html=True)
            with col2:
                try:
                    data_hist = yf.download(row["Ticker"], period="1y", interval="1d", progress=False)
                    if not data_hist.empty:
                        data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                        data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                        df_chart = data_hist.reset_index()

                        base = alt.Chart(df_chart).encode(x="Date:T")
                        chart = alt.layer(
                            base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                            base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                            base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                        ).resolve_scale(y="shared").properties(height=300)
                        st.altair_chart(chart, use_container_width=True)
                        st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")
                except:
                    st.warning("Chart konnte nicht geladen werden.")
