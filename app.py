st.header("📊 Interaktive Aktien-Analyse")

# Dropdown: Aktie aus Portfolio auswählen
if not st.session_state.aktien_liste:
    st.info("Bitte trage zuerst Aktien in der Sidebar ein.")
else:
    selected_portfolio_ticker = st.selectbox(
        "Wähle eine Aktie aus deinem Portfolio",
        [a["Ticker"] for a in st.session_state.aktien_liste],
        format_func=lambda x: next(a["Name"] for a in st.session_state.aktien_liste if a["Ticker"]==x)
    )

    # Daten laden
    df_selected = load_data(selected_portfolio_ticker)
    if df_selected.empty:
        st.warning("Keine Kursdaten verfügbar.")
    else:
        df_selected["Advanced_Signal"] = df_selected.apply(advanced_signal, axis=1)
        tendenz = forecast_trend(df_selected)
        df_reset = df_selected.reset_index()

        # --- Charts ---
        st.subheader(f"📈 Kurs + Signale für {selected_portfolio_ticker}")
        chart = alt.Chart(df_reset).mark_line(color="blue").encode(x="Date:T",y="Close:Q")
        if show_sma:
            chart += alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T",y="SMA20:Q")
            chart += alt.Chart(df_reset).mark_line(color="purple").encode(x="Date:T",y="SMA50:Q")
        if show_markers:
            chart += alt.Chart(df_reset).mark_circle(size=100).encode(
                x="Date:T",
                y="Close:Q",
                color=alt.Color("Advanced_Signal:N", scale=alt.Scale(domain=list(signal_color.keys()), range=list(signal_color.values()))),
                tooltip=["Date:T","Close:Q","Advanced_Signal:N"]
            )
        st.altair_chart(chart.interactive(), use_container_width=True)

        st.subheader("📊 Indikatoren")
        indicator_chart = None
        if show_rsi:
            chart_rsi = alt.Chart(df_reset).mark_line(color="green").encode(x="Date:T",y="RSI:Q")
            indicator_chart = chart_rsi if indicator_chart is None else indicator_chart+chart_rsi
        if show_macd:
            chart_macd = alt.Chart(df_reset).mark_line(color="red").encode(x="Date:T",y="MACD:Q")
            chart_signal = alt.Chart(df_reset).mark_line(color="orange").encode(x="Date:T",y="MACD_signal:Q")
            indicator_chart = chart_macd+chart_signal if indicator_chart is None else indicator_chart+chart_macd+chart_signal
        if indicator_chart:
            st.altair_chart(indicator_chart,use_container_width=True)

        # Ampel & Prognose
        st.subheader("🟢 Erweiterte Ampel")
        last_signal = df_selected["Advanced_Signal"].iloc[-1]
        st.markdown(f"<div style='background-color:{signal_color.get(last_signal,'#CCCCCC')};padding:20px;text-align:center;font-size:30px;border-radius:10px;color:white;'>{last_signal}</div>", unsafe_allow_html=True)

        st.subheader("🔮 Prognose (nächste 3 Tage)")
        st.markdown(f"<div style='background-color:{forecast_color.get(tendenz,'#CCCCCC')};padding:20px;text-align:center;font-size:25px;border-radius:10px;color:white;'>{tendenz}</div>", unsafe_allow_html=True)

        # Historie
        st.subheader("🟡 Historie der letzten 20 Signale")
        if "Advanced_Signal" in df_reset.columns:
            df_hist = df_reset[["Date","Advanced_Signal"]].tail(20).copy()
            df_hist["Signal_Code"] = df_hist["Advanced_Signal"].map({"Stark Kauf":2,"Halten":1,"Stark Verkauf":0})
            st.dataframe(df_hist.set_index("Date")[["Signal_Code"]].style.background_gradient(cmap="RdYlGn", axis=None))
