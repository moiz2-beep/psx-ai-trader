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
from streamlit_autorefresh import st_autorefresh
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG & AUTO-REFRESH
# ==========================================
st.set_page_config(page_title="PSX Quant Terminal Pro", layout="wide", page_icon="🏦")
st_autorefresh(interval=10000, key="realtime_psx_feed")

# Custom UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .disclaimer { font-size: 12px; color: #888888; text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ FOR EDUCATIONAL & QUANTITATIVE RESEARCH ONLY. NOT FINANCIAL ADVICE. NOT SECP REGISTERED.</div>', unsafe_allow_html=True)

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
# 3. ADVANCED TECHNICALS (RSI, MACD, ATR)
# ==========================================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def compute_macd(series):
    ema12, ema26 = series.ewm(span=12).mean(), series.ewm(span=26).mean()
    macd = ema12 - ema26
    return macd, macd.ewm(span=9).mean()

def compute_atr(high, low, close, period=14):
    tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(period).mean()

# ==========================================
# 4. FINBERT AI SENTIMENT ENGINE (Cached)
# ==========================================
@st.cache_resource(show_spinner=False)
def load_finbert():
    # FinBERT is specifically trained on financial language
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

finbert = load_finbert()

def fetch_finbert_sentiment(ticker):
    clean_ticker = ticker.replace(".KA", "")
    url = f"https://news.google.com/rss/search?q={clean_ticker}+PSX+stock+finance&hl=en-PK&gl=PK&ceid=PK:en"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req, timeout=3).read()
        headlines = [item.find('title').text for item in ET.fromstring(xml_data).findall('.//item')[:3]]
        
        if not headlines: return 0.0, "Neutral"
        
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

# ==========================================
# 5. HISTORICAL ML MODEL TRAINING (Cached)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False) # Trains only once every 24 hours
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
            
            # Target: Did the price go up 5% in the next 10 days?
            df['Future_Return'] = df['Close'].shift(-10) / df['Close'] - 1
            df['Target'] = np.where(df['Future_Return'] > 0.05, 1, 0)
            
            df.dropna(inplace=True)
            for _, row in df.iterrows():
                X_data.append([row['Above_MA'], 1, 0, row['RSI_Oversold']]) # Simplified PE/News for history
                y_data.append(row['Target'])
        except: continue
        
    if not X_data: # Emergency fallback if download fails
        X_data, y_data = [[1,1,0.5,1], [0,0,-0.5,0]], [1, 0]
        
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(np.array(X_data), np.array(y_data))
    return model

# ==========================================
# 6. UI: CONTROL PANEL
# ==========================================
st.title("⚡ PSX Institutional Quant Terminal")
st.caption("Real-Time ML Engine | FinBERT NLP | Dynamic ATR Risk Management")

with st.sidebar:
    st.header("💼 Risk Engine Config")
    total_capital = st.number_input("Account Balance (PKR)", 50000, 10000000, 500000, step=50000)
    risk_pct = st.slider("Max Account Risk per Trade (%)", 1.0, 5.0, 2.0, 0.5)
    min_conf = st.slider("Min AI Confidence Threshold (%)", 50, 95, 75)
    st.markdown("---")
    st.markdown("### Risk Guardrails Active:")
    st.markdown("✅ **FinBERT AI News**")
    st.markdown("✅ **ATR Position Sizing**")
    st.markdown("✅ **Circuit Breaker Lock**")

max_rupee_risk = total_capital * (risk_pct / 100)
c1, c2, c3 = st.columns(3)
c1.metric("Total Portfolio Equity", f"Rs. {total_capital:,.0f}")
c2.metric("Max Rupee Risk Per Trade", f"Rs. {max_rupee_risk:,.0f}")
c3.metric("AI Execution Threshold", f"{min_conf}%")
st.write("---")

# ==========================================
# 7. MARKET ANALYSIS & EXECUTION ENGINE
# ==========================================
# Top 10 PSX Heavyweights
tickers = ["MCB.KA", "FFC.KA", "MEBL.KA", "OGDC.KA", "SYS.KA", "HUBC.KA", "UBL.KA", "PPL.KA", "ENGRO.KA", "LUCK.KA"]
model = train_real_market_model(tickers)

results = []

with st.spinner("Compiling FinBERT Sentiment & Real-Time Market Data..."):
    for ticker in tickers:
        clean_name = ticker.replace(".KA", "")
        stock = yf.Ticker(ticker)
        
        try: hist = stock.history(period="6mo")
        except: hist = pd.DataFrame()
            
        if hist.empty or len(hist) < 50: continue
            
        close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        
        # Circuit Breaker Check (PSX 7.5% limit. Lock at 6.5%)
        pct_change = abs((close - prev_close) / prev_close) * 100
        circuit_lock = True if pct_change >= 6.5 else False
        
        # Technicals & ATR
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        above_50ma = 1 if close > ma50 else 0
        current_rsi = compute_rsi(hist['Close']).iloc[-1]
        rsi_over = 1 if current_rsi < 45 else 0
        current_atr = compute_atr(hist['High'], hist['Low'], hist['Close']).iloc[-1]
        
        # Valuation & FinBERT
        pe_ratio = stock.info.get('trailingPE', 12.0)
        pe_ratio = pe_ratio if pe_ratio is not None else 12.0
        pe_under = 1 if pe_ratio < 10.0 else 0
        sent_score, sent_label = fetch_finbert_sentiment(ticker)
        
        # AI ML Prediction
        features = np.array([[above_50ma, pe_under, sent_score, rsi_over]])
        confidence = model.predict_proba(features)[0][1] * 100
        
        # Dynamic Risk Engine (ATR Sizing & Targets)
        stop_loss = close - (1.5 * current_atr)
        take_profit = close + (3.0 * current_atr)  # 1:2 Risk/Reward
        risk_per_share = close - stop_loss
        
        if circuit_lock:
            signal, allocated, final_sl, final_tp = "🟡 CIRCUIT LOCK", 0.0, 0.0, 0.0
        elif confidence >= min_conf:
            signal = "🟢 AI BUY"
            shares_to_buy = max_rupee_risk / risk_per_share if risk_per_share > 0 else 0
            allocated = min(shares_to_buy * close, total_capital) # Never exceed total capital
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

# Render Dashboard Grid
st.subheader("📡 Live Quantitative Execution Matrix")
st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# Database Audit
with st.expander("📂 View Backend Execution Database (trades.db)"):
    conn = sqlite3.connect("trades.db")
    st.dataframe(pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 10", conn), hide_index=True)
    conn.close()
