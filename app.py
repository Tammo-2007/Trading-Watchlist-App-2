import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Page Config ---
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

# --- Preis pro Ticker abrufen ---
def get_latest_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            return float(data["Close"].iloc[-1])
        else:
            return 0.0
    except:
        return 0.0

# --- Sparkline abrufen ---
def get_sparkline_data(ticker, points=10):
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if "Close" in data and not data.empty:
            series = data["Close"].tail(points).fillna(0).astype(float)
            return series
        else:
            return pd.Series([0]*points)
    except:
        return pd.Series([0]*points)

# --- 1️⃣ Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")

    df = st.session_state.portfolio.copy()
    if not df.empty:
        # --- Aktueller Preis ---
        df["Aktueller Preis"] = df["Ticker"].apply(get_latest_price)

        cols_per_row = 3
        for i in range(0, len(df), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, row in df.iloc[i:i+cols_per_row].iterrows():
                with cols[j % cols_per_row]:
                    price = float(row['Aktueller Preis']) if pd.notnull(row['Aktueller Preis']) else 0.0
                    positionswert = row['Stückzahl']*price - row['Gebühr'] if price > 0 else 0
                    gewinn_verlust = positionswert - (row['Kaufpreis']*row['Stückzahl'] + row['Gebühr']) if price > 0 else 0
                    price_display = f"{price:.2f} €" if price > 0 else "Kein Kurs"

                    status_icon = "🟢" if row['Status']=="Besitzt" else "🟡"

                    # Farbcode Gewinn/Verlust
                    if gewinn_verlust > 0:
                        pnl_style = "color:#0a7f0a; font-weight:bold;"
                        spark_color = "#0a7f0a"
                    elif gewinn_verlust < 0:
                        pnl_style = "color:#c40000; font-weight:bold;"
                        spark_color = "#c40000"
                    else:
                        pnl_style = "color:#1a73e8; font-weight:bold;"
                        spark_color = "#1a73e8"

                    # Sparkline Chart
                    spark_data = get_sparkline_data(row['Ticker'])
                    spark_data = spark_data.fillna(0).astype(float)
                    spark_sum = spark_data.sum()  # Float, keine Series

                    if len(spark_data) > 0 and spark_sum > 0:
                        spark_df = spark_data.reset_index()
                        spark_df.columns = ["index","Close"]
                        spark_chart = alt.Chart(spark_df).mark_line(color=spark_color, strokeWidth=2).encode(
                            x='index',
                            y='Close:Q'
                        ).properties(height=50, width=200)
                        st.altair_chart(spark_chart, use_container_width=True)
                    else:
                        st.markdown("<p style='color:#555;'>Keine Kursdaten</p>", unsafe_allow_html=True)

                    # Card HTML
                    st.markdown(
                        f"""
                        <div style="border-radius:12px; padding:15px; background-color:#f0f2f6;
                                    box-shadow: 2px 2px 8px rgba(0,0,0,0.15); cursor:pointer; color:#333;">
                            <h3>{row['Ticker']} {status_icon}</h3>
                            <p>Status: <b>{row['Status']}</b></p>
                            <p>Aktueller Preis: <b>{price_display}</b></p>
                            <p>Positionswert: <b>{positionswert:.2f} €</b></p>
                            <p style="{pnl_style}">Gewinn/Verlust: <b>{gewinn_verlust:.2f} €</b></p>
                            <p>📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Chart-Button → Chart-Tab
                    if st.button(f"Chart {row['ID']}", key=f"chart_{row['ID']}"):
                        st.session_state.selected_ticker = row["Ticker"]
                        st.experimental_rerun()

                    # Löschen
                    if st.button("Löschen", key=row["ID"]):
                        st.session_state.portfolio = df[df["ID"] != row["ID"]].reset_index(drop=True)
                        st.experimental_rerun()
