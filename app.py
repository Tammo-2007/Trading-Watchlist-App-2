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

# --- Linke Spalte ---
left_col, right_col = st.columns([1,3])

with left_col:
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

    # Mandant wählen
    if st.session_state.mandanten:
        mandant_list = list(st.session_state.mandanten.keys())
        st.session_state.active_mandant = st.selectbox("Mandant wählen", mandant_list, index=0)
    else:
        st.warning("Bitte erst einen Mandanten anlegen.")

    # Aktie/ETF hinzufügen
    st.subheader("➕ Aktie/ETF hinzufügen")
    if st.session_state.active_mandant:
        portfolio = st.session_state.mandanten[st.session_state.active_mandant]
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
        price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
        stk_input = st.number_input("Stückzahl", min_value=1, step=1)
        stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01)
        take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01)
        status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
        fee = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

        if st.button("Hinzufügen"):
            if ticker_input:
                new_row = pd.DataFrame([{
                    "ID": str(uuid.uuid4()),
                    "Ticker": ticker_input,
                    "Kaufpreis": price_input,
                    "Stückzahl": stk_input,
                    "Stop-Loss": stop_loss_input,
                    "Take-Profit": take_profit_input,
                    "Status": status_input,
                    "Gebühr": fee
                }])
                portfolio = pd.concat([portfolio, new_row], ignore_index=True)
                st.session_state.mandanten[st.session_state.active_mandant] = portfolio
                st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
                st.experimental_rerun()

# --- Rechte Spalte: Portfolio & Charts ---
with right_col:
    st.subheader("📋 Portfolio + Charts")

    if st.session_state.active_mandant:
        portfolio = st.session_state.mandanten[st.session_state.active_mandant]

        # Aktuelle Preise abrufen
        tickers = portfolio["Ticker"].tolist()
        latest_prices = {}
        for t in tickers:
            try:
                data = yf.download(t, period="5d", interval="1d", progress=False)
                latest_prices[t] = data["Close"][-1] if not data.empty else None
            except:
                latest_prices[t] = None
        portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda x: latest_prices.get(x, None))

        # Positionswert & Gewinn/Verlust
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"]*price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_volatility(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                returns = data["Close"].pct_change().dropna()
                volatility = returns.std()
                return max(row["Kaufpreis"] * (1 - volatility), 0)
            except:
                return row["Kaufpreis"] * 0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # --- Erwartetes Portfolio-Hoch ---
        def compute_expected_portfolio_high(df):
            total = 0
            for _, row in df.iterrows():
                try:
                    ticker_obj = yf.Ticker(row["Ticker"])
                    info = ticker_obj.info
                    target_price = info.get("targetMeanPrice", row["Kaufpreis"])
                except:
                    target_price = row["Kaufpreis"]
                total += row["Stückzahl"]*target_price - row["Gebühr"]
            return total

        if not portfolio.empty:
            expected_high = compute_expected_portfolio_high(portfolio)
            st.markdown(f"""
                <div style="border:2px solid #999; padding:15px; border-radius:10px; margin-bottom:20px; background-color:#f0f0f0; font-size:18px;">
                <b>Erwartetes Portfolio-Hoch:</b> {expected_high:,.2f} €
                </div>
            """, unsafe_allow_html=True)

        # --- Portfolio Cards + Charts ---
        for _, row in portfolio.iterrows():
            col1_card, col2_chart = st.columns([1,2])

            with col1_card:
                # Analysten-Daten
                try:
                    ticker_obj = yf.Ticker(row["Ticker"])
                    info = ticker_obj.info
                    analyst_rating = info.get("recommendationKey","hold").capitalize()
                    target_price = info.get("targetMeanPrice", None)
                except:
                    analyst_rating = "Hold"
                    target_price = None

                # Ampelfarbe
                rating_color_map = {"Buy":"#a8e6a3", "Hold":"#fff4b3", "Sell":"#f5a3a3"}
                card_color = rating_color_map.get(analyst_rating,"#e0e0e0")

                st.markdown(f"""
                <div style="border:1px solid #ccc; padding:10px; border-radius:10px; margin-bottom:10px; background-color:{card_color}; color:#000;">
                <b>{row['Ticker']}</b> {'🟢' if row['Gewinn/Verlust']>=0 else '🔴'}<br>
                Status: {row['Status']}<br>
                Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                Positionswert: {row['Positionswert']:.2f} €<br>
                Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
                📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
                Analysten-Rating: {analyst_rating} | Target: {target_price if target_price else 'n/a'} €<br>
                Gebühr: {row['Gebühr']} € (pro Order)
                </div>
                """, unsafe_allow_html=True)

            with col2_chart:
                timeframe = st.selectbox(
                    f"Zeitraum für {row['Ticker']}",
                    ["1T","1W","1M","1J","Max"], key=row["ID"]
                )
                period_map = {"1T":"7d","1W":"1mo","1M":"6mo","1J":"2y","Max":"5y"}
                interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","Max":"1wk"}

                try:
                    data_hist = yf.download(
                        row["Ticker"], 
                        period=period_map[timeframe], 
                        interval=interval_map[timeframe], 
                        progress=False
                    )
                    if not data_hist.empty:
                        data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                        data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                        df_chart = data_hist.reset_index()

                        base = alt.Chart(df_chart).encode(x="Date:T")
                        chart = alt.layer(
                            base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q","SMA20:Q","SMA50:Q"]),
                            base.mark_line(color="orange").encode(y="SMA20:Q"),
                            base.mark_line(color="green").encode(y="SMA50:Q")
                        ).resolve_scale(y="shared").properties(height=200)
                        st.altair_chart(chart, use_container_width=True)
                except:
                    st.error(f"Chart für {row['Ticker']} konnte nicht geladen werden.")
