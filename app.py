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

    cols_per_row = 3
    for i in range(0, len(df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, row in df.iloc[i:i+cols_per_row].iterrows():
            with cols[j % cols_per_row]:
                price = row['Aktueller Preis']
                positionswert = row['Stückzahl']*price - row['Gebühr'] if price > 0 else 0
                gewinn_verlust = positionswert - (row['Kaufpreis']*row['Stückzahl'] + row['Gebühr']) if price > 0 else 0
                price_display = f"{price:.2f} €" if price > 0 else "Kein Kurs"

                # Status Icon
                status_icon = "🟢" if row['Status']=="Besitzt" else "🟡"

                # Farbcode für Gewinn/Verlust + Animation
                if gewinn_verlust > 0:
                    pnl_style = "color:#4caf50; animation: blinkGreen 1s infinite;"
                elif gewinn_verlust < 0:
                    pnl_style = "color:#ff4d4d; animation: blinkRed 1s infinite;"
                else:
                    pnl_style = "color:#2196f3;"

                st.markdown(
                    f"""
                    <style>
                    @keyframes blinkGreen {{ 50% {{opacity:0.5}} }}
                    @keyframes blinkRed {{ 50% {{opacity:0.5}} }}
                    .card:hover {{ transform: scale(1.03); transition: transform 0.2s; }}
                    </style>
                    <div class="card" style="border-radius:12px; padding:15px; background-color:#f0f2f6;
                                box-shadow: 2px 2px 8px rgba(0,0,0,0.15); cursor:pointer;"
                         onclick="window.location.href='#tab=2'">
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
