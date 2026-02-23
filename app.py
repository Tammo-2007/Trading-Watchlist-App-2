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
    st.session_state.mandanten = {}  # dict: mandantenname -> portfolio DataFrame
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

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

    # --- Mandant wählen ---
    if st.session_state.mandanten:
        mandant_list = list(st.session_state.mandanten.keys())
        st.session_state.active_mandant = st.selectbox("Mandant wählen", mandant_list, index=0)
    else:
        st.warning("Bitte erst einen Mandanten anlegen.")

    # --- Aktie/ETF hinzufügen ---
    st.subheader("➕ Aktie/ETF hinzufügen")
    ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = st.number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
    fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

    if st.button("Hinzufügen") and st.session_state.active_mandant:
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

# --- Portfolio-Funktionen ---
def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()

def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

# --- Portfolio-Berechnungen ---
if not portfolio.empty:
    # Aktuelle Kurse abrufen
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
        positionswert = row["Stückzahl"]*price - row["Gebühr"] if price is not None else 0
        gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
        return pd.Series([positionswert, gewinn])
    portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

    # Analysten-Rating & Target Price
    def get_analyst_info(ticker):
        try:
            info = yf.Ticker(ticker).info
            rating = info.get("recommendationKey", "neutral").capitalize()
            target = info.get("targetMeanPrice", None)
            return rating, target
        except:
            return "Neutral", None

    for idx, row in portfolio.iterrows():
        rating, target = get_analyst_info(row["Ticker"])
        portfolio.at[idx, "Analysten-Rating"] = rating
        portfolio.at[idx, "Target Price"] = target

        # Ampel-Logik
        price = row["Aktueller Preis"]
        if target and price:
            if price < target*0.95 and rating.lower() == "buy":
                portfolio.at[idx, "Ampel"] = "🟢"
            elif rating.lower() == "hold":
                portfolio.at[idx, "Ampel"] = "🟡"
            else:
                portfolio.at[idx, "Ampel"] = "🔴"
        else:
            portfolio.at[idx, "Ampel"] = "🟡"

# --- Layout: Zwei Spalten ---
col1, col2 = st.columns([1,3])

with col2:
    st.subheader("📋 Portfolio + Charts")
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        # Portfolio Cards
        for _, row in portfolio.iterrows():
            st.markdown(f"""
            <div style="border:1px solid #ccc; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f7f7f7;">
            <b>{row['Ticker']} {row['Ampel']}</b><br>
            Status: {row['Status']}<br>
            Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
            Positionswert: {row['Positionswert']:.2f} €<br>
            Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
            📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
            ⚠️ Analysten-Rating: {row['Analysten-Rating']} | Target: {row['Target Price']} €
            Gebühr: {row['Gebühr']} € (pro Order)
            </div>
            """, unsafe_allow_html=True)

        # Erwartetes Portfolio-Hoch
        expected_high = sum([row["Target Price"]*row["Stückzahl"] if row["Target Price"] else 0 for _, row in portfolio.iterrows()])
        st.subheader(f"Erwartetes Portfolio-Hoch: {expected_high:.2f} €")

        # Aktie auswählen für Chart
        selected_ticker = st.selectbox("Chart anzeigen für", [""] + portfolio["Ticker"].unique().tolist())
        timeframe = st.selectbox("Zeitraum", ["1T","1W","1M","1J","Max"])
        if selected_ticker:
            period_map = {"1T":"7d","1W":"6mo","1M":"2y","1J":"5y","Max":"max"}
            interval_map = {"1T":"15m","1W":"1d","1M":"1d","1J":"1wk","Max":"1mo"}
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
