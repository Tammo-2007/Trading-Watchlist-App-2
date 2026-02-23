import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color:white;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)
st.markdown("<style>body {background-color: #0d1117; color: white;} </style>", unsafe_allow_html=True)

# --- Session State ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# --- Sidebar: Mandanten & Aktie hinzufügen ---
st.sidebar.markdown("<h3 style='color:white;'>👤 Mandantenverwaltung</h3>", unsafe_allow_html=True)
new_mandant = st.sidebar.text_input("Neuen Mandanten anlegen")
if st.sidebar.button("Mandant hinzufügen") and new_mandant:
    if new_mandant not in st.session_state.mandanten:
        st.session_state.mandanten[new_mandant] = pd.DataFrame(columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"])
        st.session_state.active_mandant = new_mandant
        st.success(f"Mandant '{new_mandant}' angelegt!")
    else:
        st.warning("Mandant existiert bereits!")

if st.session_state.mandanten:
    mandant_list = list(st.session_state.mandanten.keys())
    st.session_state.active_mandant = st.sidebar.selectbox("Mandant wählen", mandant_list,
                                                           index=mandant_list.index(st.session_state.active_mandant)
                                                           if st.session_state.active_mandant in mandant_list else 0)
else:
    st.sidebar.warning("Bitte erst einen Mandanten anlegen.")

# --- Aktie/ETF hinzufügen ---
st.sidebar.markdown("<h3 style='color:white;'>➕ Aktie/ETF hinzufügen</h3>", unsafe_allow_html=True)
ticker_input = st.sidebar.text_input("Ticker (z.B. RHM.DE)").upper()
price_input = st.sidebar.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
stk_input = st.sidebar.number_input("Stückzahl", min_value=1, step=1)
stop_loss_input = st.sidebar.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
take_profit_input = st.sidebar.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
status_input = st.sidebar.selectbox("Status", ["Besitzt","Beobachtung"])
fee_input = st.sidebar.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()
def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

if st.sidebar.button("Hinzufügen"):
    if ticker_input:
        new_row = pd.DataFrame([{"ID":str(uuid.uuid4()),"Ticker":ticker_input,"Kaufpreis":price_input,
                                 "Stückzahl":stk_input,"Stop-Loss":stop_loss_input,"Take-Profit":take_profit_input,
                                 "Status":status_input,"Gebühr":fee_input}])
        portfolio = pd.concat([portfolio,new_row], ignore_index=True)
        set_portfolio(portfolio)
        st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
        st.experimental_rerun()
    else:
        st.sidebar.warning("Bitte Ticker eingeben.")

# --- Layout: Links Portfolio, rechts Chart ---
left_col, right_col = st.columns([1,2])

with left_col:
    st.subheader("Portfolio (TR-Style)")
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

        # Positionswert & Gewinn
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"]*price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_vol(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                returns = data["Close"].pct_change().dropna()
                vol = returns.std()
                return max(row["Kaufpreis"]*(1-vol),0) if not data.empty else row["Kaufpreis"]*0.95
            except:
                return row["Kaufpreis"]*0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_vol, axis=1)

        # Scrollbar für Portfolio
        with st.container():
            for _, row in portfolio.iterrows():
                color = "#4caf50" if row["Gewinn/Verlust"]>=0 else "#f44336"
                st.markdown(f"""
                <div style="background-color:#161b22; padding:15px; border-radius:10px; margin-bottom:10px;">
                <b style='color:white'>{row['Ticker']}</b> <span style='color:{color}'>●</span><br>
                Status: <span style='color:white'>{row['Status']}</span><br>
                Aktueller Preis: <span style='color:white'>{row['Aktueller Preis'] if row['Aktueller Preis'] else '–'} €</span><br>
                Positionswert: <span style='color:white'>{row['Positionswert']:.2f} €</span><br>
                Gewinn/Verlust: <span style='color:{color}'>{row['Gewinn/Verlust']:.2f} €</span><br>
                📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                ⚠️ Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
                Gebühr: {row['Gebühr']} € (pro Order)
                </div>
                """, unsafe_allow_html=True)

with right_col:
    st.subheader("Aktien-Chart")
    if not portfolio.empty:
        selected_ticker = st.selectbox("Ticker für Chart", [""] + portfolio["Ticker"].tolist())
        timeframe = st.selectbox("Zeitraum", ["1T","1W","1M","1J","MAX"])
        if selected_ticker:
            period_map = {"1T":"7d","1W":"6mo","1M":"2y","1J":"5y","MAX":"10y"}
            interval_map = {"1T":"15m","1W":"1d","1M":"1d","1J":"1wk","MAX":"1mo"}
            df_hist = yf.download(selected_ticker, period=period_map[timeframe], interval=interval_map[timeframe], progress=False)
            if not df_hist.empty:
                df_hist["SMA20"]=df_hist["Close"].rolling(20).mean()
                df_hist["SMA50"]=df_hist["Close"].rolling(50).mean()
                df_chart=df_hist.reset_index()
                base=alt.Chart(df_chart).encode(x="Date:T")
                chart=alt.layer(
                    base.mark_line(color="#1f77b4").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                    base.mark_line(color="#ff7f0e").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                    base.mark_line(color="#2ca02c").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                ).resolve_scale(y="shared").properties(height=500).configure_view(strokeOpacity=0)
                st.altair_chart(chart, use_container_width=True)
