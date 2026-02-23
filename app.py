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

                # Farbcode Gewinn/Verlust – gut lesbar
                if gewinn_verlust > 0:
                    pnl_style = "color:#0a7f0a; animation: blinkGreen 1s infinite; font-weight:bold;"
                elif gewinn_verlust < 0:
                    pnl_style = "color:#c40000; animation: blinkRed 1s infinite; font-weight:bold;"
                else:
                    pnl_style = "color:#1a73e8; font-weight:bold;"

                st.markdown(
                    f"""
                    <style>
                    @keyframes blinkGreen {{ 50% {{opacity:0.5}} }}
                    @keyframes blinkRed {{ 50% {{opacity:0.5}} }}
                    .card:hover {{ transform: scale(1.03); transition: transform 0.2s; }}
                    .tooltip {{
                        position: relative;
                        display: inline-block;
                        border-bottom: 1px dotted black;
                        cursor: help;
                    }}
                    .tooltip .tooltiptext {{
                        visibility: hidden;
                        width: 120px;
                        background-color: #555;
                        color: #fff;
                        text-align: center;
                        border-radius: 6px;
                        padding: 5px;
                        position: absolute;
                        z-index: 1;
                        bottom: 125%;
                        left: 50%;
                        margin-left: -60px;
                        opacity: 0;
                        transition: opacity 0.3s;
                    }}
                    .tooltip:hover .tooltiptext {{
                        visibility: visible;
                        opacity: 1;
                    }}
                    </style>
                    <div class="card" style="border-radius:12px; padding:15px; background-color:#f0f2f6;
                                box-shadow: 2px 2px 8px rgba(0,0,0,0.15); cursor:pointer;">
                        <h3>{row['Ticker']} {status_icon}</h3>
                        <p>Status: <b>{row['Status']}</b></p>
                        <p>Aktueller Preis: <b>{price_display}</b></p>
                        <p>Positionswert: <b>{positionswert:.2f} €</b></p>
                        <p style="{pnl_style}">Gewinn/Verlust: <b>{gewinn_verlust:.2f} €</b></p>
                        <p>
                            <span class="tooltip">📉 Stop-Loss: {row['Stop-Loss']} €
                                <span class="tooltiptext">Limit bei dem verkauft wird</span>
                            </span> | 
                            <span class="tooltip">📈 Take-Profit: {row['Take-Profit']} €
                                <span class="tooltiptext">Limit bei dem Gewinn gesichert wird</span>
                            </span>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Card klickbar → Chart
                if st.button(f"Chart {row['ID']}", key=f"chart_{row['ID']}"):
                    st.session_state.selected_ticker = row["Ticker"]
                    st.experimental_rerun()

                # Löschen-Button
                if st.button("Löschen", key=row["ID"]):
                    st.session_state.portfolio = df[df["ID"] != row["ID"]].reset_index(drop=True)
                    st.experimental_rerun()
