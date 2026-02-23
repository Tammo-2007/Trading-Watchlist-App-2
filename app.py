import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
import feedparser

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State Initialisierung ---
if "portfolio" not in st.session_state or not isinstance(st.session_state.portfolio, pd.DataFrame):
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr"
    ])

# --- Signaleinstellungen & Aktie hinzufügen ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([2, 1, 1, 1])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
buy_price = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01)
shares = cols[2].number_input("Stückzahl", min_value=1, step=1)
status = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"])

if st.button("Aktie hinzufügen") and ticker_input:
    fee = 1.0
    new_row = pd.DataFrame([{
        "Ticker": ticker_input,
        "Kaufpreis": buy_price,
        "Stückzahl": shares,
        "Status": status,
        "Gebühr": fee
    }])
    st.session_state.portfolio = pd.concat(
        [st.session_state.portfolio, new_row], ignore_index=True
    )
    st.success(f"Aktie {ticker_input} hinzugefügt!")

# --- Portfolio anzeigen ---
st.subheader("📋 Portfolio")
portfolio = st.session_state.portfolio.copy()

if not portfolio.empty:
    current_prices = []
    position_values = []
    profits = []
    signals = []

    for idx, row in portfolio.iterrows():
        try:
            data = yf.download(row["Ticker"], period="1d", interval="1d")
            current_price = data["Close"].iloc[-1]
        except:
            current_price = None

        current_prices.append(current_price)

        if current_price is not None:
            pos_value = current_price * row["Stückzahl"] - row["Gebühr"]
            profit = pos_value - (row["Kaufpreis"] * row["Stückzahl"])
            position_values.append(pos_value)
            profits.append(profit)
            signals.append("Halten" if profit >= 0 else "SELL")
        else:
            position_values.append(None)
            profits.append(None)
            signals.append("Keine Daten")

    portfolio["Aktueller Preis"] = current_prices
    portfolio["Positionswert"] = position_values
    portfolio["Gewinn/Verlust"] = profits
    portfolio["Signal"] = signals

    st.dataframe(portfolio[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]])
else:
    st.info("Portfolio ist leer. Füge zuerst eine Aktie hinzu.")

# --- Kursverlauf Chart ---
st.subheader("📈 Kursverlauf")
ticker_chart = st.selectbox("Wähle eine Aktie", portfolio["Ticker"] if not portfolio.empty else [])

if ticker_chart:
    df_chart = yf.download(ticker_chart, period="6mo", interval="1d")
    df_chart["SMA20"] = df_chart["Close"].rolling(20).mean()
    df_chart["SMA50"] = df_chart["Close"].rolling(50).mean()
    df_chart.reset_index(inplace=True)

    chart = alt.Chart(df_chart).transform_fold(
        ["Close", "SMA20", "SMA50"]
    ).mark_line().encode(
        x="Date:T",
        y="value:Q",
        color="key:N"
    ).properties(width=800, height=300)
    st.altair_chart(chart, use_container_width=True)

# --- RSS News ---
st.subheader("📰 RSS-News")
rss_url = st.text_input("RSS-Feed URL", value="https://www.finanzen.net/rss/news")
if rss_url:
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:
            st.write(f"**{entry.title}**")
            st.write(entry.link)
    except Exception as e:
        st.warning(f"RSS-News nicht verfügbar ({e})")
