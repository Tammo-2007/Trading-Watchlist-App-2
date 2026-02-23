import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Session State initialisieren ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None
if "sidebar_visible" not in st.session_state:
    st.session_state.sidebar_visible = True  # Linke Spalte sichtbar

# --- Sidebar toggle ---
st.sidebar.button(
    "☰ Menü ein-/ausblenden", 
    on_click=lambda: st.session_state.update({"sidebar_visible": not st.session_state.sidebar_visible})
)

if st.session_state.sidebar_visible:
    # --- Mandantenverwaltung ---
    st.sidebar.subheader("👤 Mandantenverwaltung")
    new_mandant = st.sidebar.text_input("Neuen Mandanten anlegen")
    if st.sidebar.button("Mandant hinzufügen") and new_mandant:
        if new_mandant not in st.session_state.mandanten:
            st.session_state.mandanten[new_mandant] = pd.DataFrame(
                columns=["ID","Ticker","Kaufpreis","Stückzahl","Stop-Loss","Take-Profit","Status","Gebühr"]
            )
            st.session_state.active_mandant = new_mandant
            st.success(f"Mandant '{new_mandant}' angelegt!")
        else:
            st.warning("Mandant existiert bereits!")

    # --- Mandant wählen ---
    if st.session_state.mandanten:
        mandant_list = list(st.session_state.mandanten.keys())
        st.session_state.active_mandant = st.sidebar.selectbox("Mandant wählen", mandant_list, index=0)
    else:
        st.sidebar.warning("Bitte erst einen Mandanten anlegen.")

    # --- Aktie/ETF hinzufügen ---
    st.sidebar.subheader("➕ Aktie/ETF hinzufügen")
    ticker_input = st.sidebar.text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = st.sidebar.number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = st.sidebar.number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = st.sidebar.number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = st.sidebar.number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = st.sidebar.selectbox("Status", ["Besitzt","Beobachtung"])
    fee_input = st.sidebar.number_input("Gebühr pro Order (€)", min_value=0.0, step=0.1, value=1.0)

    if st.sidebar.button("Hinzufügen"):
        if ticker_input and st.session_state.active_mandant:
            portfolio = st.session_state.mandanten[st.session_state.active_mandant]
            new_row = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "Ticker": ticker_input,
                "Kaufpreis": price_input,
                "Stückzahl": stk_input,
                "Stop-Loss": stop_loss_input,
                "Take-Profit": take_profit_input,
                "Status": status_input,
                "Gebühr": fee_input
            }])
            portfolio = pd.concat([portfolio, new_row], ignore_index=True)
            st.session_state.mandanten[st.session_state.active_mandant] = portfolio
            st.success(f"Aktie/ETF {ticker_input} hinzugefügt!")
            st.experimental_rerun()

# --- Layout: linke Spalte optional, rechte Spalte für Portfolio + Charts ---
left_col, right_col = st.columns([1,3])

with right_col:
    st.subheader("📋 Portfolio + Charts")
    if st.session_state.active_mandant:
        portfolio = st.session_state.mandanten[st.session_state.active_mandant]
    else:
        portfolio = pd.DataFrame()

    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        # Preise abrufen
        tickers = portfolio["Ticker"].tolist()
        latest_prices = {t: yf.download(t, period="5d", interval="1d", progress=False)["Close"].iloc[-1] 
                         if not yf.download(t, period="5d", interval="1d", progress=False).empty else None
                         for t in tickers}
        portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda x: latest_prices.get(x, None))

        # Positionswert & Gewinn
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"]*price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_volatility(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                returns = data["Close"].pct_change().dropna()
                vol = returns.std() if not returns.empty else 0
                return max(row["Kaufpreis"]*(1-vol), 0)
            except:
                return row["Kaufpreis"]*0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # Karten + Chart
        for idx, row in portfolio.iterrows():
            color = "#34C759" if row["Gewinn/Verlust"] >= 0 else "#FF3B30"
            cols = st.columns([1,2])

            # Karte
            with cols[0]:
                st.markdown(f"""
                <div style='padding:10px;border-radius:12px;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.12);margin-bottom:15px'>
                    <b>{row['Ticker']}</b><br>
                    Status: {row['Status']}<br>
                    Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                    Positionswert: {row['Positionswert']:.2f} €<br>
                    <span style='color:{color};font-weight:bold'>Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €</span><br>
                    ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €
                </div>
                """, unsafe_allow_html=True)
                if st.button("🗑️ Löschen", key=f"del_{row['ID']}"):
                    portfolio = portfolio[portfolio["ID"] != row["ID"]]
                    st.session_state.mandanten[st.session_state.active_mandant] = portfolio
                    st.success(f"Aktie {row['Ticker']} gelöscht!")
                    st.experimental_rerun()

            # Chart
            with cols[1]:
                st.markdown("**Chart**")
                tf = st.selectbox(f"Zeitraum für {row['Ticker']}", ["1T","1W","1M","1J","Max"], key=f"tf_{row['ID']}")
                period_map = {"1T":"7d","1W":"1mo","1M":"3mo","1J":"1y","Max":"max"}
                interval_map = {"1T":"15m","1W":"1h","1M":"1d","1J":"1d","Max":"1wk"}

                data_hist = yf.download(row["Ticker"], period=period_map[tf], interval=interval_map[tf], progress=False)
                if not data_hist.empty:
                    data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
                    data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
                    df_chart = data_hist.reset_index()
                    base = alt.Chart(df_chart).encode(x="Date:T")
                    layers = [
                        base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                        base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                        base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                    ]
                    chart = alt.layer(*layers).resolve_scale(y="shared").properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                    st.markdown("<b>Legende:</b> Blau = Close, Orange = SMA20, Grün = SMA50", unsafe_allow_html=True)
                else:
                    st.error("Chart konnte nicht geladen werden.")
