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
    st.session_state.mandanten = {}  # dict: mandantenname -> portfolio DataFrame
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# --- Layout: Links Mandanten + Aktie hinzufügen, rechts Portfolio + Charts ---
left_col, right_col = st.columns([1,3])

# --- Linke Spalte ---
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
    ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = st.number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
    fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

    if st.button("Hinzufügen"):
        if ticker_input and st.session_state.active_mandant:
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
            st.warning("Bitte Ticker eingeben und Mandanten wählen.")

# --- Rechte Spalte ---
with right_col:
    st.subheader("📋 Portfolio + Charts")

    if st.session_state.active_mandant:
        portfolio = st.session_state.mandanten[st.session_state.active_mandant]

        if portfolio.empty:
            st.info("Keine Aktien vorhanden.")
        else:
            # Aktuelle Kurse abrufen
            for idx, row in portfolio.iterrows():
                try:
                    data = yf.download(row["Ticker"], period="5d", interval="1d", progress=False)
                    portfolio.at[idx,"Aktueller Preis"] = data["Close"][-1] if not data.empty else None
                except:
                    portfolio.at[idx,"Aktueller Preis"] = None

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
                    return max(row["Kaufpreis"]*(1-volatility),0)
                except:
                    return row["Kaufpreis"]*0.95
            portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

            # Anzeige Portfolio
            for _, row in portfolio.iterrows():
                gain_color = "#006400"
                loss_color = "#8B0000"
                ticker_color = "#000080"
                value_color = gain_color if row["Gewinn/Verlust"] >= 0 else loss_color
                st.markdown(f"""
                <div style="border:2px solid #555; padding:10px; border-radius:10px; margin-bottom:10px; background-color:#f0f0f0;">
                    <b style='color:{ticker_color}; font-size:18px'>{row['Ticker']}</b><br>
                    Status: <span style='color:black'>{row['Status']}</span><br>
                    Aktueller Preis: <span style='color:black'>{row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €</span><br>
                    Positionswert: <span style='color:black'>{row['Positionswert']:.2f} €</span><br>
                    Gewinn/Verlust: <span style='color:{value_color}; font-weight:bold'>{row['Gewinn/Verlust']:.2f} €</span><br>
                    📉 Stop-Loss: <span style='color:black'>{row['Stop-Loss']} €</span> | 📈 Take-Profit: <span style='color:black'>{row['Take-Profit']} €</span><br>
                    ⚠️ Stop-Loss Empfehlung: <span style='color:black'>{row['Stop-Loss-Empfehlung']:.2f} €</span><br>
                    Gebühr: <span style='color:black'>{row['Gebühr']} €</span> (pro Order)
                </div>
                """, unsafe_allow_html=True)

            # Charts
            st.subheader("📈 Chart")
            selected_ticker = st.selectbox("Chart anzeigen für", portfolio["Ticker"].unique())
            timeframe = st.selectbox("Zeitraum", ["1T","1W","1M","1J","Max"])

            period_map = {"1T":"7d","1W":"1mo","1M":"6mo","1J":"2y","Max":"5y"}
            interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","Max":"1wk"}

            try:
                data_hist = yf.download(selected_ticker, period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
                if not data_hist.empty:
                    data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                    data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                    df_chart = data_hist.reset_index()

                    base = alt.Chart(df_chart).encode(x="Date:T")
                    chart = alt.layer(
                        base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                        base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                        base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                    ).resolve_scale(y="shared").properties(height=400)
                    st.altair_chart(chart, use_container_width=True)
                    st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")
                else:
                    st.error("Chart konnte nicht geladen werden.")
            except Exception as e:
                st.error(f"Fehler beim Laden des Charts: {e}")
