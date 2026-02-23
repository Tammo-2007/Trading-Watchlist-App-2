import streamlit as st
import yfinance as yf
import pandas as pd
import uuid
import altair as alt

# --- Seite konfigurieren ---
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Trading Dashboard Pro</h1>", unsafe_allow_html=True)

# --- Mandantenverwaltung ---
if "mandanten" not in st.session_state:
    st.session_state.mandanten = {}
if "active_mandant" not in st.session_state:
    st.session_state.active_mandant = None

# Sidebar: Mandanten + Aktie/ETF hinzufügen
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

if st.session_state.mandanten:
    mandant_list = list(st.session_state.mandanten.keys())
    st.session_state.active_mandant = st.sidebar.selectbox(
        "Mandant wählen", mandant_list, index=mandant_list.index(st.session_state.active_mandant) if st.session_state.active_mandant else 0
    )
else:
    st.warning("Bitte erst einen Mandanten anlegen.")

# Aktie/ETF hinzufügen
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
    else:
        st.warning("Bitte Mandant auswählen und Ticker eingeben.")

# --- Portfolio für aktiven Mandanten ---
def get_portfolio():
    if st.session_state.active_mandant:
        return st.session_state.mandanten[st.session_state.active_mandant]
    return pd.DataFrame()

def set_portfolio(df):
    st.session_state.mandanten[st.session_state.active_mandant] = df

portfolio = get_portfolio()

# --- Portfolio anzeigen mit Chart neben jeder Aktie ---
st.subheader("Dein Portfolio")
if portfolio.empty:
    st.info("Keine Aktien vorhanden.")
else:
    # Aktuelle Preise
    portfolio["Aktueller Preis"] = portfolio["Ticker"].apply(
        lambda t: yf.Ticker(t).history(period="5d")["Close"][-1] if not yf.Ticker(t).history(period="5d").empty else None
    )

    def compute_values(row):
        price = row["Aktueller Preis"]
        positionswert = row["Stückzahl"]*price if price else 0
        gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
        return pd.Series([positionswert, gewinn])
    portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

    for _, row in portfolio.iterrows():
        st.markdown("---")
        st.markdown(f"### {row['Ticker']} ({'🟢' if row['Gewinn/Verlust']>=0 else '🔴'})")
        col1, col2 = st.columns([1,2])
        with col1:
            st.write(f"Status: {row['Status']}")
            st.write(f"Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else '-'} €")
            st.write(f"Positionswert: {row['Positionswert']:.2f} €")
            st.write(f"Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €")
            st.write(f"📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €")
            st.write(f"⚠️ Stop-Loss Empfehlung: {row['Kaufpreis']*0.95:.2f} €")
            st.write(f"Gebühr: {row['Gebühr']} € (pro Order)")
        with col2:
            # Zeitraum umschalten
            tf = st.selectbox(f"Zeitraum {row['Ticker']}", ["1T","1W","1M","1J","MAX"], key=row["ID"])
            period_map = {"1T":"7d","1W":"6mo","1M":"2y","1J":"5y","MAX":"max"}
            interval_map = {"1T":"15m","1W":"1d","1M":"1d","1J":"1wk","MAX":"1mo"}
            try:
                hist = yf.download(row["Ticker"], period=period_map[tf], interval=interval_map[tf], progress=False)
                if not hist.empty:
                    hist = hist.reset_index()
                    hist["SMA20"] = hist["Close"].rolling(20).mean()
                    hist["SMA50"] = hist["Close"].rolling(50).mean()

                    base = alt.Chart(hist).encode(x="Date:T")
                    chart = alt.layer(
                        base.mark_line(color="blue").encode(y="Close:Q", tooltip=["Date:T","Close:Q"]),
                        base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"]),
                        base.mark_line(color="green").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])
                    ).resolve_scale(y="shared").properties(height=250)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.write("Chart nicht verfügbar")
            except:
                st.write("Chart konnte nicht geladen werden")
