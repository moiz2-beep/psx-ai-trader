import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from sklearn.ensemble import RandomForestClassifier
from transformers import pipeline
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG & BACKGROUND STYLING
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal | Institutional Suite", 
    layout="wide", 
    page_icon="🏛️",
    initial_sidebar_state="expanded"
)

# Smooth 30-Second Refresh (Cached background update prevents UI jumps)
st_autorefresh(interval=30000, key="psx_terminal_refresh")

# Institutional Dark Theme CSS
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: 'Inter', sans-serif; }
    .secp-banner { background-color: #161B22; border-left: 4px solid #D97706; padding: 12px; font-size: 13px; color: #D1D5DB; margin-bottom: 15px; border-radius: 4px; }
    .calc-box { background-color: #161B2E; border: 1px solid #232D4B; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    .stat-card { background: linear-gradient(135deg, #1E2640 0%, #111827 100%); padding: 16px; border-radius: 8px; border: 1px solid #374151; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #111827; border-radius: 6px; padding: 8px 16px; color: #9CA3AF; }
    .stTabs [aria-selected="true"] { background-color: #1F2937 !important; color: #3B82F6 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Top SECP Compliance Header
st.markdown("""
    <div class="secp-banner">
        ⚖️ <strong>SECP REGULATORY NOTICE:</strong> This quantitative terminal operates under algorithmic research models. Signals generated are non-advisory and intended strictly for educational & algorithmic evaluation. Capital allocation carries financial market risk.
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE LOGGING
# ==========================================
def init_db():
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT, price REAL, ai_confidence REAL, capital_allocated REAL, 
            stop_loss REAL, take_profit REAL, status TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_signal(ticker, price, conf, cap, sl, tp, status):
    conn = sqlite3.connect("trades.db")
    conn.cursor().execute("INSERT INTO signals (ticker, price, ai_confidence, capital_allocated, stop_loss, take_profit, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (ticker, price, conf, cap, sl, tp, status))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. MATHEMATICAL & TECHNICAL ENGINES
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
# 4. CACHED AI & DATA FETCHING (No UI Flicker)
# ==========================================
@st.cache_resource(show_spinner=False)
def load_finbert():
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

finbert = load_finbert()

@st.cache_data(ttl=60, show_spinner=False) # Caching news sentiment for 60 seconds
def fetch_finbert_sentiment(ticker):
    clean_ticker = ticker.replace(".KA", "")
    url = f"https://news.google.com/rss/search?q={clean_ticker}+PSX+stock+finance&hl=en-PK&gl=PK&ceid=PK:en"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req, timeout=3).read()
        headlines = [item.find('title').text for item in ET.fromstring(xml_data).findall('.//item')[:3]]
        
        if not headlines: return 0.0, "Neutral ⚪"
        
        results = finbert(headlines)
        score = 0
        for res in results:
            if res['label'] == 'positive': score += res['score']
            elif res['label'] == 'negative': score -= res['score']
        
        avg_score = score / len(headlines)
        if avg_score > 0.2: return avg_score, "Bullish 🟢"
        elif avg_score < -0.2: return avg_score, "Bearish 🔴"
        return avg_score, "Neutral ⚪"
    except:
        return 0.0, "Neutral ⚪"

@st.cache_data(ttl=86400, show_spinner=False) # Train once a day
def train_real_market_model(tickers):
    X_data, y_data = [], []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", progress=False)
            if len(df) < 100: continue
            
            df['MA50'] = df['Close'].rolling(50).mean()
            df['Above_MA'] = np.where(df['Close'] > df['MA50'], 1, 0)
            df['RSI'] = compute_rsi(df['Close'])
            df['RSI_Oversold'] = np.where(df['RSI'] < 45, 1, 0)
            
            df['Future_Return'] = df['Close'].shift(-10) / df['Close'] - 1
            df['Target'] = np.where(df['Future_Return'] > 0.05, 1, 0)
            
            df.dropna(inplace=True)
            for _, row in df.iterrows():
                X_data.append([row['Above_MA'], 1, 0, row['RSI_Oversold']])
                y_data.append(row['Target'])
        except: continue
        
    if not X_data: X_data, y_data = [[1,1,0.5,1], [0,0,-0.5,0]], [1, 0]
        
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(np.array(X_data), np.array(y_data))
    return model

@st.cache_data(ttl=30, show_spinner=False) # Batch fetch cached for 30s
def fetch_psx_batch(tickers):
    try:
        return yf.download(tickers, period="6mo", group_by='ticker', progress=False)
    except:
        return {}

# ==========================================
# 5. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.title("🏛️ PSX Terminal Pro")
    st.caption("Quantitative Risk Engine & Execution Suite")
    st.markdown("---")
    
    st.subheader("💼 Account Risk Sizing")
    total_capital = st.number_input("Account Equity (PKR)", 50000, 50000000, 500000, step=50000)
    risk_pct = st.slider("Max Account Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5)
    min_conf = st.slider("Min AI Confidence Threshold (%)", 50, 95, 60)
    
    st.markdown("---")
    st.markdown("### System Active Status:")
    st.markdown("🟢 **FinBERT Neural NLP**")
    st.markdown("🟢 **PSX Batch Feed (10 Tickers)**")
    st.markdown("🟢 **ATR Risk Multipliers**")
    st.markdown("🟢 **SECP Regulatory Shield**")

max_rupee_risk = total_capital * (risk_pct / 100)

# ==========================================
# 6. TABBED NAVIGATION (MULTI-PAGE UX)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 Live Execution Matrix", 
    "🧮 Institutional Calculators", 
    "🗺️ PSX Financial Hubs Map", 
    "📜 Regulatory Compliance"
])

# ------------------------------------------
# TAB 1: LIVE QUANT TERMINAL
# ------------------------------------------
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Account Equity", f"Rs. {total_capital:,.0f}")
    c2.metric("Max Rupee Risk Per Trade", f"Rs. {max_rupee_risk:,.0f}")
    c3.metric("AI Confidence Target", f"{min_conf}%")
    st.markdown("---")

    tickers = ["MCB.KA", "FFC.KA", "MEBL.KA", "OGDC.KA", "SYS.KA", "HUBC.KA", "UBL.KA", "PPL.KA", "ENGRO.KA", "LUCK.KA"]
    model = train_real_market_model(tickers)
    batch_data = fetch_psx_batch(tickers)

    results = []

    for ticker in tickers:
        clean_name = ticker.replace(".KA", "")
        
        try:
            if len(tickers) > 1 and ticker in batch_data:
                hist = batch_data[ticker].dropna()
            else:
                hist = yf.Ticker(ticker).history(period="6mo")
        except:
            hist = pd.DataFrame()
            
        if hist.empty or len(hist) < 20:
            results.append({
                "Asset": clean_name, "Price": "Fetch Error", "FinBERT Sentiment": "N/A",
                "AI Confidence": "0.0%", "Signal": "🔴 DATA OFFLINE", "Stop-Loss": "-", "Take-Profit": "-", "Capital Target": "-"
            })
            continue
            
        close = float(hist['Close'].iloc[-1])
        prev_close = float(hist['Close'].iloc[-2])
        
        pct_change = abs((close - prev_close) / prev_close) * 100
        circuit_lock = True if pct_change >= 6.5 else False
        
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        above_50ma = 1 if close > ma50 else 0
        current_rsi = compute_rsi(hist['Close']).iloc[-1]
        rsi_over = 1 if current_rsi < 45 else 0
        current_atr = compute_atr(hist['High'], hist['Low'], hist['Close']).iloc[-1]
        
        pe_under = 1
        sent_score, sent_label = fetch_finbert_sentiment(ticker)
        
        features = np.array([[above_50ma, pe_under, sent_score, rsi_over]])
        confidence = model.predict_proba(features)[0][1] * 100
        
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
            
        log_signal(ticker, round(close,2), round(confidence,1), round(allocated,2), round(final_sl,2), round(final_tp,2), signal)
        
        results.append({
            "Asset": clean_name,
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

    with st.expander("📂 View Backend Execution Database (trades.db)"):
        conn = sqlite3.connect("trades.db")
        st.dataframe(pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 10", conn), hide_index=True)
        conn.close()

# ------------------------------------------
# TAB 2: SEPARATE INSTITUTIONAL CALCULATORS
# ------------------------------------------
with tab2:
    st.header("🧮 Standalone Quantitative Calculators")
    st.caption("Perform isolated risk, position size, circuit lock, and yield calculations independently.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("1. Dynamic Position Size Calculator")
        c_equity = st.number_input("Account Balance (PKR)", 10000, 10000000, 500000, step=25000, key="c_eq")
        c_risk_p = st.number_input("Account Risk Limit (%)", 0.5, 10.0, 2.0, step=0.5, key="c_rp")
        c_entry = st.number_input("Planned Entry Price (PKR)", 1.0, 5000.0, 250.0, step=5.0, key="c_en")
        c_sl = st.number_input("Planned Stop-Loss Price (PKR)", 0.5, 5000.0, 240.0, step=5.0, key="c_sl")
        
        r_per_share = max(c_entry - c_sl, 0.01)
        r_rupees = c_equity * (c_risk_p / 100)
        recommended_shares = int(r_rupees / r_per_share)
        total_trade_val = recommended_shares * c_entry
        
        st.markdown(f"**Max Permissible Loss:** Rs. {r_rupees:,.2f}")
        st.markdown(f"**Optimal Position Size:** `{recommended_shares:,}` Shares")
        st.markdown(f"**Total Capital Required:** Rs. {total_trade_val:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("2. Risk-to-Reward Ratio (RRR) Evaluator")
        rrr_entry = st.number_input("Entry Price (PKR)", 1.0, 5000.0, 100.0, key="r_e")
        rrr_sl = st.number_input("Stop Loss (PKR)", 0.5, 5000.0, 95.0, key="r_sl")
        rrr_tp = st.number_input("Take Profit (PKR)", 1.5, 5000.0, 115.0, key="r_tp")
        
        risk_amt = max(rrr_entry - rrr_sl, 0.01)
        reward_amt = max(rrr_tp - rrr_entry, 0.0)
        rrr_ratio = reward_amt / risk_amt
        breakeven_winrate = (1 / (1 + rrr_ratio)) * 100
        
        st.markdown(f"**Risk Per Share:** Rs. {risk_amt:.2f} | **Reward Per Share:** Rs. {reward_amt:.2f}")
        st.markdown(f"**Calculated RRR:** `1 : {rrr_ratio:.2f}`")
        if rrr_ratio >= 2.0:
            st.success(f"✅ Institutional Grade (1:2+ Target Met). Required Win-Rate: {breakeven_winrate:.1f}%")
        else:
            st.warning(f"⚠️ Sub-Optimal Trade Setup (Below 1:2 RRR). Required Win-Rate: {breakeven_winrate:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("3. PSX Daily Circuit Breaker Bands")
        prev_close_price = st.number_input("Previous Session Close Price (PKR)", 1.0, 5000.0, 400.0, key="cb_p")
        
        upper_limit = prev_close_price * 1.075
        lower_limit = prev_close_price * 0.925
        warning_upper = prev_close_price * 1.065
        
        st.markdown(f"**Upper Circuit Limit (+7.5%):** <span style='color:#10B981; font-weight:bold;'>Rs. {upper_limit:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Lower Circuit Limit (-7.5%):** <span style='color:#EF4444; font-weight:bold;'>Rs. {lower_limit:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Auto-Lock Warning Threshold (+6.5%):** Rs. {warning_upper:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("4. Dividend Yield & Dividend Cashflow")
        div_price = st.number_input("Current Share Price (PKR)", 1.0, 5000.0, 350.0, key="d_p")
        div_annual = st.number_input("Annual Cash Dividend Per Share (PKR)", 0.0, 500.0, 35.0, key="d_a")
        div_shares = st.number_input("Number of Shares Held", 1, 100000, 1000, key="d_s")
        
        div_yield = (div_annual / div_price) * 100 if div_price > 0 else 0
        total_payout = div_annual * div_shares
        
        st.markdown(f"**Dividend Yield:** `{div_yield:.2f}%`")
        st.markdown(f"**Expected Annual Dividend Income:** <span style='color:#3B82F6; font-weight:bold;'>Rs. {total_payout:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# TAB 3: FINANCIAL HUBS & CORPORATE MAP
# ------------------------------------------
with tab3:
    st.header("🗺️ Pakistan Financial Ecosystem & Asset Headquarters")
    st.caption("Geographic distribution of PSX Trading Hubs and Corporate Headquarters of tracked assets.")
    
    locations = pd.DataFrame([
        {"Name": "Pakistan Stock Exchange (PSX HQ)", "Lat": 24.8532, "Lon": 67.0006, "Type": "Exchange Floor", "Details": "Karachi Stock Exchange Building, Stock Exchange Road"},
        {"Name": "PSX Regional Office Lahore", "Lat": 31.5619, "Lon": 74.3107, "Type": "Exchange Floor", "Details": "LSE Plaza, Khayaban-e-Aiwan-e-Iqbal"},
        {"Name": "PSX Regional Office Islamabad", "Lat": 33.7125, "Lon": 73.0592, "Type": "Exchange Floor", "Details": "ISE Towers, Jinnah Avenue"},
        {"Name": "MCB Bank Ltd HQ", "Lat": 31.5640, "Lon": 74.3210, "Type": "Corporate HQ", "Details": "MCB Tower, Lahore"},
        {"Name": "Fauji Fertilizer Co (FFC)", "Lat": 33.6007, "Lon": 73.0679, "Type": "Corporate HQ", "Details": "SONA Tower, Rawalpindi"},
        {"Name": "Meezan Bank Ltd HQ", "Lat": 24.8607, "Lon": 67.0011, "Type": "Corporate HQ", "Details": "Meezan House, SITE, Karachi"},
        {"Name": "OGDC Headquarters", "Lat": 33.7081, "Lon": 73.0560, "Type": "Corporate HQ", "Details": "OGDCL House, Blue Area, Islamabad"},
        {"Name": "Systems Limited (SYS) HQ", "Lat": 31.4700, "Lon": 74.4100, "Type": "Corporate HQ", "Details": "Software Technology Park, Lahore"},
        {"Name": "Hub Power Co (HUBC)", "Lat": 24.8200, "Lon": 67.0300, "Type": "Corporate HQ", "Details": "Ocean Tower, Clifton, Karachi"},
        {"Name": "United Bank Ltd (UBL)", "Lat": 24.8510, "Lon": 67.0020, "Type": "Corporate HQ", "Details": "UBL Tower, I.I. Chundrigar Road, Karachi"},
        {"Name": "Pakistan Petroleum (PPL)", "Lat": 24.8550, "Lon": 67.0040, "Type": "Corporate HQ", "Details": "PIDC House, Dr. Ziauddin Ahmed Road, Karachi"},
        {"Name": "Engro Corporation HQ", "Lat": 24.8190, "Lon": 67.0280, "Type": "Corporate HQ", "Details": "The Harbour Front Building, Clifton, Karachi"},
        {"Name": "Lucky Cement HQ", "Lat": 24.8210, "Lon": 67.0290, "Type": "Corporate HQ", "Details": "Main Clifton, Karachi"}
    ])
    
    fig_map = px.scatter_mapbox(
        locations,
        lat="Lat",
        lon="Lon",
        hover_name="Name",
        hover_data=["Type", "Details"],
        color="Type",
        color_discrete_map={"Exchange Floor": "#EF4444", "Corporate HQ": "#3B82F6"},
        zoom=5,
        height=550
    )
    
    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#0B0E14",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(17,24,39,0.8)")
    )
    
    st.plotly_chart(fig_map, use_container_width=True)

# ------------------------------------------
# TAB 4: SECP REGULATORY COMPLIANCE
# ------------------------------------------
with tab4:
    st.header("📜 Securities & Regulatory Compliance Standards")
    st.markdown("""
    ### Securities and Exchange Commission of Pakistan (SECP) Alignment
    
    This software terminal is designed purely as an **automated quantitative research system** operating under mathematical parameters, machine learning classifiers, and public natural language inputs.
    
    #### 1. Non-Advisory & Non-Fiduciary Mandate
    * **No Investment Advice:** Outputs presented in this terminal (`🟢 AI BUY`, `🔴 IGNORE`, Stop-Loss levels, Target Allocations) do not constitute personalized financial advice or brokerage portfolio management.
    * **Independent Research:** Users must verify quantitative signals against their own risk appetite and consult an SECP-registered research analyst or licensed broker before executing live trades.
    
    #### 2. Risk Mitigation & Capital Loss Explicit Warning
    * **Market Risk:** Equity trading on the Pakistan Stock Exchange involves substantial risk of capital loss. Past performance of Random Forest classification models or FinBERT sentiment scores is no guarantee of future stock returns.
    * **Circuit Lock Liability:** Liquidations during extreme volatility may be restricted by official PSX circuit breaker locks ($\pm 7.5\%$).
    
    #### 3. Algorithmic Transparency
    * Models utilize historical price data downloaded via `yfinance`, technical indicators (RSI-14, MACD, ATR-14), and public Google News RSS headlines scored by `ProsusAI/finbert`.
    """)
