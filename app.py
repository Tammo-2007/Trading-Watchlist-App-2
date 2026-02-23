import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

st.set_page_config(layout="wide")

st.title("📊 Trading Dashboard Pro")

# ---------------------------
# SESSION INITIALISIERUNG
# ---------------------------

if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker",
        "Kaufpreis",
        "Stückzahl",
        "StopLoss",
        "TakeProfit",
        "Status"
    ])

portfolio = st.session_state.portfolio

# ---------------------------
# AKTIE HINZUFÜGEN
# ---------------------------

st.subheader("🔧 Aktie hinzufügen")

col1, col2, col3 = st.columns(3)

ticker = col1.text_input("Ticker (z.B. RHM.DE)").upper()
kaufpreis = col1.number_input("Kaufpreis €", min_value=1.0, step=0.01)
stueck = col2.number_input("Stückzahl", min_value=1)
stop = col2.number_input("Stop-Loss €", min_value=0.0, step=0.01)
take = col3.number_input("Take-Profit €", min_value=0.0, step=0.01)
status = col3.selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Hinzufügen"):

    if ticker == "":
        st.error("Ticker fehlt")
    else:
        new_row = pd.DataFrame([{
            "Ticker": ticker,
            "Kaufpreis": kaufpreis,
            "Stückzahl": stueck,
            "StopLoss": stop,
            "TakeProfit": take,
            "Status": status
        }])

        st.session_state.portfolio = pd.concat(
            [portfolio, new_row],
            ignore_index=True
        )

        st.success(f"{ticker} hinzugefügt")
        st.rerun()

# ---------------------------
# PORTFOLIO ANZEIGE + EDIT
# ---------------------------

st.subheader("📋 Portfolio")

if not portfolio.empty:

    edited_df = st.data_editor(
        portfolio,
        use_container_width=True,
        num_rows="dynamic"
    )

    st.session_state.portfolio = edited_df

    # Einzel löschen
    delete_col1, delete_col2 = st.columns([3,1])

    if delete_col2.button("⚠ Alles löschen"):
        st.session_state.portfolio = pd.DataFrame(columns=portfolio.columns)
        st.rerun()

    # ---------------------------
    # PERFORMANCE BERECHNUNG
    # ---------------------------

    total_value = 0
    total_invest = 0

    for i, row in edited_df.iterrows():
        try:
            live_price = yf.Ticker(row["Ticker"]).history(period="1d")["Close"].iloc[-1]
            position_value = live_price * row["Stückzahl"]
            invest = row["Kaufpreis"] * row["Stückzahl"]

            total_value += position_value
            total_invest += invest

        except:
            pass

    profit = total_value - total_invest
    perf = (profit / total_invest * 100) if total_invest > 0 else 0

    colA, colB, colC = st.columns(3)

    colA.metric("Depotwert", f"{total_value:,.2f} €")
    colB.metric("Investiert", f"{total_invest:,.2f} €")
    colC.metric("Gesamtgewinn", f"{profit:,.2f} €", f"{perf:.2f}%")

    # ---------------------------
    # CHART
    # ---------------------------

    st.subheader("📈 Kursverlauf")

    selected = st.selectbox("Aktie wählen", edited_df["Ticker"].unique())

    if selected:
        try:
            df_chart = yf.Ticker(selected).history(period="6mo")

            if not df_chart.empty:

                df_chart.reset_index(inplace=True)

                base = alt.Chart(df_chart).mark_line().encode(
                    x="Date:T",
                    y="Close:Q"
                )

                st.altair_chart(base, use_container_width=True)

            else:
                st.warning("Keine Kursdaten verfügbar.")

        except Exception as e:
            st.error("Chart konnte nicht geladen werden.")

else:
    st.info("Portfolio ist leer.")

# ---------------------------
# CSV EXPORT
# ---------------------------

st.subheader("💾 Export / Import")

col1, col2 = st.columns(2)

csv = st.session_state.portfolio.to_csv(index=False).encode("utf-8")

col1.download_button(
    "Portfolio exportieren",
    csv,
    "portfolio.csv",
    "text/csv"
)

uploaded_file = col2.file_uploader("Portfolio importieren", type=["csv"])

if uploaded_file:
    df_import = pd.read_csv(uploaded_file)
    st.session_state.portfolio = df_import
    st.success("Portfolio importiert")
    st.rerun()
