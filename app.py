@st.cache_data
def load_data(ticker):
    import yfinance as yf
    import pandas as pd
    import ta

    try:
        # --- Versuch 1: letzte 6 Monate ---
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if "Close" in df and not df["Close"].dropna().empty:
            close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
        else:
            # --- Versuch 2: 1 Jahr ---
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if "Close" in df and not df["Close"].dropna().empty:
                close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
            else:
                # --- Versuch 3: maximal verfügbar ---
                df = yf.download(ticker, period="max", interval="1d", progress=False)
                if "Close" in df and not df["Close"].dropna().empty:
                    close_series = pd.to_numeric(df["Close"], errors='coerce').fillna(method='ffill').fillna(0)
                else:
                    return pd.DataFrame()  # wirklich keine Daten

        # --- Technische Indikatoren ---
        df["SMA20"] = ta.trend.SMAIndicator(close_series, 20).sma_indicator()
        df["SMA50"] = ta.trend.SMAIndicator(close_series, 50).sma_indicator()
        df["RSI"] = ta.momentum.RSIIndicator(close_series, 14).rsi()
        macd = ta.trend.MACD(close_series)
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["Volume"] = pd.to_numeric(df.get("Volume", 0), errors='coerce').fillna(0)
        df["Volumen_Signal"] = df["Volume"].rolling(20).mean().fillna(0)

        # Sicherstellen, dass alle numerischen Spalten korrekt sind
        for col in ["SMA20","SMA50","RSI","MACD","MACD_signal","Volume","Volumen_Signal"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except Exception as e:
        return pd.DataFrame()
