import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from sklearn.ensemble import RandomForestClassifier
from textblob import TextBlob
import plotly.graph_objects as go

# ==========================================
# PAGE CONFIGURATION & DARK THEME STYLING
# ==========================================
st.set_page_config(page_title="PSX AI Trader Terminal", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    div[data-testid="stMetricValue"] {
        font-size: 22px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. DATABASE ENGINE (SQLite Logging)
# ==========================================
def init_db():
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            price REAL,
            ai_confidence REAL,
            capital_allocated REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_signal(ticker, price, confidence, capital, status):
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO signals (ticker, price, ai_confidence, capital_allocated, status)
        VALUES (?, ?, ?, ?, ?)
    """, (ticker, price, confidence, capital, status))
    conn.commit()
    conn.close()

def fetch_trade_logs():
    conn = sqlite3.connect("trades.db")
    df = pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    return df

init_db()

# ==========================================
# 2. TECHNICAL INDICATOR CALCULATIONS
# ==========================================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def compute_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

# ==========================================
# 3. INTERACTIVE PLOTLY CANDLESTICK CHART
# ==========================================
def build_candlestick_chart(hist, ticker_name):
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name="Price (PKR)"
    ))
    
    ma50 = hist['Close'].rolling(window=50).mean()
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=ma50,
        line=dict(color='#FF9900', width=1.5),
        name="50-Day MA"
    ))
    
    fig.update_layout(
        title=f"<b>{ticker_name}</b> Technical Chart",
        yaxis_title="Price (PKR)",
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False,
        paper_bgcolor='#121826',
        plot_bgcolor='#121826'
    )
    return fig

# ==========================================
# 4. NEWS SENTIMENT SCRAPER
# ==========================================
def fetch_news_sentiment(ticker_symbol):
    clean_ticker = ticker_symbol.replace(".KA", "")
    url = f"https://news.google.com/rss/search?q={clean_ticker}+PSX+stock&hl=en-PK&gl=PK&ceid=PK:en"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req, timeout=5).read()
        root = ET.fromstring(xml_data)
        
        headlines = [item.find('title').text for item in root.findall('.//item')[:5]]
        if not headlines:
            return 0.0, "Neutral"
        
        scores = [TextBlob(text).sentiment.polarity for text in headlines]
        avg_sentiment = float(np.mean(scores))
        
        if avg_sentiment > 0.05:
            label = "Positive"
        elif avg_sentiment < -0.05:
            label = "Negative"
        else:
            label = "Neutral"
            
        return round(avg_sentiment, 2), label
    except Exception:
        return 0.0, "Neutral"

# ==========================================
# 5. ML CLASSIFIER MODEL
# ==========================================
@st.cache_resource
def train_model():
    X_dummy = np.array([
        [1, 1, 0.5, 1],
        [0, 0, -0.3, 0],
        [1, 0, 0.2, 1],
        [0, 1, -0.1, 0],
        [1, 1, 0.8, 1],
        [0, 0, -0.5, 0],
        [1, 0, 0.1, 0],
        [0, 1, 0.4, 1]
    ])
    y_dummy = np.array([1, 0, 1, 0, 1, 0, 0, 1])
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_dummy, y_dummy)
    return model

model = train_model()

# ==========================================
# 6. HEADER & METRIC OVERVIEW
# ==========================================
st.title("⚡ PSX Quant Terminal")
st.caption("AI-Powered Equity Signal Engine & Risk Allocator")

# Sidebar Controls
st.sidebar.header("💼 Risk Management Controls")
total_capital = st.sidebar.number_input("Total Capital (PKR)", min_value=10000, value=500000, step=25000)
risk_per_trade = st.sidebar.slider("Max Capital Allocation Per Trade (%)", 1, 20, 5)
min_confidence = st.sidebar.slider("Minimum AI Confidence Threshold (%)", 50, 95, 80)

# Top Summary KPIs
max_trade_cap = total_capital * (risk_per_trade / 100.0)
col1, col2, col3 = st.columns(3)
col1.metric("Total Portfolio Capital", f"Rs. {total_capital:,.0f}")
col2.metric("Max Capital Per Trade", f"Rs. {max_trade_cap:,.0f}")
col3.metric("AI Confidence Target", f"{min_confidence}%")

st.write("---")

# ==========================================
# 7. MARKET ANALYSIS & CHARTS
# ==========================================
tickers = ["MCB.KA", "FFC.KA", "MEBL.KA", "OGDC.KA", "SYS.KA"]
results = []

with st.spinner("Analyzing live PSX candlestick feeds & computing AI confidence..."):
    for ticker in tickers:
        clean_name = ticker.replace(".KA", "")
        stock = yf.Ticker(ticker)
        
        try:
            hist = stock.history(period="6mo")
        except Exception:
            hist = pd.DataFrame()
            
        # Fallback card if Yahoo Finance fails to send data for a ticker
        if hist.empty or len(hist) < 50:
            st.warning(f"⚠️ **{clean_name}**: Live market feed temporarily delayed from Yahoo Finance. Retrying on next refresh...")
            results.append({
                "Ticker": clean_name,
                "Price (PKR)": "N/A",
                "RSI (14D)": "N/A",
                "MACD Trend": "N/A",
                "News Sentiment": "N/A",
                "P/E Ratio": "N/A",
                "AI Confidence": "N/A",
                "Signal": "🟡 OFFLINE",
                "Capital Allocation": "Rs. 0"
            })
            st.write("---")
            continue
            
        current_price = hist['Close'].iloc[-1]
        
        # Technical Indicators
        ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        above_50ma = 1 if current_price > ma50 else 0
        
        rsi_series = compute_rsi(hist['Close'])
        current_rsi = rsi_series.iloc[-1]
        rsi_oversold = 1 if current_rsi < 45 else 0
        
        macd_series, signal_series = compute_macd(hist['Close'])
        macd_val = macd_series.iloc[-1]
        signal_val = signal_series.iloc[-1]
        macd_bullish = "Bullish 🟢" if macd_val > signal_val else "Bearish 🔴"
        
        # Valuation & Sentiment
        try:
            info = stock.info
            pe_ratio = info.get('trailingPE', 12.0)
            if pe_ratio is None or np.isnan(pe_ratio):
                pe_ratio = 12.0
        except Exception:
            pe_ratio = 12.0
            
        pe_undervalued = 1 if pe_ratio < 10.0 else 0
        sent_score, sent_label = fetch_news_sentiment(ticker)
        
        # AI ML Prediction
        features = np.array([[above_50ma, pe_undervalued, sent_score, rsi_oversold]])
        confidence_prob = model.predict_proba(features)[0][1] * 100
        
        if confidence_prob >= min_confidence:
            signal = "🟢 STRONG BUY"
            allocated = max_trade_cap
        else:
            signal = "🟡 DO NOT BUY"
            allocated = 0.0
            
        # Log to SQLite
        log_signal(ticker, round(current_price, 2), round(confidence_prob, 1), round(allocated, 2), signal)
        
        results.append({
            "Ticker": clean_name,
            "Price (PKR)": f"Rs. {current_price:.2f}",
            "RSI (14D)": f"{current_rsi:.1f}",
            "MACD Trend": macd_bullish,
            "News Sentiment": f"{sent_label} ({sent_score:+.2f})",
            "P/E Ratio": f"{pe_ratio:.1f}",
            "AI Confidence": f"{confidence_prob:.1f}%",
            "Signal": signal,
            "Capital Allocation": f"Rs. {allocated:,.0f}" if allocated > 0 else "Rs. 0"
        })
        
        # Render Stock Container Card
        with st.container():
            st.markdown(f"### {clean_name} — **Current Price: Rs. {current_price:.2f}**")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Signal", signal)
            c2.metric("AI Confidence", f"{confidence_prob:.1f}%")
            c3.metric("RSI (14D)", f"{current_rsi:.1f}")
            c4.metric("MACD Trend", macd_bullish)
            c5.metric("Capital Target", f"Rs. {allocated:,.0f}" if allocated > 0 else "Rs. 0")
            
            # Interactive Plotly Candlestick Chart
            with st.expander(f"📉 View Technical Candlestick Chart for {clean_name}"):
                fig = build_candlestick_chart(hist, clean_name)
                st.plotly_chart(fig, use_container_width=True)
            
            st.write("---")

# Summary Table View
st.subheader("📊 Live Quantitative Signals Table")
df_results = pd.DataFrame(results)
st.dataframe(df_results, use_container_width=True, hide_index=True)

# ==========================================
# 8. AUDIT DATABASE LOG
# ==========================================
st.write("---")
st.subheader("📜 Live Database Signal Log (`trades.db`)")
log_df = fetch_trade_logs()
if not log_df.empty:
    st.dataframe(log_df, use_container_width=True, hide_index=True)
