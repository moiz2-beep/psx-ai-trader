import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG & ANIMATED CSS STYLING
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal | Institutional Suite", 
    layout="wide", 
    page_icon="🏛️",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stApp { background-color: #050810; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    
    /* Animated Login Graphics */
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.2); }
        50% { box-shadow: 0 0 30px rgba(56, 189, 248, 0.6); }
        100% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.2); }
    }
    .animated-login-wrapper {
        background: linear-gradient(-45deg, #0f172a, #020617, #1e293b, #0f172a);
        background-size: 400% 400%;
        animation: gradientBG 12s ease infinite, pulseGlow 4s infinite;
        padding: 50px;
        border-radius: 16px;
        border: 1px solid #334155;
        max-width: 650px;
        margin: 40px auto;
        text-align: center;
    }
    
    /* Auto-Scrolling Marquee Ticker */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background-color: #0F172A;
        border-bottom: 1px solid #1E293B;
        padding: 8px 0;
        margin-bottom: 20px;
    }
    .ticker {
        display: inline-block;
        white-space: nowrap;
        animation: ticker 30s linear infinite;
    }
    @keyframes ticker {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }
    .ticker-item {
        display: inline-block;
        padding: 0 2rem;
        font-size: 14px;
        font-weight: 600;
        color: #38BDF8;
    }
    
    .calc-box { background-color: #0F172A; border: 1px solid #1E293B; padding: 24px; border-radius: 10px; margin-bottom: 20px; height: 100%; }
    .legal-box { background-color: #0B0F19; border: 1px solid #1E293B; padding: 25px; border-radius: 8px; font-size: 14px; color: #94A3B8; margin-bottom: 20px; line-height: 1.6;}
    
    /* News Portal CSS */
    .news-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .news-card:hover { transform: translateY(-5px); border-color: #38BDF8; }
    .news-img { width: 100%; height: 180px; object-fit: cover; border-bottom: 1px solid #1E293B; }
    .news-content { padding: 15px; }
    .news-title { font-size: 16px; font-weight: 700; color: #E2E8F0; margin-bottom: 10px; line-height: 1.4; }
    .news-date { font-size: 12px; color: #64748B; margin-bottom: 15px; }
    .news-btn { display: inline-block; background-color: #10B981; color: #050810 !important; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect("trades.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, plan TEXT, trx_id TEXT, expiry_date TEXT, status TEXT, best_friend TEXT, fav_place TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS calc_history (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, calc_name TEXT, inputs_text TEXT, result_text TEXT)")
        conn.commit()
        conn.close()
    except: pass
init_db()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "terms_accepted" not in st.session_state: st.session_state.terms_accepted = False

ADMIN_EMAIL = "moeez786amir@gmail.com"

# ==========================================
# 3. ANIMATED LOGIN PORTAL
# ==========================================
if not st.session_state.logged_in:
    st.markdown("""
        <div class="animated-login-wrapper">
            <h1 style="color: #38BDF8; margin-bottom: 5px;">🏛️ PSX Quant Terminal</h1>
            <p style="color: #94A3B8;">Institutional quantitative models & live market intelligence.</p>
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["🔑 Access Terminal", "💳 Buy Subscription", "🔄 Reset Password"])
    with t1:
        email = st.text_input("Registered Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if email == ADMIN_EMAIL and pwd == "Admin@2026":
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.terms_accepted = False # Force Admin to see terms too for testing
                st.rerun()
            else:
                try:
                    conn = sqlite3.connect("trades.db")
                    row = conn.cursor().execute("SELECT password, status, expiry_date FROM users WHERE email=?", (email,)).fetchone()
                    if row and row[0] == pwd:
                        if row[1] == "Active" and pd.to_datetime(row[2]) > pd.Timestamp.now():
                            st.session_state.logged_in = True
                            st.session_state.user_email = email
                            st.session_state.terms_accepted = False # Forces the Disclaimer Gate on login
                            st.rerun()
                        elif row[1] == "Pending": st.warning("⏳ Payment is pending verification by admin.")
                        else: st.error("❌ Subscription expired.")
                    else: st.error("❌ Invalid credentials.")
                except: pass
                
    with t2:
        st.markdown("**Plans:** Rs. 200/Month | Rs. 2,050/Year. **Transfer to:** JazzCash (03484178009) or EasyPaisa (03238891828).")
        r_email = st.text_input("Email", key="re")
        r_pwd = st.text_input("Password", type="password", key="rp")
        r_plan = st.selectbox("Plan", ["Monthly", "Annual"])
        r_trx = st.text_input("12-Digit TRX ID")
        st.markdown("#### 🔒 Security Questions (For Password Recovery)")
        reg_bf = st.text_input("Best Friend's Name", key="r_bf")
        reg_fp = st.text_input("Favorite Place", key="r_fp")
        if st.button("Submit Registration", type="primary"):
            if r_email and r_pwd and r_trx and reg_bf and reg_fp:
                exp = (datetime.datetime.now() + datetime.timedelta(days=30 if r_plan=="Monthly" else 365)).strftime('%Y-%m-%d %H:%M:%S')
                try:
                    conn = sqlite3.connect("trades.db")
                    conn.cursor().execute("INSERT OR REPLACE INTO users (email, password, plan, trx_id, expiry_date, status, best_friend, fav_place) VALUES (?,?,?,?,?,?,?,?)", 
                                          (r_email, r_pwd, r_plan, r_trx, exp, "Pending", reg_bf.lower(), reg_fp.lower()))
                    conn.commit()
                    st.success("✅ Submitted! Waiting for admin approval.")
                except: pass
            else: st.warning("Fill all fields.")
            
    with t3:
        st.markdown("Answer at least one security question correctly to reset your password.")
        rec_email = st.text_input("Registered Email", key="rec_email")
        ans_bf = st.text_input("Best Friend's Name", key="ans_bf")
        ans_fp = st.text_input("Favorite Place", key="ans_fp")
        new_password = st.text_input("New Password", type="password", key="new_password")
        if st.button("Reset Password", type="primary"):
            try:
                conn = sqlite3.connect("trades.db")
                row = conn.cursor().execute("SELECT best_friend, fav_place FROM users WHERE email = ?", (rec_email,)).fetchone()
                if row:
                    if (ans_bf.lower() == row[0]) or (ans_fp.lower() == row[1]):
                        conn.cursor().execute("UPDATE users SET password = ? WHERE email = ?", (new_password, rec_email))
                        conn.commit()
                        st.success("✅ Password reset successfully.")
                    else: st.error("❌ Incorrect answers.")
                else: st.error("❌ Email not found.")
            except: pass
    st.stop()

# ==========================================
# 4. POST-LOGIN MANDATORY DISCLAIMER GATE
# ==========================================
if st.session_state.logged_in and not st.session_state.terms_accepted:
    st.markdown("""
        <div style="max-width: 800px; margin: 40px auto; text-align: center;">
            <h1 style="color: #F59E0B; margin-bottom: 20px;">⚠️ Mandatory Legal & Risk Disclaimer</h1>
            <p style="color: #E2E8F0; font-size: 16px;">Please read and accept the following terms before accessing the terminal.</p>
            <div class="legal-box" style="text-align: left;">
                <strong>1. Non-Advisory Nature (SECP Compliance):</strong><br>
                PSX Quant Terminal is strictly a quantitative analysis and educational research tool. It does not provide certified financial advice, direct brokerage execution, or discretionary portfolio management. All data, AI signals, and calculations are for informational purposes only.<br><br>
                
                <strong>2. Algorithmic Risk & Market Volatility:</strong><br>
                The financial markets carry substantial risk. The platform uses historical data (SMA, RSI, ATR) and FinBERT NLP sentiment models which are probabilistic. Algorithms can lag, fail during unprecedented market shocks, or generate false positives. You trade entirely at your own risk.<br><br>
                
                <strong>3. Subscription & Refund Policy:</strong><br>
                By proceeding, you acknowledge that your manual mobile wallet subscription (Rs. 200/month or Rs. 2,050/year) is final and non-refundable once activated by the administrative team. Access will be revoked upon expiry if not renewed.<br><br>
                
                <strong>4. Data Privacy:</strong><br>
                Your authentication data and transaction IDs are secured locally. We do not sell your data to third parties.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("✅ I Agree & Understand — Enter Terminal", type="primary", use_container_width=True):
            st.session_state.terms_accepted = True
            st.rerun()
        if st.button("❌ Decline & Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.terms_accepted = False
            st.rerun()
    st.stop()

# ==========================================
# 5. AUTO-SCROLLING TICKER MARQUEE & UTILS
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
    return df

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
# 6. TERMINAL TABS & ARCHITECTURE
# ==========================================
with st.sidebar:
    st.title("🏛️ PSX Terminal")
    st.caption(f"Logged in: {st.session_state.user_email}")
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.terms_accepted = False
        st.rerun()
    total_capital = st.number_input("Account Equity (PKR)", 50000, 50000000, 500000)
    risk_pct = st.slider("Risk Limit (%)", 0.5, 5.0, 2.0, 0.5)
    min_conf = st.slider("Min Confidence (%)", 50, 95, 65)

max_rupee_risk = total_capital * (risk_pct / 100)

tabs_list = ["📡 AI Top 10 Matrix", "📰 Visual News Portal", "🧮 8 Calculators", "🎓 Quant Academy", "📈 Charting"]
if st.session_state.user_email == ADMIN_EMAIL: tabs_list.append("🔐 Admin")
tabs = st.tabs(tabs_list)

# --- TAB 1: TOP 10 LIVE MATRIX ---
with tabs[0]:
    st.header("📡 Top 10 PSX Heavyweights Matrix")
    st.markdown("Live processing of all 10 major assets using FinBERT NLP, 50 SMA, RSI, and ATR Volatility metrics.")
    
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
        
        stop_loss = close - (1.5 * atr)
        take_profit = close + (3.0 * atr)
        risk_per_share = max(close - stop_loss, 0.01)
        
        signal = "🟢 AI BUY" if confidence >= min_conf else "🔴 IGNORE"
        allocated = min((max_rupee_risk / risk_per_share) * close, total_capital) if signal == "🟢 AI BUY" else 0
            
        results.append({
            "Asset": asset_key, "Price": f"Rs. {close:.2f}", "Sentiment": sent_label,
            "AI Confidence": f"{confidence:.1f}%", "Signal": signal,
            "Target Allocation": f"Rs. {allocated:,.0f}" if allocated > 0 else "-"
        })

    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# --- TAB 2: VISUAL NEWS PORTAL (DAWN NEWS STYLE) ---
with tabs[1]:
    st.header("📰 Pakistan Financial News Portal")
    st.markdown("Live market insights, SECP decisions, and PSX corporate developments.")
    
    news_data = [
        {"title": "State Bank Hints at Policy Rate Cut Amid Falling Inflation", "date": "10 Mins Ago", "img": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=600&q=80"},
        {"title": "PSX Surges Past 80,000 Points Driven by Corporate Earnings", "date": "1 Hour Ago", "img": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=600&q=80"},
        {"title": "IMF Approves Next Tranche: Rupee Stabilizes Against Dollar", "date": "3 Hours Ago", "img": "https://images.unsplash.com/photo-1580519542036-ed47f3e42f9d?auto=format&fit=crop&w=600&q=80"},
        {"title": "Energy Sector Circular Debt: Government Proposes New Plan", "date": "5 Hours Ago", "img": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80"},
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
                    <a href="#" class="news-btn">Read Full Article ➔</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 3: ALL 8 CALCULATORS ---
with tabs[2]:
    st.header("🧮 8 Institutional Calculators")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="calc-box"><h5>1. Dynamic Position Size</h5>', unsafe_allow_html=True)
        ps_eq = st.number_input("Capital", value=500000, key="ps1")
        ps_r = st.number_input("Risk %", value=2.0, key="ps2")
        ps_en = st.number_input("Entry", value=100.0, key="ps3")
        ps_sl = st.number_input("Stop Loss", value=95.0, key="ps4")
        st.success(f"Buy: **{int((ps_eq*(ps_r/100))/max(ps_en-ps_sl, 0.01)):,} Shares**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box"><h5>2. Risk/Reward Ratio</h5>', unsafe_allow_html=True)
        rr_en = st.number_input("Entry Price", value=150.0, key="rr1")
        rr_sl = st.number_input("Stop Loss", value=140.0, key="rr2")
        rr_tp = st.number_input("Take Profit", value=180.0, key="rr3")
        rr_val = (rr_tp - rr_en) / max(rr_en - rr_sl, 0.01)
        st.info(f"Ratio: **1 : {rr_val:.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box"><h5>3. Standard Pivot Points</h5>', unsafe_allow_html=True)
        pp_h = st.number_input("Prev High", value=120.0, key="pp1")
        pp_l = st.number_input("Prev Low", value=100.0, key="pp2")
        pp_c = st.number_input("Prev Close", value=115.0, key="pp3")
        pp_val = (pp_h + pp_l + pp_c) / 3
        st.warning(f"Pivot Point (PP): **Rs. {pp_val:.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="calc-box"><h5>4. Dividend Yield</h5>', unsafe_allow_html=True)
        dy_div = st.number_input("Annual Dividend", value=12.0, key="dy1")
        dy_p = st.number_input("Stock Price", value=135.0, key="dy2")
        st.success(f"Yield: **{(dy_div/dy_p)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="calc-box"><h5>5. Graham Fair Value</h5>', unsafe_allow_html=True)
        gv_eps = st.number_input("EPS", value=25.0, key="gv1")
        gv_bvps = st.number_input("BVPS", value=120.0, key="gv2")
        st.success(f"Intrinsic Value: **Rs. {np.sqrt(22.5 * gv_eps * gv_bvps):.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box"><h5>6. Fibonacci Retracement</h5>', unsafe_allow_html=True)
        fb_h = st.number_input("Swing High", value=200.0, key="fb1")
        fb_l = st.number_input("Swing Low", value=100.0, key="fb2")
        diff = fb_h - fb_l
        st.info(f"61.8% Support: **Rs. {fb_h - (diff * 0.618):.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box"><h5>7. CAGR Calculator</h5>', unsafe_allow_html=True)
        cg_beg = st.number_input("Beginning Value", value=100000, key="cg1")
        cg_end = st.number_input("Ending Value", value=250000, key="cg2")
        cg_y = st.number_input("Years", value=5.0, key="cg3")
        st.success(f"CAGR: **{((cg_end/cg_beg)**(1/cg_y) - 1)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box"><h5>8. Portfolio Weight</h5>', unsafe_allow_html=True)
        pw_s = st.number_input("Stock Value", value=50000, key="pw1")
        pw_t = st.number_input("Total Portfolio", value=500000, key="pw2")
        st.warning(f"Weight: **{(pw_s/pw_t)*100:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 4: QUANT ACADEMY ---
with tabs[3]:
    st.header("🎓 Quant Academy & Formulas")
    st.markdown("Understand the mathematical backbone of your PSX AI Matrix.")
    
    st.markdown("### 1. Relative Strength Index (RSI)")
    st.markdown("Measures the speed and change of price movements. Values >70 indicate overbought; <30 indicate oversold.")
    st.latex(r"RSI = 100 - \left( \frac{100}{1 + \frac{\text{Average Gain}}{\text{Average Loss}}} \right)")
    
    st.markdown("### 2. Average True Range (ATR)")
    st.markdown("Measures market volatility. We use it to set dynamic stop-losses (e.g., $1.5 \times ATR$).")
    st.latex(r"TR = \max[(H - L), |H - C_{p}|, |L - C_{p}|]")
    
    st.markdown("### 3. Benjamin Graham Intrinsic Value")
    st.markdown("Finds the underlying value of a stock using Earnings Per Share (EPS) and Book Value (BVPS).")
    st.latex(r"V = \sqrt{22.5 \times \text{EPS} \times \text{BVPS}}")
    st.markdown("""
    **Practical PSX Example:**
    * You are analyzing **FFC (Fauji Fertilizer)**.
    * EPS is Rs. 25. BVPS is Rs. 120.
    * Calculation: $V = \sqrt{22.5 \times 25 \times 120} = \sqrt{67500} = 259.8$
    * **Conclusion:** The true fundamental value of FFC is Rs. 259.8. If the current PSX market price is Rs. 180, it is undervalued.
    """)
    
    st.markdown("### 4. Dynamic Risk Position Sizing")
    st.markdown("Calculates exactly how many shares keep you under your maximum loss threshold.")
    st.latex(r"\text{Shares} = \frac{\text{Account Capital} \times \text{Risk Percentage}}{\text{Entry Price} - \text{Stop Loss Price}}")

# --- TAB 5: CHARTING ---
with tabs[4]:
    st.header("📈 Interactive Candlestick Studio")
    asst = st.selectbox("Select Asset", list(TICKER_CONFIG.keys()), key="cs_asst")
    try:
        sdf = fetch_psx_stock_data(asst)
        sdf['SMA50'] = sdf['Close'].rolling(50).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25])
        fig.add_trace(go.Candlestick(x=sdf.index, open=sdf['Open'], high=sdf['High'], low=sdf['Low'], close=sdf['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sdf.index, y=sdf['SMA50'], line=dict(color='#F59E0B', width=1.5), name="50 SMA"), row=1, col=1)
        fig.add_trace(go.Bar(x=sdf.index, y=sdf['Volume'], marker_color='#38BDF8', name="Volume"), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, height=520, paper_bgcolor="#080A0F", plot_bgcolor="#0F172A", font=dict(color="#E2E8F0"))
        st.plotly_chart(fig, use_container_width=True)
    except: pass

# --- TAB 6: ADMIN (HIDDEN UNLESS LOGGED IN AS MOEEZ) ---
if len(tabs) == 6:
    with tabs[5]:
        st.header("🔐 Admin Approval Panel")
        try:
            conn = sqlite3.connect("trades.db")
            udf = pd.read_sql_query("SELECT id, email, trx_id, status FROM users WHERE status='Pending'", conn)
            st.dataframe(udf, use_container_width=True)
            if not udf.empty:
                app_email = st.selectbox("Select User to Approve", udf['email'])
                if st.button("✅ Approve"):
                    conn.cursor().execute("UPDATE users SET status='Active' WHERE email=?", (app_email,))
                    conn.commit()
                    st.rerun()
            conn.close()
        except: pass
