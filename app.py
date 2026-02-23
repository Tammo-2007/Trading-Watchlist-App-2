import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
    )

# --- Demo Data ---
if st.session_state.portfolio.empty:
    demo_data = [
        {"ID": str(uuid.uuid4()), "Ticker": "RHM.DE", "Kaufpreis": 50, "Stückzahl": 10,
         "Stop-Loss": 45, "Take-Profit": 60, "Status": "Besitzt", "Gebühr": 1.0},
        {"ID": str(uuid.uuid4()), "Ticker": "SAP.DE", "Kaufpreis": 120, "Stückzahl": 5,
         "Stop-Loss": 110, "Take-Profit": 140, "Status": "Beobachtung", "Gebühr": 1.0}
    ]
    st.session_state.portfolio = pd.DataFrame(demo_data)

# --- Funktionen ---
def get_latest_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            return float(data["Close"].iloc[-1])
        return 0.0
    except:
        return 0.0

def create_mini_chart(ticker):
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            df_plot = data.reset_index()[["Date", "Close"]]
            chart = alt.Chart(df_plot).mark_line(color="#1a73e8").encode(
                x=alt.X("Date:T"),
                y=alt.Y("Close:Q")
            ).properties(width=200, height=50)
            return chart
        return None
    except:
        return None

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie hinzufügen", "📈 Kurs & Chart"])

# ----------------- Portfolio Tab -----------------
with tab1:
    st.subheader("Dein Portfolio (Cards)")
    df = st.session_state.portfolio.copy()
    if not df.empty:
        df["Aktueller Preis"] = df["Ticker"].apply(get_latest_price)

        # Grid-Layout
        cols = st.columns(3)  # 3 Cards pro Reihe
        for idx, row in df.iterrows():
            col = cols[idx % 3]  # Wechselt die Spalte
            price = float(row['Aktueller Preis']) if pd.notnull(row['Aktueller Preis']) else 0.0
            positionswert = row['Stückzahl']*price - row['Gebühr'] if price > 0 else 0
            gewinn_verlust = positionswert - (row['Kaufpreis']*row['Stückzahl'] + row['Gebühr']) if price > 0 else 0
            price_display = f"{price:.2f} €" if price > 0 else "Kein Kurs"
            status_icon = "🟢" if row['Status']=="Besitzt" else "🟡"
            pnl_color = "#0a7f0a" if gewinn_verlust > 0 else "#c40000" if gewinn_verlust < 0 else "#1a73e8"

            with col:
                st.markdown(
                    f"""
                    <div style="border-radius:12px; padding:12px; margin-bottom:12px;
                                background-color:#f9f9f9; box-shadow: 1px 1px 6px rgba(0,0,0,0.15);
                                color:#222; font-size:13px; min-height:220px;">
                        <h4>{row['Ticker']} {status_icon}</h4>
                        <p>Status: <b>{row['Status']}</b></p>
                        <p>Aktueller Preis: <b>{price_display}</b></p>
                        <p>Positionswert: <b>{positionswert:.2f} €</b></p>
                        <p style="color:{pnl_color}; font-weight:bold;">Gewinn/Verlust: <b>{gewinn_verlust:.2f} €</b></p>
                        <p>📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €</p>
                    </div>
                    """, unsafe_allow_html=True
                )

                mini_chart = create_mini_chart(row['Ticker'])
                if mini_chart:
                    st.altair_chart(mini_chart, use_container_width=False)

                if st.button(f"Löschen: {row['Ticker']}", key=f"delete_{row['ID']}"):
                    st.session_state.portfolio = df[df["ID"] != row["ID"]].reset_index(drop=True)

# ----------------- Aktie hinzufügen Tab -----------------
with tab2:
    st.subheader("Neue Aktie hinzufügen")
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
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)

# ----------------- Kurs & Chart Tab -----------------
with tab3:
    st.subheader("Kursverlauf & SMA")
    selected_ticker = getattr(st.session_state, "selected_ticker", None)
    tickers_list = list(st.session_state.portfolio["Ticker"].unique())
    if selected_ticker not in tickers_list:
        selected_ticker = None

    selected_ticker = st.selectbox(
        "Aktie wählen",
        [""] + tickers_list,
        index=0 if not selected_ticker else tickers_list.index(selected_ticker)+1
    )

    if selected_ticker:
        data_hist = yf.download(selected_ticker, period="1y", interval="1d", progress=False)
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
        else:
            st.error("Chart konnte nicht geladen werden.")
