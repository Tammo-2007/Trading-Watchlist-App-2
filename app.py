import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt

# RSS optional
try:
    import feedparser
    rss_available = True
except ModuleNotFoundError:
    rss_available = False

st.set_page_config(page_title="Trading Dashboard Pro", layout="wide")

# --- Session State initialisieren ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        "Ticker", "Kaufpreis", "Stückzahl", "Status", "Gebühr", "Stop-Loss", "Take-Profit"
    ])

# --- Kompakte Eingabe oben ---
st.subheader("🔧 Signaleinstellungen & Aktie hinzufügen")
with st.container():
    cols = st.columns([2,1,1,1,1,1,1])
    ticker = cols[0].text_input("Ticker (z.B. RHM.DE)")
    kaufpreis = cols[1].number_input("Kaufpreis (€)", min_value=0.01, step=0.01, format="%.2f")
    stueckzahl = cols[2].number_input("Stückzahl", min_value=1, step=1)
    stop_loss = cols[3].number_input("Stop-Loss €", min_value=0.0, step=0.01)
    take_profit = cols[4].number_input("Take-Profit €", min_value=0.0, step=0.01)
    status = cols[5].radio("Status", ["Besitzt", "Beobachtung"], horizontal=True)
    add_btn = cols[6].button("Aktie hinzufügen")

# --- Hinzufügen sicher ohne sofortigen rerun ---
if add_btn and ticker:
    gebuehr = 1.0
    new_row = pd.DataFrame([{
        "Ticker": ticker.upper(),
        "Kaufpreis": kaufpreis,
        "Stückzahl": stueckzahl,
        "Status": status,
        "Gebühr": gebuehr,
        "Stop-Loss": stop_loss,
        "Take-Profit": take_profit
    }])
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
    st.success(f"Aktie {ticker.upper()} hinzugefügt!")

# --- Portfolio ---
st.subheader("📋 Portfolio")
if not st.session_state.portfolio.empty:
    df = st.session_state.portfolio.copy()
    aktuelle_preise = []
    for t in df["Ticker"]:
        try:
            data = yf.Ticker(t).history(period="1d")
            aktuelle_preise.append(float(data["Close"].iloc[-1]))
        except:
            aktuelle_preise.append(float("nan"))
    df["Aktueller Preis"] = aktuelle_preise
    df["Positionswert"] = df["Aktueller Preis"] * df["Stückzahl"] - df["Gebühr"]
    df["Gewinn/Verlust"] = df["Positionswert"] - (df["Kaufpreis"]*df["Stückzahl"] + df["Gebühr"])
    df["Signal"] = df["Gewinn/Verlust"].apply(lambda x: "Halten" if x >=0 else "SELL")

    # Löschen-Funktion
    for i, row in df.iterrows():
        cols = st.columns([1,1,1,1,1,1])
        cols[0].write(row["Ticker"])
        cols[1].write(f"{row['Aktueller Preis']:.2f} €" if pd.notna(row['Aktueller Preis']) else "n.v.")
        cols[2].write(f"{row['Positionswert']:.2f} €")
        cols[3].write(f"{row['Gewinn/Verlust']:.2f} €")
        cols[4].write(row["Signal"])
        if cols[5].button("Löschen", key=f"del_{i}"):
            st.session_state.portfolio = st.session_state.portfolio.drop(i).reset_index(drop=True)
            st.experimental_rerun()  # nur hier, nach Löschen
else:
    st.info("Keine Aktien im Portfolio.")

# --- Kursverlauf ---
st.subheader("📈 Kursverlauf")
aktie_chart = st.selectbox("Aktie wählen", [""] + list(st.session_state.portfolio["Ticker"]))
if aktie_chart:
    try:
        df_chart = yf.Ticker(aktie_chart).history(period="6mo")
        df_chart["SMA20"] = df_chart["Close"].rolling(window=20).mean()
        df_chart["SMA50"] = df_chart["Close"].rolling(window=50).mean()
        chart = alt.Chart(df_chart.reset_index()).mark_line().encode(
            x="Date:T", y="Close:Q", tooltip=["Date:T","Close:Q"]
        )
        sma20_line = alt.Chart(df_chart.reset_index()).mark_line(color="orange").encode(x="Date:T", y="SMA20:Q")
        sma50_line = alt.Chart(df_chart.reset_index()).mark_line(color="green").encode(x="Date:T", y="SMA50:Q")
        st.altair_chart(chart + sma20_line + sma50_line, use_container_width=True)
    except:
        st.warning("Chart konnte nicht geladen werden.")

# --- RSS-News ---
st.subheader("📰 News")
if rss_available:
    feed_url = "https://www.finanzen.net/rss/aktien"
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:5]:
        st.markdown(f"- [{entry.title}]({entry.link})")
else:
    st.info("RSS-News nicht verfügbar (installiere feedparser)")
