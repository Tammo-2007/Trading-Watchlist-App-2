import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# Optional: RSS-News
try:
    import feedparser
    rss_available = True
except ModuleNotFoundError:
    rss_available = False

st.set_page_config(page_title="Kompaktes Trading Dashboard Pro", layout="wide")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- Kompakte Eingabe ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
cols = st.columns([3,2,2,2])
ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)", help="Börsenkürzel der Aktie")
kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.0, step=0.01, format="%.2f", help="Preis pro Aktie beim Kauf")
stk = cols[2].number_input("Stückzahl", min_value=1, step=1, key="stk", help="Anzahl der gekauften Aktien")
status = cols[3].selectbox("Status", ["Besitzt", "Beobachtung"], help="Besitzt = im Depot, Beobachtung = Watchlist")

# Aktie hinzufügen
if st.button("Aktie hinzufügen"):
    if ticker_input.strip() == "":
        st.warning("Bitte einen Ticker eingeben!")
    else:
        st.session_state.portfolio.append({
            "Ticker": ticker_input.upper(),
            "Kaufpreis": kaufpreis,
            "Stückzahl": stk,
            "Status": status,
            "Gebühr": 1.0
        })
        st.success(f"Aktie {ticker_input.upper()} hinzugefügt!")
        st.experimental_rerun()

# --- Portfolio Anzeige ---
st.subheader("📋 Portfolio")
if len(st.session_state.portfolio) == 0:
    st.info("Noch keine Aktien im Portfolio.")
else:
    portfolio_df = pd.DataFrame(st.session_state.portfolio)
    
    # Aktueller Preis und Gewinn/Verlust abrufen
    current_prices = []
    positions = []
    profits = []
    signals = []
    for idx, row in portfolio_df.iterrows():
        ticker = row["Ticker"]
        try:
            data = yf.Ticker(ticker).history(period="1d")
            price = data["Close"][-1]
        except:
            price = None
        current_prices.append(price)
        
        if price is not None:
            pos_value = price * row["Stückzahl"]
            positions.append(pos_value)
            profit = pos_value - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            profits.append(profit)
            # Einfaches Signal: Gewinn positiv = HOLD, negativ = SELL
            signals.append("HOLD" if profit >= 0 else "SELL")
        else:
            positions.append(None)
            profits.append(None)
            signals.append("N/A")
    
    portfolio_df["Aktueller Preis"] = current_prices
    portfolio_df["Positionswert"] = positions
    portfolio_df["Gewinn/Verlust"] = profits
    portfolio_df["Signal"] = signals
    
    # Aktionen-Buttons
    for i, row in portfolio_df.iterrows():
        col1, col2 = st.columns([4,1])
        with col1:
            st.text(f"{row['Ticker']}: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'keine Daten'} € | {row['Signal']}")
        with col2:
            if st.button(f"Verkauf {row['Ticker']}", key=f"sell_{i}"):
                st.session_state.portfolio.pop(i)
                st.success(f"{row['Ticker']} verkauft!")
                st.experimental_rerun()
    
    st.dataframe(portfolio_df[["Ticker","Aktueller Preis","Positionswert","Gewinn/Verlust","Signal","Status"]], height=250)

# --- Chartanzeige für letzte ausgewählte Aktie ---
if len(st.session_state.portfolio) > 0:
    selected_ticker = st.session_state.portfolio[-1]["Ticker"]
    st.subheader(f"📈 Chart: {selected_ticker}")
    try:
        df = yf.download(selected_ticker, period="6mo", interval="1d")
        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x="Date",
            y="Close"
        ).properties(width=800, height=300)
        st.altair_chart(chart, use_container_width=False)  # Scrollfeste Größe
    except:
        st.warning(f"Für {selected_ticker} keine historischen Daten verfügbar.")

# --- RSS-News ---
if rss_available:
    st.subheader("📰 RSS-News")
    rss_url = f"https://finance.yahoo.com/rss/headline?s={selected_ticker}"
    feed = feedparser.parse(rss_url)
    for entry in feed.entries[:5]:
        st.markdown(f"- [{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar. Bitte installiere `feedparser`.")
