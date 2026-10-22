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
    /* Base styling */
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
    
    .calc-box { background-color: #0F172A; border: 1px solid #1E293B; padding: 24px; border-radius: 10px; margin-bottom: 20px; }
    .legal-box { background-color: #0B0F19; border: 1px solid #1E293B; padding: 20px; border-radius: 8px; font-size: 13px; color: #94A3B8; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect("trades.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, plan TEXT, trx_id TEXT, expiry_date TEXT, status TEXT)")
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
            <p style="color: #94A3B8;">Institutional quantitative models & financial calculators.</p>
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["🔑 Access Terminal", "💳 Buy Subscription"])
    with t1:
        email = st.text_input("Registered Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if email == ADMIN_EMAIL and pwd == "Admin@2026":
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                try:
                    conn = sqlite3.connect("trades.db")
                    row = conn.cursor().execute("SELECT password, status, expiry_date FROM users WHERE email=?", (email,)).fetchone()
                    if row and row[0] == pwd:
                        if row[1] == "Active" and pd.to_datetime(row[2]) > pd.Timestamp.now():
                            st.session_state.logged_in = True
                            st.session_state.user_email = email
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
        if st.button("Submit Registration", type="primary"):
            if r_email and r_pwd and r_trx:
                exp = (datetime.datetime.now() + datetime.timedelta(days=30 if r_plan=="Monthly" else 365)).strftime('%Y-%m-%d %H:%M:%S')
                try:
                    conn = sqlite3.connect("trades.db")
                    conn.cursor().execute("INSERT OR REPLACE INTO users (email, password, plan, trx_id, expiry_date, status) VALUES (?,?,?,?,?,?)", (r_email, r_pwd, r_plan, r_trx, exp, "Pending"))
                    conn.commit()
                    st.success("✅ Submitted! Waiting for admin approval.")
                except: pass
            else: st.warning("Fill all fields.")
    st.stop()

# ==========================================
# 4. POST-LOGIN MANDATORY AGREEMENT GATE
# ==========================================
if st.session_state.logged_in and not st.session_state.terms_accepted:
    if st.session_state.user_email == ADMIN_EMAIL:
        st.session_state.terms_accepted = True
        st.rerun()
        
    st.markdown("""
        <div style="max-width: 700px; margin: 40px auto; text-align: center;">
            <h2 style="color: #F59E0B;">⚠️ Mandatory Risk Agreement</h2>
            <div class="legal-box" style="text-align: left;">
                <strong>1. Educational Use Only:</strong> PSX Quant Terminal generates signals using historical algorithms and AI sentiment analysis. This is NOT certified financial advice.<br><br>
                <strong>2. Trading Risk:</strong> Stock market trading involves high capital risk. AI models can lag or trigger false signals. You assume full responsibility for your capital.<br><br>
                <strong>3. Non-Refundable:</strong> Activated subscriptions are strictly non-refundable.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("✅ I Agree & Understand — Enter Terminal", type="primary", use_container_width=True):
            st.session_state.terms_accepted = True
            st.rerun()
    st.stop()

# ==========================================
# 5. AUTO-SCROLLING TICKER MARQUEE & DATA
# ==========================================
TICKER_CONFIG = {
    "MCB": {"symbols": ["MCB.KA"], "base_price": 378.18},
    "FFC": {"symbols": ["FFC.KA"], "base_price": 534.42},
    "MEBL": {"symbols": ["MEBL.KA"], "base_price": 545.16},
    "OGDC": {"symbols": ["OGDC.KA"], "base_price": 300.01},
    "SYS": {"symbols": ["SYS.KA"], "base_price": 114.75}
}

def generate_mock_price(base):
    return round(base * (1 + np.random.uniform(-0.02, 0.02)), 2)

marquee_items = ""
for tkr, cfg in TICKER_CONFIG.items():
    p = generate_mock_price(cfg['base_price'])
    chg = ((p - cfg['base_price'])/cfg['base_price']) * 100
    color = "#10B981" if chg >= 0 else "#EF4444"
    arrow = "▲" if chg >= 0 else "▼"
    marquee_items += f"<div class='ticker-item'>{tkr} : Rs. {p} <span style='color: {color};'>{arrow} {abs(chg):.2f}%</span></div>"

st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {marquee_items}{marquee_items}
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 6. TERMINAL TABS
# ==========================================
tabs = st.tabs(["🧮 Calculators", "🎓 Quant Academy & Formulas", "📈 Live Dashboard", "🔐 Admin" if st.session_state.user_email == ADMIN_EMAIL else ""])

# --- CALCULATORS ---
with tabs[0]:
    st.header("🧮 Institutional Calculators")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("1. Dynamic Position Sizer")
        eq = st.number_input("Account Balance (PKR)", value=500000)
        risk = st.number_input("Risk Limit (%)", value=2.0)
        en = st.number_input("Entry Price", value=250.0)
        sl = st.number_input("Stop Loss Price", value=240.0)
        shares = int((eq * (risk/100)) / max(en - sl, 0.01))
        st.success(f"**Recommended Shares:** {shares:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("2. Graham Fair Value")
        eps = st.number_input("Earnings Per Share (EPS)", value=25.0)
        bvps = st.number_input("Book Value Per Share (BVPS)", value=120.0)
        val = np.sqrt(22.5 * eps * bvps)
        st.success(f"**Intrinsic Fair Value:** Rs. {val:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- QUANT ACADEMY & FORMULAS ---
with tabs[1]:
    st.header("🎓 Quant Academy: Formulas & Examples")
    
    st.markdown("### 1. The Benjamin Graham Intrinsic Value")
    st.markdown("Used by value investors to find the 'true' worth of a stock, regardless of current market hype. It blends a company's earnings with its physical book value.")
    st.latex(r"V = \sqrt{22.5 \times \text{EPS} \times \text{BVPS}}")
    st.markdown("""
    **Practical PSX Example:**
    * You are analyzing **FFC (Fauji Fertilizer)**.
    * The company's **EPS** (Earnings Per Share) is Rs. 25.
    * The company's **BVPS** (Book Value Per Share) is Rs. 120.
    * Calculation: $V = \sqrt{22.5 \times 25 \times 120} = \sqrt{67500} = 259.8$
    * **Conclusion:** The true fundamental value of FFC is Rs. 259.8. If the current PSX market price is Rs. 180, it is undervalued and a good buy.
    """)
    st.markdown("---")
    
    st.markdown("### 2. Dynamic Risk Position Sizing")
    st.markdown("Professional traders never guess how many shares to buy. They calculate exactly how many shares keep them under their maximum loss threshold if a trade goes wrong.")
    st.latex(r"\text{Shares} = \frac{\text{Account Capital} \times \text{Risk Percentage}}{\text{Entry Price} - \text{Stop Loss Price}}")
    st.markdown("""
    **Practical PSX Example:**
    * You have an account balance of **Rs. 500,000**.
    * You only want to risk **2%** (Rs. 10,000) on a single trade.
    * You want to buy **OGDC** at Rs. 100, but plan to sell if it drops to Rs. 95 (Stop Loss).
    * Calculation: $\text{Shares} = \frac{500,000 \times 0.02}{100 - 95} = \frac{10,000}{5} = 2000 \text{ Shares}$
    * **Conclusion:** You must buy exactly 2000 shares. If OGDC drops to your stop loss, you lose exactly Rs. 10,000 (your 2% limit).
    """)

# --- ADMIN PANEL ---
if st.session_state.user_email == ADMIN_EMAIL:
    with tabs[3]:
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
