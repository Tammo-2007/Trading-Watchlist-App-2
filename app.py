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

st.sidebar.subheader("👤 Mandantenverwaltung")
new_mandant = st.sidebar.text_input("Neuen Mandanten anlegen")
if st.sidebar.button("Mandant hinzufügen") and new_mandant:
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
    st.session_state.active_mandant = st.sidebar.selectbox("Mandant wählen", mandant_list, index=0)
else:
    st.warning("Bitte erst einen Mandanten anlegen.")

# --- Portfolio für aktiven Mandanten ---
def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()

def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie/ETF hinzufügen", "📈 Charts & Sparplan"])

# --- 1️⃣ Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
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

        # Positionswert und Gewinn/Verlust
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"] * price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung basierend auf Volatilität
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

        # Anzeige als Cards (flackerfrei, dunkler Hintergrund, schwarze Schrift)
        for _, row in portfolio.iterrows():
            if row["Gewinn/Verlust"] > 0:
                color = "🟢"
            elif row["Gewinn/Verlust"] == 0:
                color = "🟡"
            else:
                color = "🔴"

            st.markdown(f"""
            <div style="
                border:1px solid #ccc;
                padding:15px;
                border-radius:10px;
                margin-bottom:10px;
                background-color:#e0e0e0;
                color:#000000;
                font-weight:bold;
                ">
                {row['Ticker']} {color}<br>
                Status: {row['Status']}<br>
                Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                Positionswert: {row['Positionswert']:.2f} €<br>
                Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
                📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €
            </div>
            """, unsafe_allow_html=True)

        # Aktien löschen
        delete_options = portfolio[["ID","Ticker"]].apply(lambda x: f"{x['Ticker']} ({x['ID'][:6]})", axis=1).tolist()
        delete_choice = st.selectbox("Wähle Aktie zum Löschen", [""] + delete_options)
        if st.button("Löschen"):
            if delete_choice:
                selected_id = delete_choice.split("(")[-1].replace(")","")
                portfolio = portfolio[portfolio["ID"].str[:6] != selected_id]
                set_portfolio(portfolio)
                st.experimental_rerun()

# --- 2️⃣ Aktie/ETF hinzufügen Tab ---
with tab2:
    st.subheader("Neue Aktie/ETF hinzufügen")
    cols = st.columns([2,1,1,1,1,1])
    ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = cols[5].selectbox("Status", ["Besitzt","Beobachtung"])
    fee = st.number_input("Gebühr pro Aktie (€)", min_value=0.0, step=0.1, value=1.0)

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
            set_portfolio(portfolio)
            st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
            st.experimental_rerun()
        else:
            st.warning("Bitte Ticker eingeben.")

# --- 3️⃣ Charts & Sparplan Tab ---
with tab3:
    st.subheader("Charts & Sparplan")
    selected_ticker = st.selectbox("Ticker wählen", [""] + portfolio["Ticker"].unique().tolist())
    timeframe = st.selectbox("Zeitraum", ["1d","1wk","1mo","1y"])
    if selected_ticker:
        period_map = {"1d":"7d","1wk":"6mo","1mo":"2y","1y":"5y"}
        interval_map = {"1d":"15m","1wk":"1d","1mo":"1d","1y":"1wk"}
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
