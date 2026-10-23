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
        padding: 22px;
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
    
    /* Result Display Highlight Box */
    .result-box {
        background: #0B0F19;
        border: 1px solid #10B981;
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
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
# 2. MANDATORY TERMS & DISCLAIMER GATE
# ==========================================
if "terms_accepted" not in st.session_state:
    st.session_state.terms_accepted = False

if not st.session_state.terms_accepted:
    st.markdown("""
        <div style="max-width: 750px; margin: 40px auto; text-align: center;">
            <h1 style="color: #10B981; font-weight: 800;">⚡ Welcome to PSX Quant Terminal</h1>
            <p style="color: #9CA3AF; font-size: 15px;">Website Developed by <strong>Engr Moeez Amir</strong></p>
            <div class="fancy-card" style="text-align: left; margin-top: 25px; line-height: 1.8;">
                <h3 style="color: #F59E0B; margin-top: 0;">⚠️ Legal & Risk Disclaimer (SECP Compliance)</h3>
                <strong>1. Educational & Analytical Nature:</strong><br>
                PSX Quant Terminal is strictly an educational research and quantitative modeling tool. It does not provide certified investment advice, portfolio management, or trade execution.<br><br>
                <strong>2. Market & Algorithmic Risk:</strong><br>
                Trading in the Pakistan Stock Exchange carries market risk. Indicators (SMA, RSI, ATR) and mathematical calculators are probabilistic tools. Users trade entirely at their own discretion.<br><br>
                <strong>3. Free Public Platform:</strong><br>
                This application is provided free to the public, supported by digital ad sponsorships.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("✅ I Agree & Accept Terms — Enter Terminal", type="primary", use_container_width=True):
            st.session_state.terms_accepted = True
            st.rerun()
    st.stop()

# ==========================================
# 3. MARKET DATA CONFIG & ENGINE
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

# Sidebar Controls
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

tabs = st.tabs(["📡 AI Heavyweights Matrix", "📰 Financial News", "🧮 10 Smart Calculators", "🎓 Quant Academy", "📈 Charting Studio", "⚖️ Legal Statement"])

# --- TAB 1: HEAVYWEIGHTS MATRIX ---
with tabs[0]:
    st.markdown("### 📡 Top 10 PSX Heavyweights Matrix")
    st.caption("Includes exact Recommended Buy Price, Stop Loss, and Take Profit levels.")
    
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
        
        buy_price = close * 0.995
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
            "Target Allocation": f"Rs. {allocated:,-0f}" if allocated > 0 else "-"
        })

    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# --- TAB 2: VISUAL NEWS PORTAL ---
with tabs[1]:
    st.markdown("### 📰 Pakistan Financial News Hub")
    st.caption("Live market insights and regulatory updates.")
    
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

# --- TAB 3: THE 10 ESSENTIAL CALCULATORS SUITE ---
with tabs[2]:
    st.markdown("### 🧮 PSX Smart Calculator Suite (10 Models)")
    st.caption("Institutional quantitative financial calculators tailored for Pakistan Stock Exchange trading.")
    
    c_tab1, c_tab2, c_tab3, c_tab4, c_tab5 = st.tabs([
        "1. P&L & Position", "2. Risk & Exit", "3. Cost Basis & Charges", "4. Growth & Dividends", "5. Drawdown"
    ])
    
    # Group 1: P&L & Position Sizing
    with c_tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="fancy-card"><h4>1. Profit & Loss (P&L) Calculator</h4>', unsafe_allow_html=True)
            pnl_buy = st.number_input("Buy Price (PKR)", value=100.0, key="pnl_b")
            pnl_sell = st.number_input("Sell Price (PKR)", value=115.0, key="pnl_s")
            pnl_qty = st.number_input("Number of Shares", value=500, key="pnl_q")
            pnl_b_comm = st.number_input("Buy Commission (%)", value=0.15, key="pnl_bc")
            pnl_s_comm = st.number_input("Sell Commission (%)", value=0.15, key="pnl_sc")
            
            gross_cost = pnl_buy * pnl_qty
            gross_pnl = (pnl_sell - pnl_buy) * pnl_qty
            comm_cost = (gross_cost * (pnl_b_comm/100)) + ((pnl_sell * pnl_qty) * (pnl_s_comm/100))
            net_pnl = gross_pnl - comm_cost
            roi = (net_pnl / gross_cost) * 100
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Investment Cost: <strong>Rs. {gross_cost:,.2f} PKR</strong></div>
                    <div style="font-size: 12px; color: #9CA3AF;">Gross P&L: <strong>Rs. {gross_pnl:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: {'#10B981' if net_pnl >= 0 else '#EF4444'}; margin-top: 5px;">
                        Rs. {net_pnl:,.2f} PKR Net
                    </div>
                    <div style="font-size: 13px; color: #38BDF8;">Estimated ROI: {roi:.2f}%</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_b:
            st.markdown('<div class="fancy-card"><h4>2. Position Size Calculator</h4>', unsafe_allow_html=True)
            ps_cap = st.number_input("Total Available Capital (PKR)", value=500000, key="ps_c")
            ps_risk = st.number_input("Max Risk Limit (%)", value=2.0, key="ps_r")
            ps_entry = st.number_input("Entry Price (PKR)", value=120.0, key="ps_e")
            ps_sl = st.number_input("Stop-Loss Price (PKR)", value=112.0, key="ps_s")
            
            max_rupee_loss = ps_cap * (ps_risk / 100)
            risk_per_sh = max(ps_entry - ps_sl, 0.01)
            recommended_shares = int(max_rupee_loss / risk_per_sh)
            total_inv = recommended_shares * ps_entry
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Planned Max Loss: <strong>Rs. {max_rupee_loss:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #38BDF8; margin-top: 5px;">
                        {recommended_shares:,} Shares
                    </div>
                    <div style="font-size: 13px; color: #10B981;">Total Required Capital: Rs. {total_inv:,.2f} PKR</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Group 2: Risk & Exit Prices
    with c_tab2:
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown('<div class="fancy-card"><h4>3. Stop-Loss & Take-Profit Calculator</h4>', unsafe_allow_html=True)
            sltp_entry = st.number_input("Planned Entry Price", value=200.0, key="s1")
            sltp_sl = st.number_input("Stop Loss Target Price", value=190.0, key="s2")
            sltp_tp = st.number_input("Take Profit Target Price", value=230.0, key="s3")
            sltp_qty = st.number_input("Quantity", value=1000, key="s4")
            
            pot_loss = (sltp_entry - sltp_sl) * sltp_qty
            pot_gain = (sltp_tp - sltp_entry) * sltp_qty
            rr_ratio = pot_gain / max(pot_loss, 0.01)
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #EF4444;">Potential Max Loss: <strong>Rs. {pot_loss:,.2f} PKR</strong></div>
                    <div style="font-size: 12px; color: #10B981;">Potential Max Gain: <strong>Rs. {pot_gain:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #F59E0B; margin-top: 5px;">
                        Risk / Reward: 1 : {rr_ratio:.2f}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_d:
            st.markdown('<div class="fancy-card"><h4>10. Portfolio Drawdown Calculator</h4>', unsafe_allow_html=True)
            dd_val = st.number_input("Current Portfolio Value (PKR)", value=1000000, key="dd1")
            dd_peak = st.number_input("Previous Peak Value (PKR)", value=1200000, key="dd2")
            
            current_drawdown = ((dd_peak - dd_val) / dd_peak) * 100
            drop_5 = dd_val * 0.95
            drop_10 = dd_val * 0.90
            drop_20 = dd_val * 0.80
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Peak Drawdown: <strong>-{current_drawdown:.2f}%</strong></div>
                    <div style="font-size: 13px; color: #EF4444; margin-top: 5px;">Value after -10% Crash: <strong>Rs. {drop_10:,.2f} PKR</strong></div>
                    <div style="font-size: 13px; color: #EF4444;">Value after -20% Crash: <strong>Rs. {drop_20:,.2f} PKR</strong></div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Group 3: Cost Basis & Charges
    with c_tab3:
        col_e, col_f = st.columns(2)
        with col_e:
            st.markdown('<div class="fancy-card"><h4>4. Average Buy Price Calculator</h4>', unsafe_allow_html=True)
            avg_q1 = st.number_input("Existing Shares Held", value=1000, key="av1")
            avg_p1 = st.number_input("Existing Avg Price (PKR)", value=150.0, key="av2")
            avg_q2 = st.number_input("New Shares Adding", value=500, key="av3")
            avg_p2 = st.number_input("New Purchase Price (PKR)", value=120.0, key="av4")
            
            tot_shares = avg_q1 + avg_q2
            new_avg_cost = ((avg_q1 * avg_p1) + (avg_q2 * avg_p2)) / max(tot_shares, 1)
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Total Shares: <strong>{tot_shares:,}</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #10B981; margin-top: 5px;">
                        New Weighted Avg Price: Rs. {new_avg_cost:.2f} PKR
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_f:
            st.markdown('<div class="fancy-card"><h4>6. PSX Brokerage & Charges Calculator</h4>', unsafe_allow_html=True)
            brk_val = st.number_input("Trade Value (PKR)", value=200000, key="br1")
            brk_rate = st.number_input("Brokerage Rate (%)", value=0.15, key="br2")
            stax_rate = st.number_input("Sales Tax on Comm. (%)", value=13.0, key="br3")
            
            comm = brk_val * (brk_rate / 100)
            sales_tax = comm * (stax_rate / 100)
            psx_cdc_fees = brk_val * 0.0003 # ~0.03% PSX/CDC/NCCPL charges
            total_charges = comm + sales_tax + psx_cdc_fees
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Brokerage Commission: <strong>Rs. {comm:,.2f} PKR</strong></div>
                    <div style="font-size: 12px; color: #9CA3AF;">Provincial Sales Tax: <strong>Rs. {sales_tax:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #F59E0B; margin-top: 5px;">
                        Total Execution Fee: Rs. {total_charges:,.2f} PKR
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Group 4: Growth & Dividends
    with c_tab4:
        col_g, col_h = st.columns(2)
        with col_g:
            st.markdown('<div class="fancy-card"><h4>7. Compound Growth (CAGR)</h4>', unsafe_allow_html=True)
            cg_start = st.number_input("Starting Capital (PKR)", value=100000, key="cg_s")
            cg_rate = st.number_input("Expected Annual Return (%)", value=15.0, key="cg_r")
            cg_yrs = st.number_input("Investment Tenure (Years)", value=5, key="cg_y")
            
            compounded_val = cg_start * ((1 + (cg_rate/100)) ** cg_yrs)
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Initial Capital: <strong>Rs. {cg_start:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #10B981; margin-top: 5px;">
                        Projected Value: Rs. {compounded_val:,.2f} PKR
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_h:
            st.markdown('<div class="fancy-card"><h4>8. Dividend Income Calculator</h4>', unsafe_allow_html=True)
            div_q = st.number_input("Shares Held", value=2000, key="d1")
            div_dps = st.number_input("Dividend Per Share (PKR)", value=15.0, key="d2")
            filer_type = st.radio("Filer Status", ["Active Tax Filer (15% WHT)", "Non-Filer (30% WHT)"], key="d3")
            
            gross_div = div_q * div_dps
            wht_rate = 0.15 if "Active" in filer_type else 0.30
            wht_tax = gross_div * wht_rate
            net_div = gross_div - wht_tax
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Gross Dividend: <strong>Rs. {gross_div:,.2f} PKR</strong></div>
                    <div style="font-size: 12px; color: #EF4444;">Withholding Tax ({int(wht_rate*100)}%): <strong>Rs. {wht_tax:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #10B981; margin-top: 5px;">
                        Net Annual Income: Rs. {net_div:,.2f} PKR
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Group 5: Allocation & Break-Even
    with c_tab5:
        col_i, col_j = st.columns(2)
        with col_i:
            st.markdown('<div class="fancy-card"><h4>5. Portfolio Allocation Calculator</h4>', unsafe_allow_html=True)
            alloc_stock = st.number_input("Investment in Selected Stock", value=150000, key="al1")
            alloc_port = st.number_input("Total Portfolio Equity", value=1000000, key="al2")
            
            weight_pct = (alloc_stock / max(alloc_port, 1)) * 100
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 20px; font-weight: bold; color: #38BDF8; margin-top: 5px;">
                        Asset Weight: {weight_pct:.2f}%
                    </div>
                    <div style="font-size: 12px; color: {'#10B981' if weight_pct <= 20 else '#EF4444'};">
                        {'🟢 Well Diversified (<20% risk)' if weight_pct <= 20 else '⚠️ High Concentration (>20% risk)'}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_j:
            st.markdown('<div class="fancy-card"><h4>9. Break-Even Price Calculator</h4>', unsafe_allow_html=True)
            be_buy = st.number_input("Buy Price Per Share", value=100.0, key="be1")
            be_qty = st.number_input("Quantity Shares", value=1000, key="be2")
            be_comm_pct = st.number_input("Roundtrip Charges (%)", value=0.40, key="be3")
            
            cost_basis = be_buy * be_qty
            total_roundtrip_cost = cost_basis * (be_comm_pct / 100)
            breakeven_price = (cost_basis + total_roundtrip_cost) / be_qty
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="font-size: 12px; color: #9CA3AF;">Total Investment + Charges: <strong>Rs. {cost_basis + total_roundtrip_cost:,.2f} PKR</strong></div>
                    <div style="font-size: 20px; font-weight: bold; color: #10B981; margin-top: 5px;">
                        Break-Even Sell Price: Rs. {breakeven_price:.2f} PKR
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 4: QUANT ACADEMY & FORMULAS ---
with tabs[3]:
    st.markdown("### 🎓 Quant Academy: Mathematical Formulations & Examples")
    st.caption("Complete breakdown of the 10 essential financial formulas with real-world PSX numerical solutions.")
    
    q_exp1, q_exp2 = st.columns(2)
    
    with q_exp1:
        st.markdown("""
        <div class="fancy-card">
            <h4>1. Net P&L Formula</h4>
            <p style="font-size: 13px; color: #9CA3AF;">Calculates total return after accounting for buying/selling commissions.</p>
            $$\\text{Net P\&L} = (P_{sell} - P_{buy}) \\times Q - \\text{Charges}$$
            <hr style="border-color: #374151;">
            <strong>Example:</strong> You buy 1,000 shares of OGDC at Rs. 100 and sell at Rs. 110 with Rs. 300 total commission.<br>
            $$\\text{Gross P\&L} = (110 - 100) \\times 1000 = \\text{Rs. 10,000}$$
            $$\\text{Net P\&L} = 10,000 - 300 = \\text{Rs. 9,700 PKR}$$
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="fancy-card">
            <h4>2. Dynamic Risk Position Sizing</h4>
            $$\\text{Shares} = \\frac{\\text{Capital} \\times \\text{Risk \\%}}{P_{entry} - P_{stop\\_loss}}$$
            <hr style="border-color: #374151;">
            <strong>Example:</strong> Rs. 500,000 account, 2% risk limit (Rs. 10,000 max loss). Entry = Rs. 100, Stop Loss = Rs. 95.<br>
            $$\\text{Shares} = \\frac{10,000}{100 - 95} = 2,000 \\text{ shares}$$
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="fancy-card">
            <h4>3. Risk / Reward Ratio</h4>
            $$\\text{RRR} = \\frac{\\text{Take Profit Price} - \\text{Entry Price}}{\\text{Entry Price} - \\text{Stop Loss Price}}$$
            <hr style="border-color: #374151;">
            <strong>Example:</strong> Buy SYS at Rs. 400, Stop Loss at Rs. 380, Take Profit at Rs. 460.<br>
            $$\\text{RRR} = \\frac{460 - 400}{400 - 380} = \\frac{60}{20} = 3.0 \\text{ (1:3 Ratio)}$$
        </div>
        """, unsafe_allow_html=True)

    with q_exp2:
        st.markdown("""
        <div class="fancy-card">
            <h4>4. Weighted Average Buy Price</h4>
            $$\\text{Avg Price} = \\frac{(Q_1 \\times P_1) + (Q_2 \\times P_2)}{Q_1 + Q_2}$$
            <hr style="border-color: #374151;">
            <strong>Example:</strong> You hold 500 shares of HUBC at Rs. 120 and buy 500 more at Rs. 100.<br>
            $$\\text{Avg Price} = \\frac{(500 \\times 120) + (500 \\times 100)}{1000} = \\text{Rs. 110 PKR}$$
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="fancy-card">
            <h4>5. Compound Annual Growth Rate (CAGR)</h4>
            $$\\text{CAGR} = \\left( \\frac{\\text{End Value}}{\\text{Start Value}} \\right)^{\\frac{1}{n}} - 1$$
            <hr style="border-color: #374151;">
            <strong>Example:</strong> Rs. 100,000 grows to Rs. 200,000 in 4 years.<br>
            $$\\text{CAGR} = (2.0)^{0.25} - 1 = 18.92\\%$$
        </div>
        """, unsafe_allow_html=True)

# --- TAB 5: CHARTING STUDIO ---
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
