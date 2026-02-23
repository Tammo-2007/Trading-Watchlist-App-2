st.subheader("📋 Portfolio")

total_value = 0
total_invested = 0

if st.session_state.aktien_liste:

    for i, a in enumerate(st.session_state.aktien_liste):

        col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,2,2,1])

        ticker = a["ticker"]
        df = yf.download(ticker, period="3mo", interval="1d")

        if not df.empty and "Close" in df.columns:

            current_price = df["Close"].iloc[-1]
            position_value = current_price * a["quantity"]
            invested = a["buy_price"] * a["quantity"]
            profit = position_value - invested
            profit_pct = (profit / invested) * 100 if invested != 0 else 0

            total_value += position_value
            total_invested += invested

            # Trend Signal
            df["SMA20"] = df["Close"].rolling(20).mean()
            df["SMA50"] = df["Close"].rolling(50).mean()

            if df["SMA20"].iloc[-1] > df["SMA50"].iloc[-1]:
                signal = "BUY"
                signal_color = "green"
            elif df["SMA20"].iloc[-1] < df["SMA50"].iloc[-1]:
                signal = "SELL"
                signal_color = "red"
            else:
                signal = "HOLD"
                signal_color = "orange"

        else:
            current_price = None
            position_value = 0
            profit = 0
            profit_pct = 0
            signal = "-"
            signal_color = "gray"

        col1.write(f"**{ticker}**")
        col2.write(f"{round(current_price,2)} €" if current_price else "-")
        col3.write(f"{round(position_value,2)} €")
        col4.markdown(
            f"<span style='color:{'green' if profit>=0 else 'red'}'>{round(profit,2)} € ({round(profit_pct,2)}%)</span>",
            unsafe_allow_html=True
        )
        col5.markdown(
            f"<span style='color:{signal_color}'><b>{signal}</b></span>",
            unsafe_allow_html=True
        )

        if col6.button("❌", key=f"delete_{i}"):
            st.session_state.aktien_liste.pop(i)
            save_portfolio()
            st.rerun()

    st.divider()

    portfolio_profit = total_value - total_invested
    portfolio_pct = (portfolio_profit / total_invested) * 100 if total_invested != 0 else 0

    st.subheader("💰 Gesamtportfolio")

    colA, colB, colC = st.columns(3)
    colA.metric("Investiert", f"{round(total_invested,2)} €")
    colB.metric("Aktueller Wert", f"{round(total_value,2)} €")
    colC.metric(
        "Gesamt Gewinn/Verlust",
        f"{round(portfolio_profit,2)} €",
        f"{round(portfolio_pct,2)} %"
    )

else:
    st.info("Noch keine Aktien im Portfolio.")
