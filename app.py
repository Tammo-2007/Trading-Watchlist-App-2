import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import plotly.graph_objects as go

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

# Mandant wählen
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

# --- Aktie/ETF hinzufügen direkt unterhalb Mandanten ---
st.sidebar.subheader("➕ Aktie/ETF hinzufügen")
ticker_input = st.sidebar.text_input("Ticker (z.B. RHM.DE)").upper()
price_input = st.sidebar.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
stk_input = st.sidebar.number_input("Stückzahl", min_value=1, step=1)
stop_loss_input = st.sidebar.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
take_profit_input = st.sidebar.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
status_input = st.sidebar.selectbox("Status", ["Besitzt","Beobachtung"])
fee = st.sidebar.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

if st.sidebar.button("Hinzufügen"):
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

# --- Portfolio & Charts ---
if not portfolio.empty:
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

    # Anzeige Cards + Chart nebeneinander
    for _, row in portfolio.iterrows():
        color = "🟢" if row["Gewinn/Verlust"] >= 0 else "🔴"
        col1, col2 = st.columns([1,2])

        with col1:
            st.markdown(f"""
            <div style="border:1px solid #ccc; padding:15px; border-radius:10px; background-color:#f7f7f7; height:400px;">
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
            timeframe = st.selectbox(
                f"Zeitraum Chart {row['Ticker']}",
                ["1T", "1W", "1M", "1J", "Max"],
                index=2, key=f"tf_{row['Ticker']}"
            )

            period_map = {"1T":"7d","1W":"1mo","1M":"6mo","1J":"1y","Max":"max"}
            interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","Max":"1wk"}
            yf_period = period_map.get(timeframe, "6mo")
            yf_interval = interval_map.get(timeframe, "1d")

            try:
                data_hist = yf.download(row["Ticker"], period=yf_period, interval=yf_interval, progress=False)
                if not data_hist.empty:
                    data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                    data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()

                    fig = go.Figure()

                    fig.add_trace(go.Candlestick(
                        x=data_hist.index,
                        open=data_hist["Open"],
                        high=data_hist["High"],
                        low=data_hist["Low"],
                        close=data_hist["Close"],
                        name="Candlestick"
                    ))

                    fig.add_trace(go.Scatter(
                        x=data_hist.index,
                        y=data_hist["SMA20"],
                        line=dict(color='orange', width=2),
                        name='SMA20'
                    ))

                    fig.add_trace(go.Scatter(
                        x=data_hist.index,
                        y=data_hist["SMA50"],
                        line=dict(color='green', width=2),
                        name='SMA50'
                    ))

                    fig.update_layout(
                        height=400,
                        margin=dict(l=10,r=10,t=20,b=20),
                        xaxis_rangeslider_visible=False,
                        template="plotly_white",
                    )

                    st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning(f"Chart für {row['Ticker']} konnte nicht geladen werden.")

    # Aktien löschen
    delete_options = portfolio[["ID","Ticker"]].apply(lambda x: f"{x['Ticker']} ({x['ID'][:6]})", axis=1).tolist()
    delete_choice = st.selectbox("Wähle Aktie zum Löschen", [""] + delete_options)
    if st.button("Löschen"):
        if delete_choice:
            selected_id = delete_choice.split("(")[-1].replace(")","")
            portfolio = portfolio[portfolio["ID"].str[:6] != selected_id]
            set_portfolio(portfolio)
            st.experimental_rerun()
