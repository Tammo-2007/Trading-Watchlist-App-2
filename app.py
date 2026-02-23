import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State Initialisieren ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}  # Dictionary für Mandanten: {Name: Portfolio DataFrame}
if "aktueller_mandant" not in st.session_state:
    st.session_state.aktueller_mandant = None

# --- Mandantenverwaltung Sidebar ---
st.sidebar.header("👤 Mandantenverwaltung")
new_mandant = st.sidebar.text_input("Neuen Mandanten anlegen")
if st.sidebar.button("Mandant hinzufügen") and new_mandant:
    if new_mandant not in st.session_state.mandanten:
        st.session_state.mandanten[new_mandant] = pd.DataFrame(
            columns=["ID", "Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"]
        )
        st.session_state.aktueller_mandant = new_mandant
        st.sidebar.success(f"Mandant '{new_mandant}' hinzugefügt!")
    else:
        st.sidebar.warning("Mandant existiert bereits!")

# --- Mandanten wählen ---
if isinstance(st.session_state.mandanten, dict) and len(st.session_state.mandanten) > 0:
    mandanten_liste = list(st.session_state.mandanten.keys())
    index = 0 if st.session_state.aktueller_mandant is None else mandanten_liste.index(st.session_state.aktueller_mandant)
    st.session_state.aktueller_mandant = st.sidebar.selectbox("Mandant wählen", mandanten_liste, index=index)
else:
    st.info("Bitte zuerst einen Mandanten anlegen.")

# --- Tabs für Trading Dashboard ---
tab1, tab2, tab3 = st.tabs(["📋 Portfolio", "➕ Aktie/ETF hinzufügen", "📈 Charts & Sparplan"])

# --- Hilfsfunktion: aktuelle Kurse ---
def get_latest_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        return float(data["Close"][-1]) if not data.empty else None
    except:
        return None

# --- Portfolio Tab ---
with tab1:
    st.subheader("Dein Portfolio (Cards)")
    if st.session_state.aktueller_mandant:
        df = st.session_state.mandanten[st.session_state.aktueller_mandant].copy()

        if df.empty:
            st.info("Keine Aktien/ETFs vorhanden.")
        else:
            # Preise abrufen
            df["Aktueller Preis"] = df["Ticker"].apply(lambda t: get_latest_price(t) or 0.0)
            df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
            df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])

            # Signale
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

            # Portfolio als Cards anzeigen
            for _, row in df.iterrows():
                signal_emoji = "🟢" if row["Signal"]=="Halten" else "🟡" if row["Signal"]=="Take-Profit" else "🔴"
                st.markdown(f"""
                <div style="border:1px solid #ccc; padding:10px; border-radius:10px; margin-bottom:10px;">
                    <h3>{row['Ticker']} {signal_emoji}</h3>
                    <p>Status: {row['Status']}</p>
                    <p>Aktueller Preis: {row['Aktueller Preis']:.2f} €</p>
                    <p>Positionswert: {row['Positionswert']:.2f} €</p>
                    <p>Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €</p>
                    <p>📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €</p>
                </div>
                """, unsafe_allow_html=True)

            # Aktien löschen
            delete_options = df[["ID","Ticker"]].apply(lambda x: f"{x['Ticker']} ({x['ID'][:6]})", axis=1).tolist()
            delete_choice = st.selectbox("Wähle Aktie/ETF zum Löschen", [""] + delete_options)
            if st.button("Löschen"):
                if delete_choice:
                    selected_id = delete_choice.split("(")[-1].replace(")","")
                    st.session_state.mandanten[st.session_state.aktueller_mandant] = df[df["ID"] != selected_id].reset_index(drop=True)
                    st.success("Eintrag gelöscht!")

# --- Hinzufügen Tab ---
with tab2:
    st.subheader("Neue Aktie/ETF hinzufügen")
    cols = st.columns([2,1,1,1,1,1])
    ticker_input = cols[0].text_input("Ticker/ISIN/WKN").upper()
    price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
    stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
    take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
    status_input = cols[5].selectbox("Status", ["Besitzt","Beobachtung"])
    fee = st.number_input("Gebühr pro Aktie (€)", min_value=0.0, step=0.1, value=1.0)

    if st.button("Hinzufügen"):
        if ticker_input and st.session_state.aktueller_mandant:
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
            st.session_state.mandanten[st.session_state.aktueller_mandant] = pd.concat(
                [st.session_state.mandanten[st.session_state.aktueller_mandant], new_row], ignore_index=True
            )
            st.success(f"{ticker_input} hinzugefügt!")
        else:
            st.warning("Bitte Mandant auswählen und Ticker eingeben.")

# --- Charts Tab ---
with tab3:
    st.subheader("Charts & Sparplan")
    if st.session_state.aktueller_mandant:
        df_port = st.session_state.mandanten[st.session_state.aktueller_mandant]
        ticker_chart = st.selectbox("Ticker wählen", [""] + list(df_port["Ticker"].unique()))
        if ticker_chart:
            data_hist = yf.download(ticker_chart, period="1y", interval="1d", progress=False)
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
                st.markdown("**Legende:** Blau=Close, Orange=SMA20, Grün=SMA50")
            else:
                st.error("Chart konnte nicht geladen werden.")
