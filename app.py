import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import uuid
import altair as alt

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = pd.DataFrame(columns=["MandantID","Name"])
if "portfolios" not in st.session_state:
    st.session_state.portfolios = pd.DataFrame(columns=[
        "ID","MandantID","Topf","Ticker","Kaufpreis","Stückzahl",
        "Stop-Loss","Take-Profit","Status","Gebühr"
    ])

# --- Mandantenverwaltung ---
st.sidebar.header("👤 Mandantenverwaltung")
mandant_name = st.sidebar.text_input("Neuen Mandanten anlegen")
if st.sidebar.button("Mandant hinzufügen") and mandant_name:
    new_mandant = pd.DataFrame([{"MandantID": str(uuid.uuid4()), "Name": mandant_name}])
    st.session_state.mandanten = pd.concat([st.session_state.mandanten, new_mandant], ignore_index=True)
    st.sidebar.success(f"Mandant {mandant_name} hinzugefügt!")

# --- Mandant wählen ---
mandant_options = st.session_state.mandanten["Name"].tolist()
selected_mandant = st.selectbox("Mandant wählen", [""] + mandant_options)

if selected_mandant:
    mandant_id = st.session_state.mandanten.loc[
        st.session_state.mandanten["Name"]==selected_mandant, "MandantID"
    ].values[0]

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📋 Portfolio","➕ Aktie/ETF hinzufügen","📈 Charts & Sparplan"])

    # ================= Portfolio Tab =================
    with tab1:
        st.subheader(f"{selected_mandant} Portfolio (Cards)")
        df = st.session_state.portfolios[st.session_state.portfolios["MandantID"]==mandant_id].copy()

        if df.empty:
            st.info("Keine Aktien/ETFs im Portfolio.")
        else:
            # --- Aktuelle Preise abrufen ---
            tickers = df["Ticker"].unique().tolist()
            latest_prices = {}
            if tickers:
                try:
                    data = yf.download(tickers, period="5d", interval="1d", progress=False)["Close"]
                    if isinstance(data, pd.Series):
                        latest_prices[tickers[0]] = data.iloc[-1]
                    else:
                        latest_prices = data.iloc[-1].to_dict()
                except:
                    latest_prices = {t:0.0 for t in tickers}

            df["Aktueller Preis"] = df["Ticker"].map(lambda t: latest_prices.get(t,0.0))
            df["Positionswert"] = df["Aktueller Preis"]*df["Stückzahl"] - df["Gebühr"]
            df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"]*df["Stückzahl"] + df["Gebühr"])

            # --- Signale ---
            def compute_signal(row):
                if row["Aktueller Preis"] <= row["Stop-Loss"]:
                    return "SELL"
                elif row["Aktueller Preis"] >= row["Take-Profit"]:
                    return "Take-Profit"
                elif row["Gewinn/Verlust"] >= 0:
                    return "Halten"
                else:
                    return "SELL"
            df["Signal"] = df.apply(compute_signal, axis=1)

            # --- Portfolio als Cards ---
            for _, row in df.iterrows():
                signal_emoji = "🟢" if row["Signal"]=="Halten" else ("🟡" if row["Signal"]=="Take-Profit" else "🔴")
                st.markdown(f"""
                    **{row['Ticker']} {signal_emoji}**  
                    Status: {row['Status']}  
                    Aktueller Preis: {row['Aktueller Preis']:.2f} €  
                    Positionswert: {row['Positionswert']:.2f} €  
                    Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €  
                    📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €  
                    ──────────
                """)

            # --- Aktien löschen ---
            delete_options = df[["ID","Ticker"]].apply(lambda x: f"{x['Ticker']} ({x['ID'][:6]})", axis=1).tolist()
            delete_choice = st.selectbox("Wähle Aktie/ETF zum Löschen", [""] + delete_options)
            if st.button("Löschen"):
                if delete_choice:
                    selected_id = delete_choice.split("(")[-1].replace(")","")
                    st.session_state.portfolios = st.session_state.portfolios[df["ID"] != selected_id]
                    st.success("Aktie/ETF gelöscht!")

    # ================= Hinzufügen Tab =================
    with tab2:
        st.subheader("Neue Aktie/ETF hinzufügen")
        cols = st.columns([2,1,1,1,1,1])
        ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
        topf_input = st.selectbox("Topf wählen", ["Langfrist","Mittelfrist"])
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
                    "MandantID": mandant_id,
                    "Topf": topf_input,
                    "Ticker": ticker_input,
                    "Kaufpreis": price_input,
                    "Stückzahl": stk_input,
                    "Stop-Loss": stop_loss_input,
                    "Take-Profit": take_profit_input,
                    "Status": status_input,
                    "Gebühr": fee
                }])
                st.session_state.portfolios = pd.concat([st.session_state.portfolios, new_row], ignore_index=True)
                st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
            else:
                st.warning("Bitte Ticker eingeben.")

    # ================= Charts & Sparplan Tab =================
    with tab3:
        st.subheader("Charts & Sparplan")
        selected_ticker = st.selectbox("Ticker wählen", [""] + list(df["Ticker"].unique()))
        if selected_ticker:
            data_hist = yf.download(selected_ticker, period="2y", interval="1d", progress=False)
            if not data_hist.empty:
                data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                df_chart = data_hist.reset_index()
                for col in ["Close","SMA20","SMA50"]:
                    if col not in df_chart.columns:
                        df_chart[col] = np.nan

                # --- Altair Chart ---
                base = alt.Chart(df_chart).encode(x="Date:T")
                chart = alt.layer(
                    base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                    base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                    base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                ).resolve_scale(y="shared").properties(height=400)
                st.altair_chart(chart, use_container_width=True)

            # --- Sparplan Simulation ---
            st.subheader("Sparplan Simulation")
            monthly = st.number_input("Monatliche Rate (€)", 50, 5000, 250)
            years = st.slider("Laufzeit (Jahre)", 1, 40, 20)
            return_rate = st.number_input("Erwartete Rendite p.a. (%)", 0.0, 15.0, 7.0)/100

            def sparplan(monthly_rate, years, annual_return):
                months = years*12
                monthly_return = annual_return/12
                fv = monthly_rate * (((1 + monthly_return)**months - 1)/monthly_return)
                invested = monthly_rate*months
                gain = fv - invested
                return invested, fv, gain

            invested, fv, gain = sparplan(monthly, years, return_rate)
            st.metric("Investiert", f"{invested:,.0f} €")
            st.metric("Endwert", f"{fv:,.0f} €")
            st.metric("Gewinn", f"{gain:,.0f} €")
