import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Mandantenverwaltung ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# Sidebar: Mandanten + Aktie hinzufügen
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
        st.session_state.active_mandant = st.selectbox(
            "Mandant wählen",
            list(st.session_state.mandanten.keys()),
            index=0
        )

    # Aktie/ETF hinzufügen
    if st.session_state.active_mandant:
        st.subheader("➕ Aktie/ETF hinzufügen")
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
        price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
        stk_input = st.number_input("Stückzahl", min_value=1, step=1)
        stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
        take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
        status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
        fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)
        if st.button("Hinzufügen Aktie"):
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
            st.session_state.mandanten[st.session_state.active_mandant] = pd.concat([df, new_row], ignore_index=True)
            st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
            st.experimental_rerun()

# --- Hauptbereich: Portfolio + Charts ---
if st.session_state.active_mandant:
    portfolio = st.session_state.mandanten.get(st.session_state.active_mandant, pd.DataFrame())
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        st.subheader("📋 Portfolio + Charts")
        for idx, row in portfolio.iterrows():
            ticker = row["Ticker"]
            # Aktueller Preis abrufen
            try:
                data = yf.download(ticker, period="5d", interval="1d", progress=False)
                price = data["Close"].iloc[-1] if not data.empty else None
            except:
                price = None

            # Sicher Positionswert & Gewinn berechnen
            try:
                price_val = float(price) if price is not None else 0.0
                gebuehr_val = float(row["Gebühr"]) if row["Gebühr"] is not None else 0.0
                stueckzahl_val = float(row["Stückzahl"]) if row["Stückzahl"] is not None else 0.0
                kaufpreis_val = float(row["Kaufpreis"]) if row["Kaufpreis"] is not None else 0.0
                positionswert = stueckzahl_val * price_val - gebuehr_val
                gewinn = positionswert - (kaufpreis_val*stueckzahl_val + gebuehr_val)
            except:
                positionswert = 0.0
                gewinn = 0.0

            # Hintergrundfarbe der Card
            if gewinn > 0:
                bg_color = "#d4edda"  # hellgrün
            elif gewinn < 0:
                bg_color = "#f8d7da"  # hellrot
            else:
                bg_color = "#f0f0f0"  # neutral

            # Portfolio Card
            st.markdown(f"""
            <div style="
                border:1px solid #ccc; 
                padding:10px; 
                margin-bottom:10px; 
                background-color:{bg_color};
                border-radius:8px;
                color:#000000;
            ">
            <b>{ticker}</b><br>
            Status: {row['Status']}<br>
            Preis: {price_val:.2f} €<br>
            Positionswert: {positionswert:.2f} €<br>
            Gewinn/Verlust: {gewinn:.2f} €<br>
            📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
            ⚠️ Stop-Loss Empfehlung: {round(kaufpreis_val*0.95,2)} €<br>
            Gebühr: {gebuehr_val} € (pro Order)
            </div>
            """, unsafe_allow_html=True)

            # Chart direkt unter der Card
            st.subheader(f"📈 Chart: {ticker}")
            timeframe = st.selectbox(f"Zeitraum für {ticker}", ["1T","1W","1M","1J","MAX"], key=idx)
            period_map = {"1T":"7d","1W":"6mo","1M":"2y","1J":"5y","MAX":"10y"}
            interval_map = {"1T":"15m","1W":"1d","1M":"1d","1J":"1wk","MAX":"1mo"}
            try:
                hist = yf.download(ticker, period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
                if not hist.empty:
                    hist["SMA20"] = hist["Close"].rolling(20).mean()
                    hist["SMA50"] = hist["Close"].rolling(50).mean()
                    df_chart = hist.reset_index()
                    base = alt.Chart(df_chart).encode(x="Date:T")
                    chart = alt.layer(
                        base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                        base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                        base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                    ).resolve_scale(y="shared").properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                    st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")
                else:
                    st.warning(f"Chart für {ticker} konnte nicht geladen werden.")
            except:
                st.warning(f"Chart für {ticker} konnte nicht geladen werden.")
