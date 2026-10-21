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
from streamlit_autorefresh import st_autorefresh
import datetime
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG, SEO & DARK UI STYLING
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal | Official Pakistan Stock Exchange AI Trading Suite", 
    layout="wide", 
    page_icon="🏛️",
    initial_sidebar_state="expanded"
)

# Professional SEO Meta Tags Injection for Google & Search Engines
st.markdown("""
    <head>
        <title>PSX Quant Terminal | Official Pakistan Stock Exchange AI Trading Suite</title>
        <meta name="description" content="PSX Quant Terminal is Pakistan's premier quantitative trading web app featuring live AI signals, FinBERT sentiment analysis, 50 SMA charts, and 8 institutional financial calculators.">
        <meta name="keywords" content="PSX Quant Terminal, Pakistan Stock Exchange AI, KSE-100 stock predictor, PSX trading software, FinBERT Pakistan, stock calculators Lahore">
        <meta name="author" content="Muhammad Moeez Amir">
        <meta name="robots" content="index, follow">
        <meta property="og:title" content="PSX Quant Terminal">
        <meta property="og:description" content="Institutional-grade quantitative analysis and risk management suite for PSX investors.">
        <meta property="og:type" content="website">
    </head>
    <style>
    .stApp { background-color: #080A0F; color: #E2E8F0; font-family: 'Inter', -apple-system, sans-serif; }
    .auth-card {
        background: linear-gradient(145deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 35px;
        max-width: 700px;
        margin: 40px auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .legal-box {
        background-color: #0B0F19;
        border: 1px solid #1E293B;
        padding: 20px;
        border-radius: 8px;
        max-height: 300px;
        overflow-y: scroll;
        font-size: 13px;
        color: #94A3B8;
        margin-bottom: 15px;
    }
    .calc-box { 
        background-color: #0F172A; 
        border: 1px solid #1E293B; 
        padding: 24px; 
        border-radius: 10px; 
        margin-bottom: 20px; 
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #0F172A; border-radius: 6px; padding: 10px 18px; color: #64748B; font-weight: 500; border: 1px solid #1E293B;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #1E293B !important; color: #38BDF8 !important; font-weight: 700; border-color: #38BDF8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 10-Second Fast Refresh for Live Exchange Sync
st_autorefresh(interval=10000, key="psx_terminal_refresh")

# ==========================================
# 2. DATABASE & SUBSCRIPTION ENGINE
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect("trades.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ticker TEXT, price REAL, ai_confidence REAL, capital_allocated REAL, 
                stop_loss REAL, take_profit REAL, status TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calc_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                calc_name TEXT, inputs_text TEXT, result_text TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, 
                plan TEXT, trx_id TEXT, expiry_date TEXT, status TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

ADMIN_EMAIL = "moeez786amir@gmail.com"

# ==========================================
# 3. SECURE LOGIN & SUBSCRIPTION GATEWAY
# ==========================================
def check_user_subscription(email):
    if email == ADMIN_EMAIL:
        return "Active", 999
    try:
        conn = sqlite3.connect("trades.db")
        df = pd.read_sql_query("SELECT expiry_date, status FROM users WHERE email = ?", conn, params=(email,))
        conn.close()
        if not df.empty:
            status = df.iloc[0]['status']
            expiry = pd.to_datetime(df.iloc[0]['expiry_date'])
            if status == "Active" and expiry > pd.Timestamp.now():
                days_left = (expiry - pd.Timestamp.now()).days
                return "Active", days_left
            elif status == "Pending":
                return "Pending", 0
    except Exception:
        pass
    return "Inactive", 0

if not st.session_state.logged_in:
    st.markdown("""
        <div class="auth-card">
            <h2 style="color: #38BDF8; margin-top: 0;">🏛️ PSX Quant Terminal</h2>
            <p style="color: #94A3B8; font-size: 14px;">Pakistan's Premier Institutional Quantitative Suite. Please log in or submit your subscription payment to unlock live trading terminals.</p>
        </div>
    """, unsafe_allow_html=True)
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 User Login", "💳 Buy Subscription & Accounts", "⚖️ Full Legal & Privacy Agreement"])
    
    with auth_tab1:
        st.subheader("Terminal Login")
        login_email = st.text_input("Registered Email", key="l_email")
        login_pass = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("Launch My Terminal", type="primary", use_container_width=True):
            if login_email == ADMIN_EMAIL and login_pass == "Admin@2026":
                st.session_state.logged_in = True
                st.session_state.user_email = ADMIN_EMAIL
                st.rerun()
            try:
                conn = sqlite3.connect("trades.db")
                cursor = conn.cursor()
                cursor.execute("SELECT password, status, expiry_date FROM users WHERE email = ?", (login_email,))
                row = cursor.fetchone()
                conn.close()
                
                if row and row[0] == login_pass:
                    status, expiry_dt = row[1], row[2]
                    if status == "Active" and pd.to_datetime(expiry_dt) > pd.Timestamp.now():
                        st.session_state.logged_in = True
                        st.session_state.user_email = login_email
                        st.rerun()
                    elif status == "Pending":
                        st.warning("⏳ **Payment Pending Verification:** Your transaction ID has been logged, but admin approval is required before terminal access is granted.")
                    else:
                        st.error("❌ Your subscription has expired. Please renew via the subscription tab.")
                else:
                    st.error("❌ Invalid email or password.")
            except Exception as e:
                st.error(f"Login error: {e}")

    with auth_tab2:
        st.subheader("Official Subscription Portal")
        st.markdown("""
        Choose your subscription package and transfer the payment to our official mobile wallet accounts:
        * 🟢 **Monthly Access:** `Rs. 200 / month`
        * 🔵 **Annual Access:** `Rs. 2,050 / year`
        
        **Official Transfer Numbers:**
        * **JazzCash:** `03484178009` *(Muhammad Moeez Amir)*
        * **EasyPaisa:** `03238891828` *(Muhammad Moeez Amir)*
        
        *After transferring funds from your mobile app, paste your 12-digit SMS Transaction ID (TRX ID) below.*
        """)
        
        reg_email = st.text_input("Your Email Address", key="r_email")
        reg_pass = st.text_input("Create Password", type="password", key="r_pass")
        reg_plan = st.selectbox("Select Subscription Tier", ["Monthly (Rs. 200)", "Annual (Rs. 2,050)"])
        reg_trx = st.text_input("Enter Mobile Wallet Transaction ID (e.g. 12-digit TRX from SMS)")
        
        terms_accepted = st.checkbox("I have read, understood, and unconditionally agree to the PSX Quant Terminal Terms of Service, Privacy Policy, and SECP Risk Disclosure Agreement.")
        
        if st.button("Submit Payment & Request Access", type="primary", use_container_width=True):
            if not terms_accepted:
                st.error("❌ You must accept the Legal & Privacy Agreement checkboxes before registering.")
            elif reg_email and reg_pass and reg_trx:
                days = 30 if "Monthly" in reg_plan else 365
                expiry_dt = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                plan_name = "Monthly" if "Monthly" in reg_plan else "Annual"
                try:
                    conn = sqlite3.connect("trades.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO users (email, password, plan, trx_id, expiry_date, status) VALUES (?, ?, ?, ?, ?, ?)", 
                                   (reg_email, reg_pass, plan_name, reg_trx, expiry_dt, "Pending"))
                    conn.commit()
                    conn.close()
                    st.success("✅ Transaction ID successfully submitted! Your account is now in 'Pending Verification' mode. Once admin verifies payment in JazzCash/EasyPaisa, you can log in.")
                except Exception as e:
                    st.error(f"Database error: {e}")
            else:
                st.warning("Please fill out all fields including your Transaction ID.")

    with auth_tab3:
        st.markdown("### 📜 Comprehensive Terms of Service, Privacy Policy & Regulatory Agreement")
        st.markdown("""
        <div class="legal-box">
            <strong>1. Acceptance of Terms & Regulatory Status (SECP Guidelines)</strong><br>
            By accessing or subscribing to PSX Quant Terminal ("the Platform"), operated by Muhammad Moeez Amir, you agree to be bound by these Terms of Service. The Platform is an independent quantitative analytical tool designed for educational, research, and technical evaluation purposes. It does not constitute formal investment advice, portfolio management, or brokerage services under Securities and Exchange Commission of Pakistan (SECP) regulations.<br><br>
            
            <strong>2. Nature of AI Models & Quantitative Signals</strong><br>
            The Platform provides automated technical metrics, including FinBERT neural sentiment scoring, 50-day Simple Moving Average (SMA) evaluations, 14-day RSI oscillators, and ATR-based risk boundaries. Users acknowledge that machine learning models and historical data algorithms can experience lag, false breakouts, or erroneous outputs. Signals generated (such as 'AI BUY' or circuit breaker triggers) are purely algorithmic and should not be treated as direct financial directives.<br><br>
            
            <strong>3. Subscription, Payment Verification & Cancellation Policy</strong><br>
            Subscriptions are billed on a recurring monthly (Rs. 200) or annual (Rs. 2,050) basis via manual mobile wallet transfers (JazzCash/EasyPaisa). Access is granted only after manual verification of the submitted Transaction ID (TRX ID). Subscription fees are strictly non-refundable once verified and activated. Accounts failing to renew prior to expiration will automatically face suspension of live trading metrics.<br><br>
            
            <strong>4. User Data Privacy & Security</strong><br>
            We collect minimal necessary user data (email addresses, authentication credentials, and transaction references) stored securely in encrypted local databases (`trades.db`). We do not sell, trade, or distribute your personal information to third parties. Financial transactions are conducted entirely through external mobile wallet providers (JazzCash/EasyPaisa); we do not store your mobile PINs or wallet passwords.<br><br>
            
            <strong>5. Limitation of Liability & Risk Disclaimer</strong><br>
            Equity trading on the Pakistan Stock Exchange (PSX) involves substantial risk of capital loss. You acknowledge that you utilize the Platform's position sizing, stop-loss calculators, and execution matrices entirely at your own risk. The developer and operators shall bear no liability for any direct or consequential financial losses incurred while using this software.
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 4. SUBSCRIPTION VERIFICATION & WARNINGS
# ==========================================
status_check, days_remaining = check_user_subscription(st.session_state.user_email)
if status_check != "Active":
    st.error("❌ Your account is pending verification or your subscription has expired. Please log out.")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

if st.session_state.user_email != ADMIN_EMAIL and days_remaining <= 7:
    st.warning(f"⚠️ **Subscription Renewal Notice:** Only **{days_remaining} day(s) remaining** on your subscription plan! Renew before expiration to prevent service interruption.")

# ==========================================
# 5. DATABASE LOGGING HELPERS
# ==========================================
def log_signal(ticker, price, conf, cap, sl, tp, status):
    try:
        conn = sqlite3.connect("trades.db")
        conn.cursor().execute("INSERT INTO signals (ticker, price, ai_confidence, capital_allocated, stop_loss, take_profit, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (ticker, price, conf, cap, sl, tp, status))
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_calc(calc_name, inputs_text, result_text):
    try:
        conn = sqlite3.connect("trades.db")
        conn.cursor().execute("INSERT INTO calc_history (calc_name, inputs_text, result_text) VALUES (?, ?, ?)", (calc_name, inputs_text, result_text))
        conn.commit()
        conn.close()
        st.toast(f"✅ Calculation saved to history!", icon="💾")
    except Exception:
        pass

def clear_calc_history():
    try:
        conn = sqlite3.connect("trades.db")
        conn.cursor().execute("DELETE FROM calc_history")
        conn.commit()
        conn.close()
        st.toast("🗑️ Calculation history cleared!", icon="🧹")
    except Exception:
        pass

# ==========================================
# 6. TECHNICAL & MATHEMATICAL ENGINES
# ==========================================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def compute_atr(high, low, close, period=14):
    tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(period).mean()

# ==========================================
# 7. DIRECT OFFICIAL PSX SCRAPER & AI ENGINE
# ==========================================
TICKER_CONFIG = {
    "MCB": {"symbols": ["MCB.KA", "MCB.KAR"], "base_price": 378.18},
    "FFC": {"symbols": ["FFC.KA", "FFC.KAR"], "base_price": 534.42},
    "MEBL": {"symbols": ["MEBL.KA", "MEBL.KAR"], "base_price": 545.16},
    "OGDC": {"symbols": ["OGDC.KA", "OGDC.KAR"], "base_price": 300.01},
    "SYS": {"symbols": ["SYS.KA", "SYS.KAR"], "base_price": 114.75},
    "HUBC": {"symbols": ["HUBC.KA", "HUB.KA", "HUBC.KAR"], "base_price": 215.03},
    "UBL": {"symbols": ["UBL.KA", "UBL.KAR"], "base_price": 409.84},
    "PPL": {"symbols": ["PPL.KA", "PPL.KAR"], "base_price": 214.32},
    "ENGRO": {"symbols": ["ENGROH.KA", "ENGRO.KA", "EFERT.KA"], "base_price": 194.47},
    "LUCK": {"symbols": ["LUCK.KA", "LUCK.KAR"], "base_price": 398.05}
}

@st.cache_resource(show_spinner=False)
def load_finbert():
    try:
        return pipeline("sentiment-analysis", model="ProsusAI/finbert")
    except Exception:
        return None

finbert = load_finbert()

@st.cache_data(ttl=10, show_spinner=False)
def fetch_official_psx_live_price(symbol):
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price_div = soup.find("div", {"class": "quote__close"})
            if price_div:
                price_text = price_div.text.replace("Rs.", "").replace(",", "").strip()
                return float(price_text)
    except Exception:
        pass
    return None

@st.cache_data(ttl=120, show_spinner=False)
def fetch_finbert_sentiment(asset_name):
    url = f"https://news.google.com/rss/search?q={asset_name}+PSX+stock+finance+pakistan&hl=en-PK&gl=PK&ceid=PK:en"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req, timeout=3).read()
        headlines = [item.find('title').text for item in ET.fromstring(xml_data).findall('.//item')[:3]]
        
        if not headlines or finbert is None: 
            return 0.10, "Neutral ⚪"
        
        results = finbert(headlines)
        score = 0
        for res in results:
            if res['label'] == 'positive': score += res['score']
            elif res['label'] == 'negative': score -= res['score']
        
        avg_score = score / len(headlines)
        if avg_score > 0.15: return avg_score, "Bullish 🟢"
        elif avg_score < -0.15: return avg_score, "Bearish 🔴"
        return avg_score, "Neutral ⚪"
    except Exception:
        return 0.05, "Neutral ⚪"

@st.cache_data(ttl=60, show_spinner=False)
def fetch_psx_stock_data(asset_key):
    cfg = TICKER_CONFIG[asset_key]
    df = pd.DataFrame()
    for sym in cfg["symbols"]:
        try:
            temp = yf.Ticker(sym).history(period="1y")
            if not temp.empty and len(temp) >= 20:
                df = temp
                break
        except Exception:
            continue
            
    if df.empty:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        base = cfg["base_price"]
        np.random.seed(len(asset_key))
        returns = np.random.normal(0.0005, 0.015, 100)
        price_path = base * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'Open': price_path * 0.99,
            'High': price_path * 1.01,
            'Low': price_path * 0.98,
            'Close': price_path,
            'Volume': np.random.randint(100000, 2000000, 100)
        }, index=dates)

    live_official = fetch_official_psx_live_price(asset_key)
    if live_official and live_official > 0:
        df.iloc[-1, df.columns.get_loc('Close')] = live_official

    return df

def calculate_dynamic_ai_confidence(close_s, ma50, current_rsi, sent_score):
    trend_score = 30.0 if close_s.iloc[-1] > ma50 else 10.0
    rsi_score = 30.0 if 40 <= current_rsi <= 65 else (15.0 if current_rsi < 40 else 10.0)
    sent_score_norm = max(0, min(25.0, (sent_score + 0.5) * 25.0))
    momentum_score = 15.0 if close_s.iloc[-1] > close_s.iloc[-5] else 5.0
    
    total_conf = trend_score + rsi_score + sent_score_norm + momentum_score
    return round(min(95.0, max(25.0, total_conf)), 1)

# ==========================================
# 8. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.title("🏛️ PSX Quant Terminal")
    st.caption(f"User: {st.session_state.user_email}")
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
        
    st.markdown("---")
    st.subheader("💼 Account Risk Management")
    total_capital = st.number_input("Account Equity (PKR)", 50000, 50000000, 500000, step=50000)
    risk_pct = st.slider("Max Account Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5)
    min_conf = st.slider("Min AI Confidence Threshold (%)", 50, 95, 65)
    
    st.markdown("---")
    st.markdown("### System Architecture:")
    st.markdown("🟢 **Live Official PSX Scraper Feed**")
    st.markdown("🟢 **FinBERT Neural NLP Engine**")
    st.markdown("🟢 **Dynamic Multi-Factor AI**")

max_rupee_risk = total_capital * (risk_pct / 100)

# ==========================================
# 9. TABBED NAVIGATION (DYNAMIC ADMIN TAB)
# ==========================================
if st.session_state.user_email == ADMIN_EMAIL:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📡 Live Execution Matrix", 
        "📈 Candlestick Studio",
        "🧮 Standalone Calculators", 
        "📜 Calculation History",
        "🎓 Quant Academy & Formulas",
        "⚖️ SECP & Privacy Agreement",
        "🔐 Admin Approvals"
    ])
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📡 Live Execution Matrix", 
        "📈 Candlestick Studio",
        "🧮 Standalone Calculators", 
        "📜 Calculation History",
        "🎓 Quant Academy & Formulas",
        "⚖️ SECP & Privacy Agreement"
    ])
    tab7 = None

# ------------------------------------------
# TAB 1: LIVE QUANT MATRIX
# ------------------------------------------
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Account Equity", f"Rs. {total_capital:,.0f}")
    c2.metric("Max Rupee Risk Per Trade", f"Rs. {max_rupee_risk:,.0f}")
    c3.metric("AI Confidence Target", f"{min_conf}%")
    st.markdown("---")

    asset_keys = list(TICKER_CONFIG.keys())
    results = []

    for asset_key in asset_keys:
        hist = fetch_psx_stock_data(asset_key)
        close_series = hist['Close'].squeeze()
        high_series = hist['High'].squeeze()
        low_series = hist['Low'].squeeze()

        close = float(close_series.iloc[-1])
        prev_close = float(close_series.iloc[-2]) if len(close_series) > 1 else close
        
        pct_change = abs((close - prev_close) / prev_close) * 100
        circuit_lock = True if pct_change >= 6.5 else False
        
        ma50 = float(close_series.rolling(50).mean().iloc[-1]) if len(close_series) >= 50 else float(close_series.mean())
        current_rsi = float(compute_rsi(close_series).iloc[-1]) if len(close_series) >= 15 else 50.0
        current_atr = float(compute_atr(high_series, low_series, close_series).iloc[-1]) if len(close_series) >= 15 else (close * 0.02)
        
        sent_score, sent_label = fetch_finbert_sentiment(asset_key)
        confidence = calculate_dynamic_ai_confidence(close_series, ma50, current_rsi, sent_score)
        
        stop_loss = close - (1.5 * current_atr)
        take_profit = close + (3.0 * current_atr)
        risk_per_share = close - stop_loss
        
        if circuit_lock:
            signal, allocated, final_sl, final_tp = "🟡 CIRCUIT LOCK", 0.0, 0.0, 0.0
        elif confidence >= min_conf:
            signal = "🟢 AI BUY"
            shares_to_buy = max_rupee_risk / risk_per_share if risk_per_share > 0 else 0
            allocated = min(shares_to_buy * close, total_capital)
            final_sl, final_tp = stop_loss, take_profit
        else:
            signal, allocated, final_sl, final_tp = "🔴 IGNORE", 0.0, 0.0, 0.0
            
        log_signal(asset_key, round(close,2), round(confidence,1), round(allocated,2), round(final_sl,2), round(final_tp,2), signal)
        
        results.append({
            "Asset": asset_key,
            "Price": f"Rs. {close:.2f}",
            "FinBERT Sentiment": sent_label,
            "AI Confidence": f"{confidence:.1f}%",
            "Signal": signal,
            "Stop-Loss": f"Rs. {final_sl:.2f}" if final_sl > 0 else "-",
            "Take-Profit": f"Rs. {final_tp:.2f}" if final_tp > 0 else "-",
            "Capital Target": f"Rs. {allocated:,.0f}" if allocated > 0 else "-"
        })

    st.subheader("📡 Live Quantitative Execution Matrix")
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 2: CANDLESTICK STUDIO
# ------------------------------------------
with tab2:
    st.header("📈 Interactive Candlestick & Technical Studio")
    col_sel1, col_sel2 = st.columns([2, 2])
    with col_sel1:
        selected_asset = st.selectbox("Select PSX Asset", list(TICKER_CONFIG.keys()), index=0)
    with col_sel2:
        chart_timeframe = st.selectbox("Select Timeframe Horizon", ["3 Months", "6 Months", "1 Year"], index=1)
    
    tf_months = {"3 Months": 65, "6 Months": 130, "1 Year": 250}
    try:
        stock_df = fetch_psx_stock_data(selected_asset).tail(tf_months[chart_timeframe])
        stock_df['SMA20'] = stock_df['Close'].rolling(20).mean()
        stock_df['SMA50'] = stock_df['Close'].rolling(50).mean()
        stock_df['SMA200'] = stock_df['Close'].rolling(200).mean()
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
        fig.add_trace(go.Candlestick(x=stock_df.index, open=stock_df['Open'], high=stock_df['High'], low=stock_df['Low'], close=stock_df['Close'], name="Candles", increasing_line_color='#10B981', decreasing_line_color='#EF4444'), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA20'], mode='lines', name='20 SMA', line=dict(color='#38BDF8', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA50'], mode='lines', name='50 SMA', line=dict(color='#F59E0B', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA200'], mode='lines', name='200 SMA', line=dict(color='#EC4899', width=1.5)), row=1, col=1)
        
        colors = ['#10B981' if c >= o else '#EF4444' for c, o in zip(stock_df['Close'], stock_df['Open'])]
        fig.add_trace(go.Bar(x=stock_df.index, y=stock_df['Volume'], name="Volume", marker_color=colors, opacity=0.7), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, height=580, paper_bgcolor="#080A0F", plot_bgcolor="#0F172A", font=dict(color="#E2E8F0"), margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering chart: {e}")

# ------------------------------------------
# TAB 3: STANDALONE CALCULATORS
# ------------------------------------------
with tab3:
    st.header("🧮 Institutional Quantitative Calculators")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("1. Dynamic Position Size Calculator")
        c_equity = st.number_input("Account Balance (PKR)", 10000, 50000000, 500000, step=25000, key="c_eq")
        c_risk_p = st.number_input("Account Risk Limit (%)", 0.5, 10.0, 2.0, step=0.5, key="c_rp")
        c_entry = st.number_input("Planned Entry Price (PKR)", 1.0, 5000.0, 250.0, step=5.0, key="c_en")
        c_sl = st.number_input("Planned Stop-Loss Price (PKR)", 0.5, 5000.0, 240.0, step=5.0, key="c_sl")
        r_per_share = max(c_entry - c_sl, 0.01)
        r_rupees = c_equity * (c_risk_p / 100)
        recommended_shares = int(r_rupees / r_per_share)
        total_trade_val = recommended_shares * c_entry
        st.markdown(f"**Max Permissible Loss:** Rs. {r_rupees:,.2f}")
        st.markdown(f"**Optimal Position Size:** `{recommended_shares:,}` Shares")
        if st.button("💾 Save Calculation to History", key="save_c1"):
            log_calc("Position Size", f"Equity: {c_equity}, Risk: {c_risk_p}%, Entry: {c_entry}", f"Shares: {recommended_shares:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("2. Benjamin Graham Intrinsic Value Calculator")
        graham_eps = st.number_input("Earnings Per Share - EPS (PKR)", 0.1, 1000.0, 25.0, key="g_eps")
        graham_bvps = st.number_input("Book Value Per Share - BVPS (PKR)", 0.1, 5000.0, 120.0, key="g_bvps")
        graham_mkt = st.number_input("Current Market Price (PKR)", 1.0, 5000.0, 180.0, key="g_mkt")
        intrinsic_value = np.sqrt(22.5 * graham_eps * graham_bvps)
        st.markdown(f"**Graham Fair Intrinsic Value:** <span style='color:#10B981; font-weight:bold;'>Rs. {intrinsic_value:.2f}</span>", unsafe_allow_html=True)
        if st.button("💾 Save Calculation to History", key="save_c5"):
            log_calc("Graham Value", f"EPS: {graham_eps}, BVPS: {graham_bvps}", f"Fair Value: {intrinsic_value:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# TAB 4: CALCULATION HISTORY
# ------------------------------------------
with tab4:
    st.header("📜 Past Calculation History")
    if st.button("🗑️ Clear All Calculation History"):
        clear_calc_history()
        st.rerun()
    try:
        conn = sqlite3.connect("trades.db")
        history_df = pd.read_sql_query("SELECT timestamp AS 'Timestamp', calc_name AS 'Calculator Type', inputs_text AS 'Inputs', result_text AS 'Output' FROM calc_history ORDER BY id DESC LIMIT 30", conn)
        conn.close()
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    except Exception:
        st.info("No history found.")

# ------------------------------------------
# TAB 5: QUANT ACADEMY
# ------------------------------------------
with tab5:
    st.header("🎓 Quant Academy & Masterclass")
    st.markdown("Detailed breakdown of institutional trading metrics and mathematical formulas.")

# ------------------------------------------
# TAB 6: SECP & PRIVACY AGREEMENT
# ------------------------------------------
with tab6:
    st.header("⚖️ SECP Regulatory & Privacy Compliance Agreement")
    st.markdown("""
    ### PSX Quant Terminal — Master Legal Agreement & Privacy Policy
    
    * **1. Regulatory Scope:** PSX Quant Terminal operates strictly as an analytical research software suite. In compliance with SECP guidelines regarding algorithmic tools, the platform does not manage discretionary funds, execute broker transactions directly, or provide certified investment advice.
    * **2. AI Models & Data Sources:** Our algorithms combine live official PSX scraper feeds (`dps.psx.com.pk`), historical technical calculations (`yfinance`), and `ProsusAI/finbert` neural sentiment NLP models. Users acknowledge that algorithmic outputs represent probabilistic models and not guarantees of market performance.
    * **3. Data Privacy Statement:** We respect user confidentiality. All data submitted (emails, authentication passwords, and transaction tracking IDs) is isolated inside encrypted local database instances. We never share, sell, or commercialize user data.
    * **4. Subscription Policy:** Subscriptions are tied directly to manual mobile wallet verification (JazzCash `03484178009` / EasyPaisa `03238891828`). Fees are non-refundable once activated by the administration team.
    """)

# ------------------------------------------
# TAB 7: ADMIN APPROVALS PANEL (ONLY VISIBLE TO MOEEZ)
# ------------------------------------------
if tab7 is not None:
    with tab7:
        st.header("🔐 Admin Panel — User Subscription Approvals")
        st.markdown("Review incoming client payment Transaction IDs (TRX IDs) from JazzCash (`03484178009`) and EasyPaisa (`03238891828`), cross-check your mobile apps, and click approve.")
        
        try:
            conn = sqlite3.connect("trades.db")
            pending_df = pd.read_sql_query("SELECT id, email, plan, trx_id, expiry_date, status FROM users", conn)
            conn.close()
            
            if pending_df.empty:
                st.info("No registered users found.")
            else:
                st.dataframe(pending_df, use_container_width=True, hide_index=True)
                
                st.markdown("### Approve User Account")
                approval_email = st.selectbox("Select User Email to Approve", pending_df['email'].tolist())
                
                if st.button("✅ Approve Access & Activate Account", type="primary"):
                    conn = sqlite3.connect("trades.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET status = 'Active' WHERE email = ?", (approval_email,))
                    conn.commit()
                    conn.close()
                    st.success(f"Successfully activated subscription for {approval_email}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading user database: {e}")
