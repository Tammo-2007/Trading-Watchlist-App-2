import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")
st.title("📊 Kompaktes Trading Dashboard Pro")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=["Ticker", "Kaufpreis", "Stückzahl", "Stop-Loss", "Take-Profit", "Status", "Gebühr"]
    )

# --- Kompaktes Eingabeformular ---
st.subheader("🔧 Aktie hinzufügen")
with st.expander("Formular öffnen", expanded=True):
    cols = st.columns([2, 1, 1, 1, 1, 1])
    ticker_input = cols[0].text_input("Ticker (z.B. RHM.DE)").upper()
    price_input = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stk_input = cols[2].number_input("Stückzahl", min_value=1, step=1)
    stop_loss_input = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01, format="%.2f")
    take_profit_input = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01, format="%.2f")
    status_input = cols[5].selectbox("Status", ["Besitzt", "Beobachtung"])
    fee = 1.00  # Kaufgebühr pro Aktie

    if st.button("Hinzufügen"):
        if ticker_input:
            new_row = pd.DataFrame([{
                "Ticker": ticker_input,
                "Kaufpreis": price_input,
                "Stückzahl": stk_input,
                "Stop-Loss": stop_loss_input,
                "Take-Profit": take_profit_input,
                "Status": status_input,
                "Gebühr": fee
            }])
            st.session_state.portfolio = pd.concat(
                [st.session_state.portfolio, new_row], ignore_index=True
            )
            st.success(f"Aktie {ticker_input} hinzugefügt!")
        else:
            st.warning("Bitte einen Ticker eingeben.")

# --- Portfolio ---
st.subheader("📋 Portfolio")
if st.session_state.portfolio.empty:
    st.info("Keine Aktien im Portfolio.")
else:
    df = st.session_state.portfolio.copy()

    # Aktuellen Preis abrufen
    def get_current_price(ticker):
        try:
            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            return data["Close"][-1] if not data.empty else 0
        except:
            return 0

    df["Aktueller Preis"] = df["Ticker"].apply(lambda t: get_current_price(t))
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"] * df["Stückzahl"] + df["Gebühr"])
    df["Signal"] = df["Gewinn/Verlust"].apply(lambda x: "Halten" if x >= 0 else "SELL")

    st.dataframe(df[["Ticker", "Aktueller Preis", "Positionswert", "Gewinn/Verlust", "Signal", "Status"]], height=250)

    # Kompakter Löschen-Bereich
    delete_col, _ = st.columns([1, 3])
    ticker_to_delete = delete_col.selectbox("Lösche Aktie", [""] + df["Ticker"].tolist())
    if delete_col.button("Löschen"):
        if ticker_to_delete:
            st.session_state.portfolio = df[df["Ticker"] != ticker_to_delete].reset_index(drop=True)
            st.success(f"Aktie {ticker_to_delete} gelöscht!")

# --- Kursverlauf mit SMA20 & SMA50 ---
st.subheader("📈 Kursverlauf")
selected_ticker = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"].unique()))
timeframe = st.selectbox("Zeitraum", ["1d", "1wk", "1mo", "1y"], help="1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")
st.caption("Abkürzungen: 1d = Tag, 1wk = Woche, 1mo = Monat, 1y = Jahr")

if selected_ticker:
    data_hist = yf.download(selected_ticker, period="1y", interval="1d", progress=False)
    if data_hist.empty:
        st.error("Chart konnte nicht geladen werden. Prüfe den Ticker.")
    else:
        data_hist["SMA20"] = data_hist["Close"].rolling(20).mean()
        data_hist["SMA50"] = data_hist["Close"].rolling(50).mean()
        data_hist_reset = data_hist.reset_index()

        base = alt.Chart(data_hist_reset).encode(
            x="Date:T"
        )

        close_line = base.mark_line(color="blue").encode(
            y="Close:Q",
            tooltip=["Date:T", "Close:Q"]
        )
        sma20_line = base.mark_line(color="orange").encode(
            y="SMA20:Q",
            tooltip=["Date:T", "SMA20:Q"]
        )
        sma50_line = base.mark_line(color="green").encode(
            y="SMA50:Q",
            tooltip=["Date:T", "SMA50:Q"]
        )

        chart = alt.layer(close_line, sma20_line, sma50_line).resolve_scale(
            y='shared'
        ).properties(height=350, width=700)

        st.altair_chart(chart, use_container_width=True)
        st.markdown("**Legende:** Blau = Close, Orange = SMA20, Grün = SMA50")

# --- RSS-News ---
st.subheader("📰 News")
try:
    import feedparser
    rss_url = "https://www.finanzen.net/rss/nachrichten"
    feed = feedparser.parse(rss_url)
    if feed.entries:
        for entry in feed.entries[:5]:
            date_str = datetime(*entry.published_parsed[:6]).strftime("%d.%m.%Y")
            st.markdown(f"- {date_str} | [{entry.title}]({entry.link})")
    else:
        st.info("Keine News gefunden.")
except ModuleNotFoundError:
    st.info("RSS-News Modul `feedparser` ist nicht installiert. News werden nicht angezeigt.")
