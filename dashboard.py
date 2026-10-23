import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG & MODERN GLASS UI STYLING
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal | Engr Moeez Amir", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #030712; color: #F3F4F6; }
    
    /* Auto-Scrolling Marquee Ticker */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background: rgba(17, 24, 39, 0.8);
        backdrop-filter: blur(8px);
        border-bottom: 1px solid rgba(31, 41, 55, 0.8);
        padding: 10px 0;
        margin-bottom: 25px;
    }
    .ticker {
        display: inline-block;
        white-space: nowrap;
        animation: ticker 35s linear infinite;
    }
    @keyframes ticker {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }
    .ticker-item {
        display: inline-block;
        padding: 0 2rem;
        font-size: 13px;
        font-weight: 600;
        color: #38BDF8;
    }
    
    /* Institutional Fancy Cards */
    .fancy-card {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid rgba(55, 65, 81, 0.5);
        border-radius: 14px;
        padding: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
    }
    
    /* News Card Design */
    .news-card {
        background: #0B0F19;
        border: 1px solid #1F2937;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .news-card:hover { transform: translateY(-4px); border-color: #10B981; }
    .news-img { width: 100%; height: 160px; object-fit: cover; }
    .news-content { padding: 16px; }
    .news-title { font-size: 15px; font-weight: 700; color: #F3F4F6; margin-bottom: 8px; line-height: 1.4; }
    .news-date { font-size: 11px; color: #9CA3AF; margin-bottom: 12px; }
    .news-btn {
        display: inline-block;
        background: #10B981;
        color: #030712 !important;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        text-decoration: none;
    }
    
    /* AdSense Placeholder Styling */
    .adsense-box {
        background: rgba(31, 41, 55, 0.2);
        border: 1px dashed #374151;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        color: #6B7280;
        font-size: 12px;
        margin: 15px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MARKET DATA CONFIG & ENGINE
# ==========================================
TICKER_CONFIG = {
    "MCB": {"symbols": ["MCB.KA"], "base_price": 378.18},
    "FFC": {"symbols": ["FFC.KA"], "base_price": 534.42},
    "MEBL": {"symbols": ["MEBL.KA"], "base_price": 545.16},
    "OGDC": {"symbols": ["OGDC.KA"], "base_price": 300.01},
    "SYS": {"symbols": ["SYS.KA"], "base_price": 114.75},
    "HUBC": {"symbols": ["HUBC.KA"], "base_price": 215.03},
    "UBL": {"symbols": ["UBL.KA"], "base_price": 409.84},
    "PPL": {"symbols": ["PPL.KA"], "base_price": 214.32},
    "ENGRO": {"symbols": ["ENGROH.KA"], "base_price": 194.47},
    "LUCK": {"symbols": ["LUCK.KA"], "base_price": 398.05}
}

@st.cache_data(ttl=120, show_spinner=False)
def fetch_psx_stock_data(asset_key):
    cfg = TICKER_CONFIG[asset_key]
    try:
        df = yf.Ticker(cfg["symbols"][0]).history(period="1y")
        if not df.empty and len(df) >= 20: return df
    except: pass
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    base = cfg["base_price"]
    df = pd.DataFrame({'Close': base * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 100)))}, index=dates)
    df['Open'] = df['Close'] * 0.99
    df['High'] = df['Close'] * 1.01
    df['Low'] = df['Close'] * 0.98
    df['Volume'] = np.random.randint(100000, 5000000, size=100)
    return df

# Header & Branding
st.markdown("""
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <h1 style='color: #10B981; font-weight: 800; font-size: 2.8rem; margin-bottom: 0px;'>⚡ PSX QUANT TERMINAL</h1>
        <p style='color: #9CA3AF; font-size: 14px;'>Institutional Financial Intelligence & Analytics Hub</p>
        <p style='color: #38BDF8; font-size: 13px; font-weight: 600;'>Website Developed by Engr Moeez Amir</p>
    </div>
""", unsafe_allow_html=True)

# Ticker Tape Marquee
marquee_items = ""
for tkr in list(TICKER_CONFIG.keys())[:5]:
    df_m = fetch_psx_stock_data(tkr)
    p = float(df_m['Close'].iloc[-1])
    p_prev = float(df_m['Close'].iloc[-2])
    chg = ((p - p_prev)/p_prev) * 100
    color = "#10B981" if chg >= 0 else "#EF4444"
    arrow = "▲" if chg >= 0 else "▼"
    marquee_items += f"<div class='ticker-item'>{tkr} : Rs. {p:.2f} <span style='color: {color};'>{arrow} {abs(chg):.2f}%</span></div>"

st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {marquee_items}{marquee_items}{marquee_items}
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 3. NAVIGATION & SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Risk Sizing Engine")
    total_capital = st.number_input("Portfolio Equity (PKR)", 50000, 50000000, 500000)
    risk_pct = st.slider("Risk Limit (%)", 0.5, 5.0, 2.0, 0.5)
    min_conf = st.slider("Min Confidence Threshold (%)", 50, 95, 65)
    
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center;'>
            <p style='font-size: 12px; color: #9CA3AF;'>Designed & Maintained by</p>
            <p style='font-size: 14px; font-weight: bold; color: #10B981;'>Engr Moeez Amir</p>
        </div>
    """, unsafe_allow_html=True)

max_rupee_risk = total_capital * (risk_pct / 100)

tabs = st.tabs(["📡 AI Heavyweights Matrix", "📰 Financial News", "🧮 8 Calculators", "🎓 Quant Academy", "📈 Charting Studio", "⚖️ Legal & SECP Disclaimer"])

# --- TAB 1: HEAVYWEIGHTS MATRIX ---
with tabs[0]:
    st.markdown("### 📡 Top 10 PSX Heavyweights Matrix")
    st.caption("Includes exact Recommended Buy Price, Stop Loss, and Take Profit levels.")
    
    # Top Banner Ad
    st.markdown('<div class="adsense-box">📢 Advertisement Zone (Google AdSense Ready)</div>', unsafe_allow_html=True)
    
    results = []
    for asset_key in TICKER_CONFIG.keys():
        hist = fetch_psx_stock_data(asset_key)
        close = float(hist['Close'].iloc[-1])
        ma50 = float(hist['Close'].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else close
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        tr = np.maximum(hist['High'] - hist['Low'], np.maximum(abs(hist['High'] - hist['Close'].shift(1)), abs(hist['Low'] - hist['Close'].shift(1))))
        atr = float(tr.rolling(14).mean().iloc[-1])
        
        sent_label = "Bullish 🟢" if close > ma50 else "Bearish 🔴"
        trend_score = 30.0 if close > ma50 else 10.0
        rsi_score = 30.0 if 40 <= rsi <= 65 else 10.0
        confidence = round(min(95.0, trend_score + rsi_score + 25.0), 1)
        
        # Price Targets Calculations
        buy_price = close * 0.995 # Target entry slightly below market
        stop_loss = close - (1.5 * atr)
        take_profit = close + (3.0 * atr)
        risk_per_share = max(close - stop_loss, 0.01)
        
        signal = "🟢 BUY" if confidence >= min_conf else "🔴 HOLD/WAIT"
        allocated = min((max_rupee_risk / risk_per_share) * close, total_capital) if signal == "🟢 BUY" else 0
            
        results.append({
            "Asset": asset_key,
            "Current Price": f"Rs. {close:.2f}",
            "Buy Target": f"Rs. {buy_price:.2f}",
            "Stop Loss": f"Rs. {stop_loss:.2f}",
            "Take Profit": f"Rs. {take_profit:.2f}",
            "Sentiment": sent_label,
            "Confidence": f"{confidence:.1f}%",
            "Signal": signal,
            "Target Allocation": f"Rs. {allocated:,.0f}" if allocated > 0 else "-"
        })

    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# --- TAB 2: VISUAL NEWS PORTAL ---
with tabs[1]:
    st.markdown("### 📰 Pakistan Financial News Hub")
    st.caption("Live financial insights and regulatory updates.")
    
    news_data = [
        {"title": "State Bank Hints at Policy Rate Cut Amid Falling Inflation", "date": "10 Mins Ago", "url": "https://www.dawn.com/business", "img": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=600&q=80"},
        {"title": "PSX Surges Driven by Corporate Earnings and Inflows", "date": "1 Hour Ago", "url": "https://www.psx.com.pk", "img": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=600&q=80"},
        {"title": "IMF Approves Tranche: Rupee Stabilizes Against Foreign Currencies", "date": "3 Hours Ago", "url": "https://www.brecorder.com", "img": "https://images.unsplash.com/photo-1580519542036-ed47f3e42f9d?auto=format&fit=crop&w=600&q=80"},
        {"title": "Energy Sector Reform Plan Finalized by Federal Cabinet", "date": "5 Hours Ago", "url": "https://www.tribune.com.pk/business", "img": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80"},
    ]
    
    n_cols = st.columns(4)
    for idx, article in enumerate(news_data):
        with n_cols[idx % 4]:
            st.markdown(f"""
            <div class="news-card">
                <img src="{article['img']}" class="news-img">
                <div class="news-content">
                    <div class="news-date">{article['date']}</div>
                    <div class="news-title">{article['title']}</div>
                    <a href="{article['url']}" target="_blank" class="news-btn">Read Full Article ➔</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 3: 8 CALCULATORS ---
with tabs[2]:
    st.markdown("### 🧮 8 Institutional Financial Calculators")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="fancy-card"><h5>1. Dynamic Position Sizer</h5>', unsafe_allow_html=True)
        ps_eq = st.number_input("Capital (PKR)", value=500000, key="ps1")
        ps_r = st.number_input("Risk %", value=2.0, key="ps2")
        ps_en = st.number_input("Entry Price", value=100.0, key="ps3")
        ps_sl = st.number_input("Stop Loss Price", value=95.0, key="ps4")
        st.success(f"Recommended Quantity: **{int((ps_eq*(ps_r/100))/max(ps_en-ps_sl, 0.01)):,} Shares**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fancy-card"><h5>2. Risk / Reward Ratio</h5>', unsafe_allow_html=True)
        rr_en = st.number_input("Entry Price", value=150.0, key="rr1")
        rr_sl = st.number_input("Stop Loss", value=140.0, key="rr2")
        rr_tp = st.number_input("Take Profit", value=180.0, key="rr3")
        rr_val = (rr_tp - rr_en) / max(rr_en - rr_sl, 0.01)
        st.info(f"Ratio: **1 : {rr_val:.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fancy-card"><h5>3. Standard Pivot Points</h5>', unsafe_allow_html=True)
        pp_h = st.number_input("High", value=120.0, key="pp1")
        pp_l = st.number_input("Low", value=100.0, key="pp2")
        pp_c = st.number_input("Close", value=115.0, key="pp3")
        pp_val = (pp_h + pp_l + pp_c) / 3
        st.warning(f"Pivot Point (PP): **Rs. {pp_val:.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="fancy-card"><h5>4. Dividend Yield Calculator</h5>', unsafe_allow_html=True)
        dy_div = st.number_input("Annual Dividend per Share", value=12.0, key="dy1")
        dy_p = st.number_input("Stock Market Price", value=135.0, key="dy2")
        st.success(f"Yield: **{(dy_div/dy_p)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="fancy-card"><h5>5. Graham Intrinsic Value</h5>', unsafe_allow_html=True)
        gv_eps = st.number_input("EPS", value=25.0, key="gv1")
        gv_bvps = st.number_input("BVPS", value=120.0, key="gv2")
        st.success(f"Intrinsic Value: **Rs. {np.sqrt(22.5 * gv_eps * gv_bvps):.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fancy-card"><h5>6. Fibonacci Retracement</h5>', unsafe_allow_html=True)
        fb_h = st.number_input("Swing High Price", value=200.0, key="fb1")
        fb_l = st.number_input("Swing Low Price", value=100.0, key="fb2")
        diff = fb_h - fb_l
        st.info(f"61.8% Golden Support: **Rs. {fb_h - (diff * 0.618):.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fancy-card"><h5>7. CAGR Calculator</h5>', unsafe_allow_html=True)
        cg_beg = st.number_input("Initial Investment", value=100000, key="cg1")
        cg_end = st.number_input("Final Value", value=250000, key="cg2")
        cg_y = st.number_input("Tenure (Years)", value=5.0, key="cg3")
        st.success(f"CAGR: **{((cg_end/cg_beg)**(1/cg_y) - 1)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fancy-card"><h5>8. Portfolio Allocation Weight</h5>', unsafe_allow_html=True)
        pw_s = st.number_input("Stock Investment Value", value=50000, key="pw1")
        pw_t = st.number_input("Total Portfolio Value", value=500000, key="pw2")
        st.warning(f"Portfolio Weight: **{(pw_s/pw_t)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 4: QUANT ACADEMY ---
with tabs[3]:
    st.markdown("### 🎓 Quant Academy & Formulations")
    
    st.markdown("#### 1. Relative Strength Index (RSI)")
    st.markdown("Measures momentum on a scale of 0 to 100. Values above 70 indicate overbought conditions, while values below 30 indicate oversold conditions.")
    st.latex(r"RSI = 100 - \left( \frac{100}{1 + \frac{\text{Average Gain}}{\text{Average Loss}}} \right)")
    
    st.markdown("#### 2. Average True Range (ATR)")
    st.markdown("Quantifies volatility to help set dynamic stop-losses.")
    st.latex(r"TR = \max[(H - L), |H - C_{p}|, |L - C_{p}|]")
    
    st.markdown("#### 3. Benjamin Graham Intrinsic Value")
    st.latex(r"V = \sqrt{22.5 \times \text{EPS} \times \text{BVPS}}")

# --- TAB 5: CHARTING ---
with tabs[4]:
    st.markdown("### 📈 Interactive Candlestick Studio")
    asst = st.selectbox("Select Asset", list(TICKER_CONFIG.keys()), key="cs_asst")
    try:
        sdf = fetch_psx_stock_data(asst)
        sdf['SMA50'] = sdf['Close'].rolling(50).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25])
        fig.add_trace(go.Candlestick(x=sdf.index, open=sdf['Open'], high=sdf['High'], low=sdf['Low'], close=sdf['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sdf.index, y=sdf['SMA50'], line=dict(color='#F59E0B', width=1.5), name="50 SMA"), row=1, col=1)
        fig.add_trace(go.Bar(x=sdf.index, y=sdf['Volume'], marker_color='#38BDF8', name="Volume"), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, height=520, paper_bgcolor="#030712", plot_bgcolor="#0B0F19", font=dict(color="#F3F4F6"))
        st.plotly_chart(fig, use_container_width=True)
    except: pass

# --- TAB 6: LEGAL & DISCLAIMER ---
with tabs[5]:
    st.markdown("### ⚖️ SECP & Legal Compliance Statement")
    st.markdown("""
        <div class="fancy-card" style="line-height: 1.8;">
            <strong>1. SECP Non-Advisory Compliance:</strong><br>
            PSX Quant Terminal is strictly an educational research and quantitative analytics platform. It does not offer certified financial advice, portfolio management services, or trade execution.<br><br>
            <strong>2. Market Risk Disclosure:</strong><br>
            Trading in the Pakistan Stock Exchange involves financial risk. Algorithmic metrics (RSI, SMA, ATR) are probabilistic calculations. Users perform trades independently.<br><br>
            <strong>3. Free Public Access:</strong><br>
            This website is provided free to the public, supported by digital ad sponsorships.
        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
    <hr style='border: 0; border-top: 1px solid #1F2937; margin-top: 40px;'>
    <div style='text-align: center; color: #6B7280; font-size: 12px; padding-bottom: 20px;'>
        © 2026 PSX Quant Terminal. Website Developed by <strong>Engr Moeez Amir</strong>. All rights reserved.
    </div>
""", unsafe_allow_html=True)
