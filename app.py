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
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = ""

# --- Demo-Aktien ---
if st.session_state.portfolio.empty:
    demo_data = [
        {"ID": str(uuid.uuid4()), "Ticker": "RHM.DE", "Kaufpreis": 50, "Stückzahl": 10,
         "Stop-Loss": 45, "Take-Profit": 60, "Status": "Besitzt", "Gebühr": 1.0},
        {"ID": str(uuid.uuid4()), "Ticker": "SAP.DE", "Kaufpreis": 120, "Stückzahl": 5,
         "Stop-Loss": 110, "Take-Profit": 140, "Status": "Beobachtung", "Gebühr": 1.0}
    ]
    st.session_state.portfolio = pd.DataFrame(demo_data)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie hinzufügen", "📈 Kurs & Chart"])

# --- Sichere Preisabfrage ---
def get_latest_prices_safe(tickers):
    latest = {}
    for t in tickers:
        try:
            data = yf.download(t, period="5d", interval="1d", progress=False)["Close"]
            latest[t] = data[-1] if not data.empty else 0.0
        except:
            latest[t] = 0.0
    return pd.Series(latest)

# --- 1️⃣ Portfolio Tab (Cards) ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")

    df = st.session_state.portfolio.copy()
    df["Aktueller Preis"] = df["Ticker"].map(get_latest_prices_safe(df["Ticker"].unique()))

    cols_per_row = 3
    for i in range(0, len(df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, row in df.iloc[i:i+cols_per_row].iterrows():
            with cols[j % cols_per_row]:
                price = row['Aktueller Preis']
                positionswert = row['Stückzahl']*price - row['Gebühr'] if price > 0 else 0
                gewinn_verlust = positionswert - (row['Kaufpreis']*row['Stückzahl'] + row['Gebühr']) if price > 0 else 0
                price_display = f"{price:.2f} €" if price > 0 else "Kein Kurs"

                status_icon = "🟢" if row['Status']=="Besitzt" else "🟡"

                if gewinn_verlust > 0:
                    pnl_style = "color:#4caf50; animation: blinkGreen 1s infinite;"
                elif gewinn_verlust < 0:
                    pnl_style = "color:#ff4d4d; animation: blinkRed 1s infinite;"
                else:
                    pnl_style = "color:#2196f3;"

                # Card mit Button für Click-to-Chart
                if st.button(f"{row['Ticker']} Card", key=f"card_{row['ID']}"):
                    st.session_state.selected_ticker = row["Ticker"]
                    st.experimental_rerun()

                st.markdown(
                    f"""
                    <style>
                    @keyframes blinkGreen {{ 50% {{opacity:0.5}} }}
                    @keyframes blinkRed {{ 50% {{opacity:0.5}} }}
                    .card:hover {{ transform: scale(1.03); transition: transform 0.2s; }}
                    </style>
                    <div class="card" style="border-radius:12px; padding:15px; background-color:#f0f2f6;
                                box-shadow: 2px 2px 8px rgba(0,0,0,0.15); cursor:pointer;">
                        <h3>{row['Ticker']} {status_icon}</h3>
                        <p>Status: <b>{row['Status']}</b></p>
                        <p>Aktueller Preis: <b>{price_display}</b></p>
                        <p>Positionswert: <b>{positionswert:.2f} €</b></p>
                        <p style="{pnl_style}">Gewinn/Verlust: <b>{gewinn_verlust:.2f} €</b></p>
                        <p>Stop-Loss: {row['Stop-Loss']} € | Take-Profit: {row['Take-Profit']} €</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("Löschen", key=row["ID"]):
                    st.session_state.portfolio = df[df["ID"] != row["ID"]].reset_index(drop=True)
                    st.experimental_rerun()

# --- 2️⃣ Aktie hinzufügen Tab ---
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
            st.success(f"Aktie {ticker_input} hinzugefügt!")
        else:
            st.warning("Bitte Ticker eingeben.")

# --- 3️⃣ Chart Tab ---
with tab3:
    st.subheader("Kursverlauf & SMA")
    selected_ticker = st.session_state.selected_ticker
    timeframe = st.selectbox("Zeitraum", ["1d","1wk","1mo","1y"])
    if selected_ticker:
        period_map = {"1d":"7d","1wk":"6mo","1mo":"2y","1y":"5y"}
        interval_map = {"1d":"15m","1wk":"1d","1mo":"1d","1y":"1wk"}
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
                st.warning(f"Keine Chart-Daten für {selected_ticker} verfügbar.")
        except Exception as e:
            st.error(f"Fehler beim Laden des Charts für {selected_ticker}: {e}")
