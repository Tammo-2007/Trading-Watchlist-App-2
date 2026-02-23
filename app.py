import streamlit as st
import yfinance as yf
import pandas as pd
import uuid

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
    )

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

# --- Funktion: Sichere Preisabfrage ---
def get_latest_prices_safe(tickers):
    latest = {}
    for t in tickers:
        try:
            data = yf.download(t, period="5d", interval="1d", progress=False)["Close"]
            if not data.empty:
                latest[t] = data[-1]
            else:
                latest[t] = 0.0
        except:
            latest[t] = 0.0
    return pd.Series(latest)

# --- 1️⃣ Portfolio Tab (Cards) ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")

    df = st.session_state.portfolio.copy()
    df["Aktueller Preis"] = df["Ticker"].map(get_latest_prices_safe(df["Ticker"].unique()))
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])

    def pnl_color(val):
        if val > 0:
            return "#4caf50"  # grün
        elif val < 0:
            return "#ff4d4d"  # rot
        else:
            return "#2196f3"  # blau

    cols_per_row = 3
    for i in range(0, len(df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, row in df.iloc[i:i+cols_per_row].iterrows():
            with cols[j % cols_per_row]:
                # Markierung bei fehlenden Kursen
                price_display = f"{row['Aktueller Preis']:.2f} €" if row['Aktueller Preis'] > 0 else "Kein Kurs"
                st.markdown(
                    f"""
                    <div style="border-radius:10px; padding:15px; background-color:#f0f2f6; box-shadow: 2px 2px 6px rgba(0,0,0,0.1);">
                        <h3>{row['Ticker']}</h3>
                        <p>Status: <b>{row['Status']}</b></p>
                        <p>Aktueller Preis: <b>{price_display}</b></p>
                        <p>Positionswert: <b>{row['Positionswert']:.2f} €</b></p>
                        <p style="color:{pnl_color(row['Gewinn/Verlust'])}">Gewinn/Verlust: <b>{row['Gewinn/Verlust']:.2f} €</b></p>
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
    selected_ticker = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"].unique()))
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

                import altair as alt
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
