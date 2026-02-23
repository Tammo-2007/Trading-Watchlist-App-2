import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import uuid

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State für Portfolio ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr","Aktueller Preis","Positionswert","Gewinn/Verlust"]
    )

# --- Demo-Daten einfügen, falls leer ---
if st.session_state.portfolio.empty:
    demo_data = [
        {"ID": str(uuid.uuid4()), "Ticker": "RHM.DE", "Kaufpreis": 50, "Stückzahl": 10,
         "Stop-Loss": 45, "Take-Profit": 60, "Status": "Besitzt", "Gebühr": 1.0,
         "Aktueller Preis": 0.0, "Positionswert": 0.0, "Gewinn/Verlust": 0.0},
        {"ID": str(uuid.uuid4()), "Ticker": "SAP.DE", "Kaufpreis": 120, "Stückzahl": 5,
         "Stop-Loss": 110, "Take-Profit": 140, "Status": "Beobachtung", "Gebühr": 1.0,
         "Aktueller Preis": 0.0, "Positionswert": 0.0, "Gewinn/Verlust": 0.0}
    ]
    st.session_state.portfolio = pd.DataFrame(demo_data)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie/ETF hinzufügen", "📈 Charts & Sparplan"])

# --- 1️⃣ Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")

    portfolio = st.session_state.portfolio
    cols_per_row = 2

    # --- Aktuelle Preise abrufen ---
    tickers = portfolio["Ticker"].tolist()
    latest_prices = {}
    if tickers:
        try:
            data = yf.download(tickers, period="5d", interval="1d", progress=False)["Close"]
            if isinstance(data, pd.Series):
                latest_prices[tickers[0]] = data.iloc[-1]
            else:
                latest_prices = data.iloc[-1].to_dict()
        except:
            latest_prices = {t: 0.0 for t in tickers}

    # Portfolio-Kennzahlen aktualisieren
    portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda t: latest_prices.get(t, 0.0))
    portfolio["Positionswert"] = portfolio["Aktueller Preis"] * portfolio["Stückzahl"] - portfolio["Gebühr"]
    portfolio["Gewinn/Verlust"] = portfolio["Positionswert"] - (portfolio["Kaufpreis"]*portfolio["Stückzahl"] + portfolio["Gebühr"])

    # --- Portfolio-Karten ---
    for i in range(0, len(portfolio), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(portfolio):
                row = portfolio.iloc[i+j]
                ticker = row["Ticker"]
                signal_color_emoji = "🟢" if row["Gewinn/Verlust"] >= 0 else "🔴"
                chart_color = "green" if row["Gewinn/Verlust"] >= 0 else "red"

                with col:
                    # Klickbare Karte
                    if st.button(f"{ticker} {signal_color_emoji}", key=f"btn_{ticker}"):
                        st.session_state.selected_ticker = ticker

                    # Kennzahlen
                    st.markdown(
                        f"**Status:** {row['Status']}  \n"
                        f"**Aktueller Preis:** {row['Aktueller Preis']:.2f} €  \n"
                        f"**Positionswert:** {row['Positionswert']:.2f} €  \n"
                        f"**Gewinn/Verlust:** {row['Gewinn/Verlust']:.2f} €  \n"
                        f"📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €"
                    )

                    # Mini-Chart mit Hover-Linien
                    try:
                        data_hist = yf.download(ticker, period="6mo", interval="1d", progress=False)
                        if not data_hist.empty:
                            data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                            data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                            df_chart = data_hist.reset_index()

                            base = alt.Chart(df_chart).encode(x="Date:T")
                            mini_chart = alt.layer(
                                base.mark_line(color=chart_color).encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                                base.mark_line(color="orange", strokeDash=[5,5]).encode(y="SMA20:Q"),
                                base.mark_line(color="blue", strokeDash=[2,2]).encode(y="SMA50:Q"),
                                # Stop-Loss Linie
                                alt.Chart(pd.DataFrame({'y':[row['Stop-Loss']]})).mark_rule(color='red', strokeDash=[2,2]).encode(
                                    y='y:Q', tooltip=alt.Tooltip('y:Q', title='Stop-Loss')),
                                # Take-Profit Linie
                                alt.Chart(pd.DataFrame({'y':[row['Take-Profit']]})).mark_rule(color='green', strokeDash=[2,2]).encode(
                                    y='y:Q', tooltip=alt.Tooltip('y:Q', title='Take-Profit'))
                            ).resolve_scale(y='shared').properties(height=150, width=300)
                            st.altair_chart(mini_chart, use_container_width=False)
                        else:
                            st.info("Kein Chart verfügbar")
                    except:
                        st.info("Fehler beim Laden des Charts")

                    st.markdown("---")

# --- 2️⃣ Aktie/ETF hinzufügen Tab ---
with tab2:
    st.subheader("Neue Aktie/ETF hinzufügen")
    cols = st.columns([2,1,1,1,1,1])
    ticker_input = cols[0].text_input("Ticker / ISIN / WKN").upper()
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
                "Gebühr": fee,
                "Aktueller Preis": 0.0,
                "Positionswert": 0.0,
                "Gewinn/Verlust": 0.0
            }])
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
            st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
        else:
            st.warning("Bitte Ticker / ISIN / WKN eingeben.")

# --- 3️⃣ Charts & Sparplan ---
with tab3:
    st.subheader("📈 Interaktiver Chart")
    selected_ticker = st.session_state.get("selected_ticker", "")
    ticker_list = [""] + portfolio["Ticker"].unique().tolist()
    selected_ticker = st.selectbox("Aktie/ETF wählen", ticker_list, index=ticker_list.index(selected_ticker) if selected_ticker in ticker_list else 0)
    if selected_ticker:
        data_hist = yf.download(selected_ticker, period="2y", interval="1d", progress=False)
        if not data_hist.empty:
            data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
            data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
            df_chart = data_hist.reset_index()
            row = portfolio[portfolio["Ticker"] == selected_ticker].iloc[0]
            chart_color = "green" if row["Gewinn/Verlust"] >= 0 else "red"

            base = alt.Chart(df_chart).encode(x="Date:T")
            chart = alt.layer(
                base.mark_line(color=chart_color).encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                base.mark_line(color="orange", strokeDash=[5,5]).encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                base.mark_line(color="blue", strokeDash=[2,2]).encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"]),
                alt.Chart(pd.DataFrame({'y':[row['Stop-Loss']]})).mark_rule(color='red', strokeDash=[2,2]).encode(
                    y='y:Q', tooltip=alt.Tooltip('y:Q', title='Stop-Loss')),
                alt.Chart(pd.DataFrame({'y':[row['Take-Profit']]})).mark_rule(color='green', strokeDash=[2,2]).encode(
                    y='y:Q', tooltip=alt.Tooltip('y:Q', title='Take-Profit'))
            ).interactive().resolve_scale(y='shared').properties(height=400, width=800)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Keine Daten für den großen Chart verfügbar")
