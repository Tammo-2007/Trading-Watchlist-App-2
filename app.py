import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

# -----------------------
# Session-State Setup
# -----------------------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"]
    )

# -----------------------
# Kompakte Eingabemaske
# -----------------------
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1, 1, 1])  # kompakte Breite
ticker = cols[0].text_input("Ticker (z.B. RHM.DE)", key="ticker")
kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, key="price")
stk = cols[2].number_input("Stückzahl", min_value=1, step=1, key="stk")
stop_loss = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01, key="sl")
take_profit = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01, key="tp")
status = cols[5].selectbox("Status", ["Besitzt", "Beobachtung"], key="status")
gebühr = 1.0  # Kaufgebühr fest

if st.button("Aktie hinzufügen"):
    if ticker:
        new_row = pd.DataFrame([{
            "Ticker": ticker.upper(),
            "Kaufpreis": kaufpreis,
            "Stückzahl": stk,
            "Stop-Loss": stop_loss,
            "Take-Profit": take_profit,
            "Status": status,
            "Gebühr": gebühr
        }])
        st.session_state.portfolio = pd.concat(
            [st.session_state.portfolio, new_row], ignore_index=True
        )
        st.success(f"Aktie {ticker.upper()} hinzugefügt!")
        st.experimental_rerun()

# -----------------------
# Portfolio Tabelle
# -----------------------
st.subheader("📋 Portfolio")
if not st.session_state.portfolio.empty:
    df = st.session_state.portfolio.copy()
    
    # Aktueller Kurs & Gewinn/Verlust
    current_prices = {}
    positions_value = []
    profit_loss = []
    signals = []
    
    for i, row in df.iterrows():
        try:
            data = yf.download(row["Ticker"], period="1d", interval="1d")
            current_price = data["Close"][-1] if not data.empty else 0
        except:
            current_price = 0
        current_prices[row["Ticker"]] = current_price
        pos_val = current_price * row["Stückzahl"] - row["Gebühr"]
        positions_value.append(pos_val)
        pl = pos_val - (row["Kaufpreis"] * row["Stückzahl"] + row["Gebühr"])
        profit_loss.append(pl)
        signals.append("Halten" if pl >= 0 else "SELL")
    
    df["Aktueller Preis"] = df["Ticker"].map(current_prices)
    df["Positionswert"] = positions_value
    df["Gewinn/Verlust"] = profit_loss
    df["Signal"] = signals
    
    # Portfolio anzeigen mit Löschen-Button
    for i, row in df.iterrows():
        cols = st.columns([2, 1, 1, 1, 1, 1])
        cols[0].write(row["Ticker"])
        cols[1].write(f"{row['Aktueller Preis']:.2f} €")
        cols[2].write(f"{row['Positionswert']:.2f} €")
        pl_display = f"{row['Gewinn/Verlust']:.2f} €"
        if row['Gewinn/Verlust'] >= 0:
            cols[3].success(pl_display)
        else:
            cols[3].error(pl_display)
        cols[4].write(row["Signal"])
        if cols[5].button("❌", key=f"del_{i}"):
            st.session_state.portfolio.drop(i, inplace=True)
            st.session_state.portfolio.reset_index(drop=True, inplace=True)
            st.experimental_rerun()
else:
    st.info("Portfolio ist leer.")

# -----------------------
# Kursverlauf Chart
# -----------------------
st.subheader("📈 Kursverlauf")
aktie = st.selectbox("Aktie wählen", st.session_state.portfolio["Ticker"] if not st.session_state.portfolio.empty else [""])
zeitraum = st.selectbox("Zeitraum", ["1d", "1wk", "1mo", "1y"])
st.caption("Abkürzungen: 1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")

if aktie:
    try:
        hist = yf.download(aktie, period=zeitraum, interval="1d")
        hist.reset_index(inplace=True)
        hist["SMA20"] = hist["Close"].rolling(20).mean()
        hist["SMA50"] = hist["Close"].rolling(50).mean()
        
        base = alt.Chart(hist).encode(x="Date:T")
        close_line = base.mark_line(color="blue").encode(y="Close", tooltip=["Date", "Close"])
        sma20_line = base.mark_line(color="orange").encode(y="SMA20", tooltip=["Date", "SMA20"])
        sma50_line = base.mark_line(color="green").encode(y="SMA50", tooltip=["Date", "SMA50"])
        
        chart = alt.layer(close_line, sma20_line, sma50_line).interactive()
        st.altair_chart(chart, use_container_width=True)
    except:
        st.error("Chart konnte nicht geladen werden.")

# -----------------------
# RSS News (optional)
# -----------------------
# import feedparser
# st.subheader("📰 News")
# feed_url = "https://www.finanzen.net/rss/aktien"
# feed = feedparser.parse(feed_url)
# for entry in feed.entries[:5]:
#     st.markdown(f"- [{entry.title}]({entry.link})")
