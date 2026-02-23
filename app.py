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
if "sidebar_visible" not in st.session_state:
    st.session_state.sidebar_visible = True

# Sidebar ein-/ausblenden
st.sidebar.checkbox("🔹 Sidebar anzeigen", value=True, key="sidebar_visible")

if st.session_state.sidebar_visible:
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

        # Mandant wählen
        if st.session_state.mandanten:
            mandant_list = list(st.session_state.mandanten.keys())
            st.session_state.active_mandant = st.selectbox("Mandant wählen", mandant_list, index=0)
        else:
            st.warning("Bitte erst einen Mandanten anlegen.")

        # Neue Aktie/ETF hinzufügen
        st.subheader("➕ Aktie/ETF hinzufügen")
        ticker_input = st.text_input("Ticker (z.B. RHM.DE)").upper()
        price_input = st.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
        stk_input = st.number_input("Stückzahl", min_value=1, step=1)
        stop_loss_input = st.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
        take_profit_input = st.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
        status_input = st.selectbox("Status", ["Besitzt","Beobachtung"])
        fee_input = st.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

        if st.button("Hinzufügen") and st.session_state.active_mandant:
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

# --- Portfolio Funktionen ---
def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()

def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

# --- Tabs für Portfolio und Charts ---
tab1, tab2 = st.tabs(["📋 Portfolio + Charts", "📊 Portfolio Analyse"])

with tab1:
    st.subheader("Dein Portfolio")
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        tickers = portfolio["Ticker"].unique().tolist()

        @st.cache_data(ttl=300)
        def fetch_data(tickers):
            try:
                return yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)
            except:
                return pd.DataFrame()

        data_hist = fetch_data(tickers)

        # Portfolio aktualisieren mit Kursen, Stop-Loss Empfehlung
        def compute_values(row):
            price = None
            try:
                if len(tickers) == 1:
                    price = data_hist["Close"].iloc[-1]
                else:
                    price = data_hist[row["Ticker"]]["Close"].iloc[-1]
            except:
                price = None
            positionswert = row["Stückzahl"]*price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([price, positionswert, gewinn])

        portfolio[["Aktueller Preis","Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_volatility(row):
            try:
                if len(tickers) == 1:
                    df = data_hist
                else:
                    df = data_hist[row["Ticker"]]
                returns = df["Close"].pct_change().dropna()
                volatility = returns.std()
                return max(row["Kaufpreis"]*(1-volatility), 0)
            except:
                return row["Kaufpreis"]*0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # Anzeige Portfolio Cards
        for _, row in portfolio.iterrows():
            color = "#ffcc00" if row["Gewinn/Verlust"] >= 0 else "#ff4d4d"
            st.markdown(f"""
            <div style="border:1px solid #ccc; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f7f7f7;">
            <b style='color:{color}'>{row['Ticker']}</b><br>
            Status: {row['Status']}<br>
            Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
            Positionswert: {row['Positionswert']:.2f} €<br>
            Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
            📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
            ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
            Gebühr: {row['Gebühr']} € (pro Order)
            </div>
            """, unsafe_allow_html=True)

        # Chart für ausgewählte Aktie
        selected_ticker = st.selectbox("Chart anzeigen für", portfolio["Ticker"].unique())
        timeframe = st.selectbox("Zeitraum", ["1T","1W","1M","1J","MAX"])
        period_map = {"1T":"7d","1W":"1mo","1M":"6mo","1J":"2y","MAX":"5y"}
        interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","MAX":"1wk"}

        if selected_ticker:
            try:
                chart_data = yf.download(selected_ticker, period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
                chart_data["SMA20"] = chart_data["Close"].rolling(20).mean()
                chart_data["SMA50"] = chart_data["Close"].rolling(50).mean()
                df_chart = chart_data.reset_index()

                base = alt.Chart(df_chart).encode(x="Date:T")
                chart = alt.layer(
                    base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                    base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                    base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                ).resolve_scale(y="shared").properties(height=400)
                st.altair_chart(chart, use_container_width=True)
                st.markdown("<b>Legende:</b> Blau = Close, Orange = SMA20, Grün = SMA50", unsafe_allow_html=True)
            except:
                st.warning("Chart konnte nicht geladen werden.")

with tab2:
    st.subheader("Portfolio Analyse (Zukünftige Features)")
    st.info("Hier könnten später Kaufempfehlungen, Verkaufssignale und erwartetes Portfolio-Hoch angezeigt werden.")
