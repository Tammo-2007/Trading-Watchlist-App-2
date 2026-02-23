with tab1:
    st.subheader("Dein Portfolio (Cards)")
    if portfolio.empty:
        st.info("Keine Aktien vorhanden.")
    else:
        # Aktuelle Preise abrufen
        tickers = portfolio["Ticker"].tolist()
        latest_prices = {}
        for t in tickers:
            try:
                data = yf.download(t, period="5d", interval="1d", progress=False)
                latest_prices[t] = data["Close"][-1] if not data.empty else None
            except:
                latest_prices[t] = None
        portfolio["Aktueller Preis"] = portfolio["Ticker"].map(lambda x: latest_prices.get(x, None))

        # Positionswert und Gewinn/Verlust berechnen
        def compute_values(row):
            price = row["Aktueller Preis"]
            positionswert = row["Stückzahl"] * price - row["Gebühr"] if price else 0
            gewinn = positionswert - (row["Kaufpreis"]*row["Stückzahl"] + row["Gebühr"])
            return pd.Series([positionswert, gewinn])
        portfolio[["Positionswert","Gewinn/Verlust"]] = portfolio.apply(compute_values, axis=1)

        # Stop-Loss Empfehlung
        def stop_loss_volatility(row):
            try:
                data = yf.Ticker(row["Ticker"]).history(period="1mo")
                if not data.empty:
                    returns = data["Close"].pct_change().dropna()
                    volatility = returns.std()
                    return max(row["Kaufpreis"] * (1 - volatility), 0)
                else:
                    return row["Kaufpreis"] * 0.95
            except:
                return row["Kaufpreis"] * 0.95
        portfolio["Stop-Loss-Empfehlung"] = portfolio.apply(stop_loss_volatility, axis=1)

        # Portfolio zweispaltig darstellen
        for _, row in portfolio.iterrows():
            col1, col2 = st.columns([1,2])  # links Card, rechts Chart
            with col1:
                color = "🟢" if row["Gewinn/Verlust"] >= 0 else "🔴"
                st.markdown(f"""
                <div style="border:1px solid #ccc; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f7f7f7;">
                <b>{row['Ticker']} {color}</b><br>
                Status: {row['Status']}<br>
                Aktueller Preis: {row['Aktueller Preis'] if row['Aktueller Preis'] else 'Kein Kurs'} €<br>
                Positionswert: {row['Positionswert']:.2f} €<br>
                Gewinn/Verlust: {row['Gewinn/Verlust']:.2f} €<br>
                📉 Stop-Loss: {row['Stop-Loss']} € | 📈 Take-Profit: {row['Take-Profit']} €<br>
                ⚠️ Stop-Loss Empfehlung: {row['Stop-Loss-Empfehlung']:.2f} €<br>
                Gebühr: {row['Gebühr']} € (pro Order)
                </div>
                """, unsafe_allow_html=True)

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
                        hist["Direction"] = hist["Close"].diff().apply(lambda x: "Steigend" if x >= 0 else "Fallend")

                        base = alt.Chart(hist).encode(x="Date:T")

                        close_line = base.mark_line().encode(
                            y="Close:Q",
                            color=alt.Color("Direction:N",
                                            scale=alt.Scale(domain=["Steigend","Fallend"], range=["green","red"]),
                                            legend=None),
                            tooltip=["Date:T","Close:Q"]
                        )
                        sma20_line = base.mark_line(color="orange").encode(y="SMA20:Q", tooltip=["Date:T","SMA20:Q"])
                        sma50_line = base.mark_line(color="blue").encode(y="SMA50:Q", tooltip=["Date:T","SMA50:Q"])

                        chart = alt.layer(close_line, sma20_line, sma50_line).resolve_scale(y="shared").properties(height=250)
                        st.altair_chart(chart, use_container_width=True)
                        st.markdown("**Legende:** 🟢 Steigend | 🔴 Fallend | 🟠 SMA20 | 🔵 SMA50")
                    else:
                        st.write("Chart nicht verfügbar")
                except:
                    st.write("Chart konnte nicht geladen werden")
