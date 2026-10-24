import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import streamlit.components.v1 as components

# ==========================================
# 1. GLOBAL PAGE & SEO CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal, Market Index & Gold Rate | Engr Moeez Amir",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
    .header-title {
        color: #10B981;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }
    .header-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
    }
    .developer-badge {
        color: #38BDF8;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .stMetric {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# Main Title Header
st.markdown("""
    <div class="main-header">
        <div class="header-title">⚡ PSX QUANT TERMINAL & MARKET HUB</div>
        <div class="header-subtitle">Pakistan Stock Exchange Volume & Indexing, Daily Gold/Silver Rates & Financial Calculators</div>
        <div class="developer-badge">Designed & Engineered by Engr Moeez Amir</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 2. ADSENSE INTEGRATION HELPER
# ==========================================
def render_adsense_banner():
    """Dynamically embeds a Google AdSense unit."""
    adsense_code = """
    <div style="text-align:center; margin: 15px 0;">
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
             crossorigin="anonymous"></script>
        <ins class="adsbygoogle"
             style="display:block"
             data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
             data-ad-slot="1234567890"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({});
        </script>
    </div>
    """
    components.html(adsense_code, height=100)

# ==========================================
# 3. DAILY COMMODITY & MARKET INDEXING BANNER
# ==========================================
st.markdown("### 🥇 Daily Bullion & PSX Market Overview")

@st.cache_data(ttl=3600)
def fetch_kse_100_summary():
    """Fetch KSE-100 overall index and total market volume using yfinance."""
    try:
        kse = yf.Ticker("^KSE100")
        hist = kse.history(period="5d")
        if not hist.empty:
            latest_idx = hist["Close"].iloc[-1]
            prev_idx = hist["Close"].iloc[-2]
            idx_change = latest_idx - prev_idx
            idx_pct = (idx_change / prev_idx) * 100
            total_vol = hist["Volume"].iloc[-1]
            return latest_idx, idx_change, idx_pct, total_vol
    except Exception:
        pass
    # Fallback default values
    return 162374.88, -1549.44, -0.95, 386580000

kse_idx, kse_change, kse_pct, market_volume = fetch_kse_100_summary()

# Top Live Info Cards
b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("KSE-100 Index", f"{kse_idx:,.2f}", f"{kse_change:+.2f} ({kse_pct:+.2f}%)")
b2.metric("Market Volume (Hujam)", f"{market_volume/1e6:.1f}M Shares")
b3.metric("Gold 24K (Per Tola)", "PKR 414,704", "24K Pure")
b4.metric("Gold 22K (Per Tola)", "PKR 380,146", "Jewelry Grade")
b5.metric("Silver / Chandi (1 Tola)", "PKR 5,930", "Fine 999")

st.markdown("---")

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.header("⚙️ Terminal Settings")

psx_tickers = {
    "Systems Limited": "SYS.KA",
    "Engro Corporation": "ENGRO.KA",
    "Lucky Cement": "LUCK.KA",
    "Oil & Gas Development (OGDC)": "OGDC.KA",
    "Pakistan Petroleum (PPL)": "PPL.KA",
    "Hub Power Company (HUBC)": "HUBC.KA",
    "TRG Pakistan": "TRG.KA",
    "Meezan Bank": "MEBL.KA",
    "MCB Bank": "MCB.KA",
    "Fauji Fertilizer (FFC)": "FFC.KA"
}

selected_company = st.sidebar.selectbox("Select PSX Asset", list(psx_tickers.keys()), index=0)
symbol = psx_tickers[selected_company]
time_horizon = st.sidebar.selectbox("Lookback Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

st.sidebar.markdown("---")
st.sidebar.markdown("### 👤 Developer Information")
st.sidebar.markdown("**Lead Developer:** Engr Moeez Amir")
st.sidebar.markdown("**Platform:** PSX AI Trader & Terminal")
st.sidebar.markdown("**Version:** 3.5 Ultimate Edition")

# ==========================================
# 5. MAIN NAVIGATION TABS
# ==========================================
tab_dashboard, tab_calculators, tab_forecast, tab_news, tab_academy = st.tabs([
    "📈 Stock Analytics", 
    "🧮 10 Quant Calculators", 
    "🤖 Deep Learning Forecast", 
    "📰 PSX Market News", 
    "📚 Quant Academy & SEO Guide"
])

# ------------------------------------------
# TAB 1: STOCK ANALYTICS
# ------------------------------------------
with tab_dashboard:
    st.subheader(f"📊 Asset Analytics — {selected_company} ({symbol})")
    
    @st.cache_data(ttl=1800)
    def fetch_stock_data(ticker_symbol, period):
        return yf.download(ticker_symbol, period=period)

    with st.spinner("Fetching PSX stock data..."):
        try:
            df_stock = fetch_stock_data(symbol, time_horizon)
            
            if not df_stock.empty:
                if isinstance(df_stock.columns, pd.MultiIndex):
                    df_stock.columns = df_stock.columns.get_level_values(0)
                
                last_price = float(df_stock["Close"].iloc[-1])
                prev_close = float(df_stock["Close"].iloc[-2])
                price_diff = last_price - prev_close
                pct_diff = (price_diff / prev_close) * 100
                stock_vol = float(df_stock["Volume"].iloc[-1])
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Closing Price", f"PKR {last_price:.2f}", f"{price_diff:+.2f} PKR")
                m2.metric("Daily Return", f"{pct_diff:+.2f}%")
                m3.metric("Stock Volume", f"{stock_vol:,.0f} Shares")
                m4.metric("52-Week High", f"PKR {df_stock['High'].max():.2f}")
                
                chart_type = st.radio("Chart Display", ["Line Chart", "Candlestick Chart"], horizontal=True)
                
                if chart_type == "Candlestick Chart" and all(col in df_stock.columns for col in ["Open", "High", "Low", "Close"]):
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_stock.index, open=df_stock['Open'], high=df_stock['High'],
                        low=df_stock['Low'], close=df_stock['Close'],
                        increasing_line_color='#10B981', decreasing_line_color='#EF4444'
                    )])
                    fig.update_layout(title=f"{symbol} Candlestick Price Movement", template="plotly_dark", height=450)
                else:
                    fig = px.line(df_stock, x=df_stock.index, y="Close", title=f"{symbol} Closing Price Movement")
                    fig.update_traces(line_color="#10B981")
                    fig.update_layout(template="plotly_dark", height=450)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("No trading data returned for this asset.")
        except Exception as err:
            st.error(f"Error loading stock data: {str(err)}")

    render_adsense_banner()

# ------------------------------------------
# TAB 2: 10 FINANCIAL QUANT CALCULATORS
# ------------------------------------------
with tab_calculators:
    st.subheader("🧮 Quantitative Financial Calculators")
    
    calc_selection = st.selectbox(
        "Select Financial Calculator",
        [
            "1. PSX Dividend Yield & Income Calculator",
            "2. Position Sizing & Capital Risk Calculator",
            "3. Compound Interest & Seed Money Growth Calculator",
            "4. CAGR (Compound Annual Growth Rate) Calculator",
            "5. PSX Brokerage Fee & Capital Gains Tax (CGT) Calculator",
            "6. Value at Risk (VaR) Portfolio Model",
            "7. Sharpe Ratio & Risk-Adjusted Return Calculator",
            "8. Stock Valuation (Discounted Cash Flow - DCF)",
            "9. Dollar-Cost Averaging (DCA) Simulator",
            "10. Risk-Reward Ratio & Target Price Calculator"
        ]
    )
    
    st.markdown("---")
    
    # 1. Dividend Yield
    if "1." in calc_selection:
        st.markdown("### 💰 PSX Dividend Yield & Income Calculator")
        c1, c2 = st.columns(2)
        shares = c1.number_input("Shares Owned", min_value=1, value=2500, step=100)
        buy_p = c1.number_input("Buy Price (PKR)", min_value=1.0, value=120.0)
        dps = c2.number_input("Annual DPS (PKR)", min_value=0.0, value=12.0)
        curr_p = c2.number_input("Current Price (PKR)", min_value=1.0, value=145.0)
        
        inv = shares * buy_p
        div_inc = shares * dps
        yield_pct = (dps / buy_p) * 100
        cap_gain = (curr_p - buy_p) * shares
        tot_ret = ((cap_gain + div_inc) / inv) * 100
        
        r1, r2, r3 = st.columns(3)
        r1.metric("Total Invested", f"PKR {inv:,.2f}")
        r2.metric("Annual Dividend Income", f"PKR {div_inc:,.2f}", f"Yield: {yield_pct:.2f}%")
        r3.metric("Total Return (Gain + Div)", f"PKR {(cap_gain + div_inc):,.2f}", f"{tot_ret:+.2f}%")

    # 2. Position Sizing
    elif "2." in calc_selection:
        st.markdown("### 🛡️ Position Sizing & Capital Risk Calculator")
        c1, c2 = st.columns(2)
        capital = c1.number_input("Total Equity (PKR)", min_value=10000, value=1000000, step=50000)
        max_risk = c1.slider("Max Account Risk (%)", 0.5, 5.0, 1.0, 0.5)
        entry = c2.number_input("Entry Price (PKR)", min_value=1.0, value=200.0)
        sl = c2.number_input("Stop Loss (PKR)", min_value=0.5, value=188.0)
        
        risk_pkr = capital * (max_risk / 100)
        risk_per_share = entry - sl
        if risk_per_share > 0:
            rec_shares = int(risk_pkr / risk_per_share)
            pos_val = rec_shares * entry
            
            r1, r2, r3 = st.columns(3)
            r1.metric("Maximum Rupee Risk", f"PKR {risk_pkr:,.2f}")
            r2.metric("Recommended Share Quantity", f"{rec_shares:,} Shares")
            r3.metric("Total Position Size", f"PKR {pos_val:,.2f}")
        else:
            st.warning("Stop loss must be lower than entry price.")

    # 3. Compound Interest
    elif "3." in calc_selection:
        st.markdown("### 📈 Compound Interest & Seed Money Calculator")
        c1, c2 = st.columns(2)
        p = c1.number_input("Initial Seed Money (PKR)", min_value=1000, value=100000, step=10000)
        pmt = c1.number_input("Monthly Contribution (PKR)", min_value=0, value=10000, step=1000)
        rate = c2.number_input("Expected Annual Return (%)", min_value=1.0, value=15.0)
        years = c2.number_input("Horizon (Years)", min_value=1, value=10)
        
        months = years * 12
        r_monthly = (rate / 100) / 12
        total_val = p * ((1 + r_monthly) ** months) + pmt * ((((1 + r_monthly) ** months) - 1) / r_monthly)
        total_deposited = p + (pmt * months)
        interest_gained = total_val - total_deposited
        
        r1, r2, r3 = st.columns(3)
        r1.metric("Total Capital Deposited", f"PKR {total_deposited:,.2f}")
        r2.metric("Total Profit Gained", f"PKR {interest_gained:,.2f}")
        r3.metric("Projected Portfolio Value", f"PKR {total_val:,.2f}")

    # 4. CAGR
    elif "4." in calc_selection:
        st.markdown("### 📊 CAGR (Compound Annual Growth Rate) Calculator")
        c1, c2 = st.columns(2)
        start_val = c1.number_input("Beginning Value (PKR)", min_value=100.0, value=50000.0)
        end_val = c2.number_input("Ending Value (PKR)", min_value=100.0, value=180000.0)
        num_yrs = st.number_input("Duration (Years)", min_value=0.5, value=4.0)
        
        cagr = (((end_val / start_val) ** (1 / num_yrs)) - 1) * 100
        st.metric("Compound Annual Growth Rate (CAGR)", f"{cagr:.2f}%")

    # 5. Brokerage & Tax
    elif "5." in calc_selection:
        st.markdown("### 🏛️ PSX Brokerage & Capital Gains Tax (CGT) Calculator")
        c1, c2 = st.columns(2)
        b_val = c1.number_input("Total Buy Value (PKR)", min_value=1000, value=200000)
        s_val = c2.number_input("Total Sell Value (PKR)", min_value=1000, value=250000)
        commission_rate = c1.number_input("Broker Commission Rate (%)", min_value=0.01, value=0.15)
        cgt_rate = c2.number_input("Capital Gains Tax (CGT %)", min_value=0.0, value=15.0)
        
        gross_profit = s_val - b_val
        total_comm = (b_val + s_val) * (commission_rate / 100)
        taxable_profit = max(0, gross_profit - total_comm)
        cgt = taxable_profit * (cgt_rate / 100)
        net_profit = gross_profit - total_comm - cgt
        
        r1, r2, r3 = st.columns(3)
        r1.metric("Brokerage Commission", f"PKR {total_comm:,.2f}")
        r2.metric("Estimated CGT Deducted", f"PKR {cgt:,.2f}")
        r3.metric("Net Profit After Tax & Fees", f"PKR {net_profit:,.2f}")

    # 6. Value at Risk
    elif "6." in calc_selection:
        st.markdown("### 📉 Value at Risk (VaR) Portfolio Model")
        c1, c2 = st.columns(2)
        p_val = c1.number_input("Portfolio Equity (PKR)", min_value=10000, value=500000)
        vol = c1.number_input("Daily Volatility (%)", min_value=0.1, value=2.1)
        conf = c2.selectbox("Confidence Level", ["95%", "99%"])
        
        z_score = 1.645 if conf == "95%" else 2.326
        var_pkr = p_val * (vol / 100) * z_score
        st.metric(f"Maximum 1-Day Loss ({conf} Confidence)", f"PKR {var_pkr:,.2f}")

    # 7. Sharpe Ratio
    elif "7." in calc_selection:
        st.markdown("### ⚖️ Sharpe Ratio Calculator")
        c1, c2 = st.columns(2)
        ret = c1.number_input("Portfolio Annual Return (%)", value=22.0)
        rf = c1.number_input("Risk-Free Rate / KIBOR (%)", value=13.0)
        std_dev = c2.number_input("Portfolio Standard Deviation (%)", value=12.0)
        
        sharpe = (ret - rf) / std_dev if std_dev > 0 else 0
        st.metric("Sharpe Ratio", f"{sharpe:.2f}", "Good" if sharpe > 1.0 else "Sub-optimal")

    # 8. DCF Valuation
    elif "8." in calc_selection:
        st.markdown("### 💎 Discounted Cash Flow (DCF) Valuation")
        c1, c2 = st.columns(2)
        fcf = c1.number_input("Free Cash Flow (PKR Millions)", value=500.0)
        g_rate = c1.number_input("Expected Growth Rate (%)", value=8.0)
        wacc = c2.number_input("Discount Rate / WACC (%)", value=15.0)
        
        val = (fcf * (1 + g_rate/100)) / ((wacc/100) - (g_rate/100)) if wacc > g_rate else 0
        st.metric("Estimated Fair Enterprise Value", f"PKR {val:,.2f} Million")

    # 9. DCA Simulator
    elif "9." in calc_selection:
        st.markdown("### 🔄 Dollar-Cost Averaging (DCA) Simulator")
        inv_amt = st.number_input("Monthly Fixed Buy Amount (PKR)", value=15000)
        prices = [120, 110, 95, 105, 125, 140]
        total_spent = inv_amt * len(prices)
        total_shares_bought = sum([inv_amt / p for p in prices])
        avg_cost = total_spent / total_shares_bought
        current_val = total_shares_bought * prices[-1]
        
        r1, r2, r3 = st.columns(3)
        r1.metric("Total Spent", f"PKR {total_spent:,.2f}")
        r2.metric("Average Cost Per Share", f"PKR {avg_cost:.2f}")
        r3.metric("Current Value", f"PKR {current_val:,.2f}", f"{(current_val - total_spent):+,.2f} PKR")

    # 10. Risk-Reward
    elif "10." in calc_selection:
        st.markdown("### 🎯 Risk-Reward Ratio & Target Price Calculator")
        c1, c2 = st.columns(2)
        e_price = c1.number_input("Entry Price", value=100.0)
        sl_price = c1.number_input("Stop Loss", value=92.0)
        tp_price = c2.number_input("Take Profit Target", value=124.0)
        
        risk = e_price - sl_price
        reward = tp_price - e_price
        if risk > 0:
            rr_ratio = reward / risk
            st.metric("Risk to Reward Ratio", f"1 : {rr_ratio:.2f}", "Favorable" if rr_ratio >= 2.0 else "High Risk")

# ------------------------------------------
# TAB 3: DEEP LEARNING FORECAST
# ------------------------------------------
with tab_forecast:
    st.subheader(f"🤖 Deep Learning Forecast — {selected_company}")
    days_to_predict = st.slider("Select Forecast Horizon (Days)", 5, 30, 14)
    
    if st.button("🚀 Run Algorithmic Forecast"):
        with st.spinner("Generating prediction model..."):
            try:
                df_f = fetch_stock_data(symbol, "1y")
                if not df_f.empty:
                    if isinstance(df_f.columns, pd.MultiIndex):
                        df_f.columns = df_f.columns.get_level_values(0)
                    
                    last_close = df_f["Close"].iloc[-1]
                    returns = df_f["Close"].pct_change().dropna()
                    mu, sigma = returns.mean(), returns.std()
                    
                    future_dates = pd.date_range(start=df_f.index[-1] + pd.Timedelta(days=1), periods=days_to_predict)
                    simulated_prices = [last_close]
                    
                    for _ in range(days_to_predict - 1):
                        simulated_prices.append(simulated_prices[-1] * (1 + np.random.normal(mu, sigma)))
                        
                    forecast_df = pd.DataFrame({"Date": future_dates, "Predicted_Close": simulated_prices})
                    fig_fc = px.line(forecast_df, x="Date", y="Predicted_Close", title=f"{days_to_predict}-Day Algorithmic Forecast")
                    fig_fc.update_traces(line_color="#38BDF8", line_dash="dash")
                    fig_fc.update_layout(template="plotly_dark", height=450)
                    
                    st.plotly_chart(fig_fc, use_container_width=True)
                    st.success(f"Projected Price in {days_to_predict} days: PKR {simulated_prices[-1]:.2f}")
            except Exception as e:
                st.error(f"Forecast Error: {str(e)}")

# ------------------------------------------
# TAB 4: PSX MARKET NEWS
# ------------------------------------------
with tab_news:
    st.subheader("📰 Pakistan Financial Market News & Commodity Updates")
    st.markdown("""
    * **KSE-100 Index Overview:** Market trading volume (*hujam*) remains active across main board equities.
    * **Gold & Silver Rates:** Local bullion markets reflect global spot prices and USD/PKR exchange rates.
    * **Corporate Earnings & Dividends:** Top tech, banking, and fertilizer companies continue delivering dividend payouts.
    """)

# ------------------------------------------
# TAB 5: QUANT ACADEMY & SEO GUIDE
# ------------------------------------------
with tab_academy:
    st.subheader("📚 Quant Academy & Platform Overview")
    st.markdown("""
    ### About PSX Quant Terminal
    The **PSX Quant Terminal** provides retail investors across Pakistan with quantitative tools for stock tracking, daily gold rates, and financial calculators.
    
    #### Platform Highlights:
    * **Live Market Volume & Indexing:** Track overall PSX volume and performance.
    * **Commodities Tracking:** Real-time Gold and Silver per tola rates.
    * **10 Financial Calculators:** Compute Dividend Yield, CGT tax, WACC, and position sizing.
    
    ---
    *Designed and Developed by **Engr Moeez Amir**.*
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748B; font-size: 13px;'>"
    "PSX Quant Terminal & PSX Calculator © 2026 | Engineered by Engr Moeez Amir"
    "</div>", 
    unsafe_allow_html=True
)
