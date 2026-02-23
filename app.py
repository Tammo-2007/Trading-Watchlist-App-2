import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# --- Layout ---
left_col, right_col = st.columns([1,2])

# --- LINKS: Mandantenverwaltung + Aktie hinzufügen ---
with left_col:
    st.subheader("👤 Mandantenverwaltung")
    new_mandant = st.text_input("Neuen Mandanten anlegen")
    if st.button("Mandant hinzufügen"):
        if new_mandant and new_mandant not in st.session_state.mandanten:
            st.session_state.mandanten[new_mandant] = pd.DataFrame(
                columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
            )
            st.session_state.active_mandant = new_mandant
            st.success(f"Mandant '{new_mandant}' angelegt!")
        elif new_mandant:
            st.warning("Mandant existiert bereits!")

    # Mandant wählen
    if st.session_state.mandanten:
        mandant_list = list(st.session_state.mandanten.keys())
        st.session_state.active_mandant = st.selectbox("Mandant wählen", mandant_list, index=0)
    else:
        st.info("Bitte erst einen Mandanten anlegen.")

    # Aktie hinzufügen
    if st.session_state.active_mandant:
        st.subheader("➕ Aktie/ETF hinzufügen")
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
        price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
        stk_input = st.number_input("Stückzahl", min_value=1, step=1)
        stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01)
        take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01)
        status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
        fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

        if st.button("Hinzufügen", key="add_stock"):
            if ticker_input:
                portfolio = st.session_state.mandanten[st.session_state.active_mandant]
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
                portfolio = pd.concat([portfolio, new_row], ignore_index=True)
                st.session_state.mandanten[st.session_state.active_mandant] = portfolio
                st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
                st.experimental_rerun()
            else:
                st.warning("Bitte Ticker eingeben.")

# --- RECHTS: Portfolio + Chart ---
with right_col:
    if st.session_state.active_mandant:
        portfolio = st.session_state.mandanten[st.session_state.active_mandant]
        st.subheader("📋 Portfolio (Cards + Charts)")

        if portfolio.empty:
            st.info("Keine Aktien vorhanden.")
        else:
            # Preise abrufen
            tickers = portfolio["Ticker"].tolist()
            latest_prices = {}
            for t in tickers:
                try:
                    data = yf.download(t, period="5d", interval="1d", progress=False)
                    latest_prices[t] = data["Close"][-1] if not data.empty else None
                except:
                    latest_prices[t] = None
            portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda x: latest_prices.get(x, None))

            # Positionswert + Gewinn/Verlust
            def compute_values(row):
                price = row["Aktueller Preis"]
                positionswert = row["Stückzahl"] * price if price else 0
                gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
                return pd.Series([positionswert, gewinn])
            portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

            # Stop-Loss Empfehlung
            def stop_loss_volatility(row):
                try:
                    data = yf.Ticker(row["Ticker"]).history(period="1mo")
                    if not data.empty:
                        returns = data["Close"].pct_change().dropna()
                        volatility = returns.std()
                        return max(row["Kaufpreis"] * (1 - volatility), 0)
                    else:
                        return row["Kaufpreis"] * 0.95
                except:
                    return row["Kaufpreis"] * 0.95
            portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

            # Anzeige + Chart
            for idx, row in portfolio.iterrows():
                color = "#34C759" if row["Gewinn/Verlust"] >= 0 else "#FF3B30"
                card_cols = st.columns([1,2])

                # Card
                with card_cols[0]:
                    st.markdown(f"""
                    <div style="
                        border-radius:12px; 
                        padding:15px; 
                        margin-bottom:15px; 
                        background-color:#FFFFFF;
                        color:#000000;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
                    ">
                        <b style='font-size:18px'>{row['Ticker']}</b><br>
                        Status: {row['Status']}<br>
                        Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                        Positionswert: {row['Positionswert']:.2f} €<br>
                        <span style='color:{color}; font-weight:bold;'>Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €</span><br>
                        📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                        ⚠️ Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
                        Gebühr: {row['Gebühr']:.2f} € (pro Order)<br><br>
                        <button onclick="window.location.reload();">Löschen</button>
                    </div>
                    """, unsafe_allow_html=True)

                # Chart
                with card_cols[1]:
                    st.markdown("**Aktienverlauf**")
                    timeframe = st.selectbox(f"Zeitraum für {row['Ticker']}", ["1T","1W","1M","1J","Max"], key=f"time_{row['ID']}")
                    period_map = {"1T":"7d","1W":"1mo","1M":"3mo","1J":"1y","Max":"max"}
                    interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","Max":"1wk"}

                    try:
                        data_hist = yf.download(row["Ticker"], period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
                        if not data_hist.empty:
                            data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                            data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                            df_chart = data_hist.reset_index()
                            base = alt.Chart(df_chart).encode(x="Date:T")
                            layers = [base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"])]
                            layers.append(base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]))
                            layers.append(base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"]))
                            chart = alt.layer(*layers).resolve_scale(y="shared").properties(height=300)
                            st.altair_chart(chart, use_container_width=True)
                            st.markdown("<b>Legende:</b> Blau = Close, Orange = SMA20, Grün = SMA50", unsafe_allow_html=True)
                        else:
                            st.error("Chart konnte nicht geladen werden.")
                    except:
                        st.error("Fehler beim Laden des Charts.")
