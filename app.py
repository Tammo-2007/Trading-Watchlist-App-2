import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide", page_title="Trading Dashboard Pro")

# --- Session State ---
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["PLTR", "NVDA", "TSLA"]
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["Ticker","Kaufpreis","Stückzahl"])

# --- Daten laden ---
@st.cache_data(ttl=900)
def load_data(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty: return pd.DataFrame()
        df = df.dropna(how="all")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

# --- Indikatoren ---
def add_indicators(df):
    df = df.copy()
    if df.empty: return df
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["GoldenCross"] = (df["MA50"] > df["MA200"]) & (df["MA50"].shift(1) <= df["MA200"].shift(1))
    return df

# --- Titel ---
st.title("📊 Trading Dashboard Pro (Stabil)")

# --- Watchlist verwalten ---
with st.expander("🔧 Watchlist verwalten"):
    new_ticker = st.text_input("Ticker hinzufügen")
    if st.button("Hinzufügen"):
        t = new_ticker.upper()
        if t and t not in st.session_state.watchlist:
            st.session_state.watchlist.append(t)
            st.success(f"{t} hinzugefügt")
    if st.session_state.watchlist:
        remove = st.selectbox("Ticker löschen", st.session_state.watchlist)
        if st.button("Löschen"):
            st.session_state.watchlist.remove(remove)
            st.success(f"{remove} gelöscht")

# --- Watchlist Tabelle ---
st.subheader("📈 Watchlist Übersicht")
rows = []
for t in st.session_state.watchlist:
    df = load_data(t)
    if df.empty: continue
    df = add_indicators(df)
    last = df.iloc[-1]
    perf_1m = ((last["Close"]/df.iloc[-20]["Close"] -1)*100) if len(df)>20 else np.nan
    rows.append({
        "Ticker": t,
        "Preis": round(last["Close"],2) if "Close" in last else None,
        "1M %": round(perf_1m,2) if pd.notna(perf_1m) else None,
        "RSI": round(last["RSI"],2) if "RSI" in last else None,
        "GoldenCross": bool(last["GoldenCross"]) if "GoldenCross" in last else False
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True)

# --- Portfolio ---
st.subheader("💰 Portfolio")
with st.expander("Position hinzufügen"):
    if st.session_state.watchlist:
        ticker = st.selectbox("Ticker", st.session_state.watchlist)
        buy = st.number_input("Kaufpreis", value=0.0, step=0.01)
        qty = st.number_input("Stückzahl", value=1, step=1)
        if st.button("Speichern"):
            new_row = pd.DataFrame([{"Ticker":ticker,"Kaufpreis":buy,"Stückzahl":qty}])
            st.session_state.portfolio = pd.concat([st.session_state.portfolio,new_row],ignore_index=True)
            st.success(f"{ticker} gespeichert!")

if not st.session_state.portfolio.empty:
    pf = st.session_state.portfolio.copy()
    pnl_list=[]
    for _, r in pf.iterrows():
        df = load_data(r["Ticker"])
        if df.empty or "Close" not in df.columns:
            pnl_list.append(0)
            continue
        current_price = df["Close"].iloc[-1]
        pnl_list.append(round((current_price - r["Kaufpreis"])*r["Stückzahl"],2))
    pf["PnL €"] = pnl_list
    st.dataframe(pf,use_container_width=True)

# --- Chart ---
st.subheader("📊 Chart")
if st.session_state.watchlist:
    chart_ticker = st.selectbox("Ticker wählen", st.session_state.watchlist, key="chart")
    df = load_data(chart_ticker)
    if not df.empty and "Close" in df.columns:
        df = add_indicators(df)
        cols = ["Close"]
        if "MA50" in df.columns: cols.append("MA50")
        if "MA200" in df.columns: cols.append("MA200")
        st.line_chart(df[cols].dropna())
        if "RSI" in df.columns:
            st.subheader("RSI")
            st.line_chart(df["RSI"].dropna().tail(100))
    else:
        st.warning("Keine Daten verfügbar")
