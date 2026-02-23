import streamlit as st
import yfinance as yf
import pandas as pd
import uuid

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Mandantenverwaltung ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# Sidebar: Mandanten
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

# Mandant wählen
if st.session_state.mandanten:
    mandant_list = list(st.session_state.mandanten.keys())
    st.session_state.active_mandant = st.sidebar.selectbox(
        "Mandant wählen", mandant_list, index=mandant_list.index(st.session_state.active_mandant) if st.session_state.active_mandant else 0
    )
else:
    st.warning("Bitte erst einen Mandanten anlegen.")

# Aktie/ETF hinzufügen in Sidebar
st.sidebar.subheader("➕ Aktie/ETF hinzufügen")
ticker_input = st.sidebar.text_input("Ticker (z.B. RHM.DE)").upper()
price_input = st.sidebar.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
stk_input = st.sidebar.number_input("Stückzahl", min_value=1, step=1)
stop_loss_input = st.sidebar.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
take_profit_input = st.sidebar.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
status_input = st.sidebar.selectbox("Status", ["Besitzt","Beobachtung"])
fee_input = st.sidebar.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

if st.sidebar.button("Hinzufügen"):
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
        st.warning("Bitte Mandant auswählen und Ticker eingeben.")

# --- Portfolio für aktiven Mandanten ---
def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()

def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

# --- Tabs ---
tab1, tab2 = st.tabs(["📋 Portfolio", "📈 Charts & Sparplan"])

# --- Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        # Kurse abrufen
        def get_latest_price(ticker):
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if not data.empty:
                    return data["Close"][-1]
            except:
                pass
            return None

        portfolio["Aktueller Preis"] = portfolio["Ticker"].apply(get_latest_price)

        # Positionswert & Gewinn/Verlust
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"]*price if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung (basierend auf Volatilität)
        def stop_loss_volatility(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                if not data.empty:
                    vol = data["Close"].pct_change().std()
                    return max(row["Kaufpreis"]*(1-vol), 0)
            except:
                return row["Kaufpreis"]*0.95
            return row["Kaufpreis"]*0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # Anzeige als Cards
        for _, row in portfolio.iterrows():
            color = "🟢" if row["Gewinn/Verlust"] >= 0 else "🔴"
            st.markdown(f"""
            <div style="border:1px solid #ccc; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f0f0f0; color:#000;">
            <b>{row['Ticker']} {color}</b><br>
            Status: {row['Status']}<br>
            Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else '-'} €<br>
            Positionswert: {row['Positionswert']:.2f} €<br>
            Gewinn/Verlust: <span style="color:{'green' if row['Gewinn/Verlust']>=0 else 'red'}">{row['Gewinn/Verlust']:.2f} €</span><br>
            📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
            ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
            Gebühr: {row['Gebühr']} € (pro Order)
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

# --- Charts & Sparplan Tab ---
with tab2:
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
            st.line_chart(data_hist[["Close","SMA20","SMA50"]])
        else:
            st.error("Chart konnte nicht geladen werden.")
