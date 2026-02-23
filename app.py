import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import numpy as np
import altair as alt

# --- Page Config ---
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

# --- Preis pro Ticker ---
def get_latest_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            return float(data["Close"].iloc[-1])
        return 0.0
    except:
        return 0.0

# --- Sparkline Mini-Chart ---
def get_sparkline_ascii(ticker, points=10):
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            series = data["Close"].tail(points).fillna(0).astype(float)
            # Normalisieren zwischen 0 und 1
            min_v, max_v = series.min(), series.max()
            if max_v - min_v == 0:
                return "─"*points
            normalized = ((series - min_v)/(max_v - min_v) * 7).round().astype(int)
            bars = "▁▂▃▄▅▆▇█"
            return "".join([bars[int(n)] for n in normalized])
        return "─"*points
    except:
        return "─"*points

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie hinzufügen", "📈 Kurs & Chart"])

# --- Portfolio Cards ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")
    df = st.session_state.portfolio.copy()
    if not df.empty:
        df["Aktueller Preis"] = df["Ticker"].apply(get_latest_price)
        cols_per_row = 4  # fixe Anzahl pro Reihe
        for i in range(0, len(df), cols_per_row):
            cols = st.columns(cols_per_row, gap="small")
            for j, row in df.iloc[i:i+cols_per_row].iterrows():
                with cols[j % cols_per_row]:
                    price = float(row['Aktueller Preis']) if pd.notnull(row['Aktueller Preis']) else 0.0
                    positionswert = row['Stückzahl']*price - row['Gebühr'] if price > 0 else 0
                    gewinn_verlust = positionswert - (row['Kaufpreis']*row['Stückzahl'] + row['Gebühr']) if price > 0 else 0
                    price_display = f"{price:.2f} €" if price > 0 else "Kein Kurs"

                    status_icon = "🟢" if row['Status']=="Besitzt" else "🟡"
                    pnl_color = "#0a7f0a" if gewinn_verlust > 0 else "#c40000" if gewinn_verlust < 0 else "#1a73e8"
                    spark_ascii = get_sparkline_ascii(row['Ticker'])

                    st.markdown(
                        f"""
                        <div style="border-radius:12px; padding:12px; margin-bottom:8px;
                                    background-color:#ffffff; box-shadow: 1px 1px 6px rgba(0,0,0,0.15);
                                    color:#222; font-size:13px; width:220px; min-height:180px;
                                    overflow:hidden; transition: transform 0.2s;">
                            <h4>{row['Ticker']} {status_icon}</h4>
                            <p>Status: <b>{row['Status']}</b></p>
                            <p>Aktueller Preis: <b>{price_display}</b></p>
                            <p>Positionswert: <b>{positionswert:.2f} €</b></p>
                            <p style="color:{pnl_color}; font-weight:bold;">Gewinn/Verlust: <b>{gewinn_verlust:.2f} €</b></p>
                            <p>📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €</p>
                            <p style="font-family: monospace; font-size:14px; color:#555;">{spark_ascii}</p>
                            <button onclick="window.dispatchEvent(new CustomEvent('open_chart', {{detail:'{row['Ticker']}'}}))">Chart</button>
                        </div>
                        <style>
                        div:hover {{
                            transform: scale(1.03);
                            box-shadow: 2px 2px 12px rgba(0,0,0,0.25);
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )

                    if st.button("Löschen", key=row["ID"]):
                        st.session_state.portfolio = df[df["ID"] != row["ID"]].reset_index(drop=True)
                        st.experimental_rerun()

# --- Chart Tab (Popup / Modal) ---
with tab3:
    st.subheader("Kursverlauf & SMA")
    selected_ticker = getattr(st.session_state, "selected_ticker", None)
    selected_ticker = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"].unique()), index=0 if not selected_ticker else list(st.session_state.portfolio["Ticker"].unique()).index(selected_ticker)+1)
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
            st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")
        else:
            st.error("Chart konnte nicht geladen werden.")
