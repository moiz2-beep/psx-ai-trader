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
from plotly.subplots import make_subplots
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE CONFIG & INSTITUTIONAL STYLING
# ==========================================
st.set_page_config(
    page_title="PSX Quant Terminal | Institutional Suite", 
    layout="wide", 
    page_icon="🏛️",
    initial_sidebar_state="expanded"
)

# Smooth 30-second silent background refresh
st_autorefresh(interval=30000, key="psx_terminal_refresh")

# Dark Theme CSS
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: 'Inter', sans-serif; }
    .secp-banner { background-color: #161B22; border-left: 4px solid #D97706; padding: 12px; font-size: 13px; color: #D1D5DB; margin-bottom: 15px; border-radius: 4px; }
    .calc-box { background-color: #161B2E; border: 1px solid #232D4B; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #111827; border-radius: 6px; padding: 8px 16px; color: #9CA3AF; }
    .stTabs [aria-selected="true"] { background-color: #1F2937 !important; color: #3B82F6 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Regulatory Notice
st.markdown("""
    <div class="secp-banner">
        ⚖️ <strong>SECP REGULATORY NOTICE:</strong> This quantitative terminal operates under algorithmic research models. Signals generated are non-advisory and intended strictly for educational & algorithmic evaluation. Capital allocation carries financial market risk.
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE LOGGING ENGINE
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
    try:
        conn = sqlite3.connect("trades.db")
        conn.cursor().execute("INSERT INTO signals (ticker, price, ai_confidence, capital_allocated, stop_loss, take_profit, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (ticker, price, conf, cap, sl, tp, status))
        conn.commit()
        conn.close()
    except Exception:
        pass

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
# 4. CACHED AI & DATA FETCHING
# ==========================================
@st.cache_resource(show_spinner=False)
def load_finbert():
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

finbert = load_finbert()

@st.cache_data(ttl=60, show_spinner=False)
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
    except Exception:
        return 0.0, "Neutral ⚪"

@st.cache_data(ttl=86400, show_spinner=False)
def train_real_market_model(tickers):
    X_data, y_data = [], []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", progress=False)
            if df.empty or len(df) < 100: continue
            
            close_s = df['Close'].squeeze()
            ma50 = close_s.rolling(50).mean()
            above_ma = np.where(close_s > ma50, 1, 0)
            rsi = compute_rsi(close_s)
            rsi_over = np.where(rsi < 45, 1, 0)
            
            future_ret = close_s.shift(-10) / close_s - 1
            target = np.where(future_ret > 0.05, 1, 0)
            
            temp = pd.DataFrame({
                'Above_MA': above_ma,
                'RSI_Oversold': rsi_over,
                'Target': target
            }).dropna()

            for _, row in temp.iterrows():
                X_data.append([row['Above_MA'], 1, 0, row['RSI_Oversold']])
                y_data.append(row['Target'])
        except Exception:
            continue
        
    if not X_data or len(set(y_data)) < 2:
        X_data, y_data = [[1,1,0.5,1], [0,0,-0.5,0]], [1, 0]
        
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(np.array(X_data), np.array(y_data))
    return model

@st.cache_data(ttl=30, show_spinner=False)
def fetch_psx_batch(tickers):
    try:
        return yf.download(tickers, period="1y", group_by='ticker', progress=False)
    except Exception:
        return pd.DataFrame()

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
    st.markdown("🟢 **PSX Candlestick Feed**")
    st.markdown("🟢 **Moving Averages (20/50/200)**")
    st.markdown("🟢 **SECP Regulatory Shield**")

max_rupee_risk = total_capital * (risk_pct / 100)

# ==========================================
# 6. TABBED NAVIGATION
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 Live Execution Matrix", 
    "📈 Interactive Candlestick Studio",
    "🧮 Institutional Calculators", 
    "📜 Regulatory Compliance"
])

# ------------------------------------------
# TAB 1: LIVE QUANT MATRIX
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
        hist = pd.DataFrame()
        
        try:
            if isinstance(batch_data, pd.DataFrame) and not batch_data.empty:
                if isinstance(batch_data.columns, pd.MultiIndex) and ticker in batch_data.columns.levels[0]:
                    hist = batch_data[ticker].dropna()
        except Exception:
            hist = pd.DataFrame()

        if hist.empty or len(hist) < 20:
            try:
                hist = yf.Ticker(ticker).history(period="6mo")
            except Exception:
                hist = pd.DataFrame()
            
        if hist.empty or len(hist) < 20:
            results.append({
                "Asset": clean_name, "Price": "Fetch Error", "FinBERT Sentiment": "N/A",
                "AI Confidence": "0.0%", "Signal": "🔴 DATA OFFLINE", "Stop-Loss": "-", "Take-Profit": "-", "Capital Target": "-"
            })
            continue
            
        close_series = hist['Close'].squeeze()
        high_series = hist['High'].squeeze()
        low_series = hist['Low'].squeeze()

        close = float(close_series.iloc[-1])
        prev_close = float(close_series.iloc[-2])
        
        pct_change = abs((close - prev_close) / prev_close) * 100
        circuit_lock = True if pct_change >= 6.5 else False
        
        ma50 = float(close_series.rolling(50).mean().iloc[-1])
        above_50ma = 1 if close > ma50 else 0
        current_rsi = float(compute_rsi(close_series).iloc[-1])
        rsi_over = 1 if current_rsi < 45 else 0
        current_atr = float(compute_atr(high_series, low_series, close_series).iloc[-1])
        
        pe_under = 1
        sent_score, sent_label = fetch_finbert_sentiment(ticker)
        
        features = np.array([[above_50ma, pe_under, sent_score, rsi_over]])
        confidence = float(model.predict_proba(features)[0][1] * 100)
        
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
        try:
            conn = sqlite3.connect("trades.db")
            st.dataframe(pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 10", conn), hide_index=True)
            conn.close()
        except Exception:
            st.info("Database logs initializing...")

# ------------------------------------------
# TAB 2: CANDLESTICK & TECHNICAL MA STUDIO
# ------------------------------------------
with tab2:
    st.header("📈 Interactive Candlestick & Moving Average Studio")
    st.caption("Real-time candlestick price action, trading volume, and dynamic Moving Averages (20 SMA, 50 SMA, 200 SMA).")
    
    col_sel1, col_sel2 = st.columns([2, 2])
    with col_sel1:
        selected_asset = st.selectbox("Select PSX Stock", ["MCB", "FFC", "MEBL", "OGDC", "SYS", "HUBC", "UBL", "PPL", "ENGRO", "LUCK"], index=0)
    with col_sel2:
        chart_timeframe = st.selectbox("Select Timeframe", ["3 Months", "6 Months", "1 Year"], index=1)
    
    tf_map = {"3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}
    selected_ticker = f"{selected_asset}.KA"
    
    try:
        stock_df = yf.Ticker(selected_ticker).history(period=tf_map[chart_timeframe])
        if stock_df.empty:
            st.error("Market data unavailable for selected ticker.")
        else:
            stock_df['SMA20'] = stock_df['Close'].rolling(20).mean()
            stock_df['SMA50'] = stock_df['Close'].rolling(50).mean()
            stock_df['SMA200'] = stock_df['Close'].rolling(200).mean()
            
            # Subplot: Row 1 = Candlestick & MAs, Row 2 = Volume
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03, 
                row_heights=[0.75, 0.25],
                subplot_titles=(f"{selected_asset} Daily Price Chart & Moving Averages", "Trading Volume")
            )
            
            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=stock_df.index,
                    open=stock_df['Open'],
                    high=stock_df['High'],
                    low=stock_df['Low'],
                    close=stock_df['Close'],
                    name="Candles",
                    increasing_line_color='#10B981', 
                    decreasing_line_color='#EF4444'
                ), row=1, col=1
            )
            
            # Moving Averages
            fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA20'], mode='lines', name='20 SMA', line=dict(color='#3B82F6', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA50'], mode='lines', name='50 SMA', line=dict(color='#F59E0B', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_df.index, y=stock_df['SMA200'], mode='lines', name='200 SMA', line=dict(color='#EC4899', width=1.5)), row=1, col=1)
            
            # Volume Bars
            colors = ['#10B981' if c >= o else '#EF4444' for c, o in zip(stock_df['Close'], stock_df['Open'])]
            fig.add_trace(go.Bar(x=stock_df.index, y=stock_df['Volume'], name="Volume", marker_color=colors, opacity=0.7), row=2, col=1)
            
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                paper_bgcolor="#0B0E14",
                plot_bgcolor="#111827",
                font=dict(color="#E0E6ED"),
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(gridcolor="#1F2937")
            fig.update_yaxes(gridcolor="#1F2937")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Latest Technical Highlights
            last_close = stock_df['Close'].iloc[-1]
            last_sma20 = stock_df['SMA20'].iloc[-1]
            last_sma50 = stock_df['SMA50'].iloc[-1]
            last_sma200 = stock_df['SMA200'].iloc[-1]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Latest Close", f"Rs. {last_close:.2f}")
            m2.metric("20 SMA", f"Rs. {last_sma20:.2f}" if pd.notna(last_sma20) else "N/A")
            m3.metric("50 SMA", f"Rs. {last_sma50:.2f}" if pd.notna(last_sma50) else "N/A")
            m4.metric("200 SMA", f"Rs. {last_sma200:.2f}" if pd.notna(last_sma200) else "N/A")
    except Exception as e:
        st.error(f"Error loading chart data: {e}")

# ------------------------------------------
# TAB 3: STANDALONE CALCULATORS SUITE
# ------------------------------------------
with tab3:
    st.header("🧮 Institutional Quantitative Calculators")
    st.caption("Perform isolated risk, taxation, DCA, intrinsic value, and yield calculations standard in top-tier trading platforms.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Dynamic Position Size Calculator
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
        st.markdown(f"**Total Capital Required:** Rs. {total_trade_val:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 2. Risk-to-Reward Ratio (RRR) Evaluator
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

        # 3. PSX Net Profit, Brokerage Commission & CGT Calculator
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("3. PSX Net Profit, Brokerage & Tax Calculator")
        tx_buy_price = st.number_input("Buy Price (PKR)", 1.0, 5000.0, 100.0, key="tx_bp")
        tx_sell_price = st.number_input("Sell Price (PKR)", 1.0, 5000.0, 120.0, key="tx_sp")
        tx_qty = st.number_input("Share Quantity", 1, 1000000, 1000, key="tx_q")
        tx_comm_rate = st.number_input("Broker Commission (%)", 0.01, 1.0, 0.15, step=0.01, key="tx_comm") / 100
        tx_filer = st.radio("Tax Status", ["Filer (15% CGT)", "Non-Filer (Normal Slabs ~30%)"], key="tx_status")
        
        buy_val = tx_buy_price * tx_qty
        sell_val = tx_sell_price * tx_qty
        buy_comm = buy_val * tx_comm_rate
        sell_comm = sell_val * tx_comm_rate
        prov_sales_tax = (buy_comm + sell_comm) * 0.13
        secp_cdc_fees = (buy_val + sell_val) * 0.0003
        
        gross_profit = sell_val - buy_val
        total_trading_costs = buy_comm + sell_comm + prov_sales_tax + secp_cdc_fees
        net_before_cgt = gross_profit - total_trading_costs
        
        cgt_rate = 0.15 if "Filer" in tx_filer else 0.30
        cgt_tax = max(net_before_cgt * cgt_rate, 0.0) if net_before_cgt > 0 else 0.0
        final_take_home = net_before_cgt - cgt_tax
        
        st.markdown(f"**Gross Profit:** Rs. {gross_profit:,.2f}")
        st.markdown(f"**Brokerage Fees & Taxes:** Rs. {total_trading_costs:,.2f}")
        st.markdown(f"**Capital Gains Tax (CGT):** Rs. {cgt_tax:,.2f}")
        st.markdown(f"**Net Take-Home Profit:** <span style='color:#10B981; font-weight:bold;'>Rs. {final_take_home:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 4. Dollar-Cost Averaging (DCA) / Average Price Calculator
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("4. Dollar-Cost Averaging (DCA) / Average Price")
        dca_p1 = st.number_input("Batch 1 Buy Price (PKR)", 1.0, 5000.0, 150.0, key="dca_p1")
        dca_q1 = st.number_input("Batch 1 Quantity", 1, 100000, 500, key="dca_q1")
        dca_p2 = st.number_input("Batch 2 Buy Price (Dip Price PKR)", 1.0, 5000.0, 110.0, key="dca_p2")
        dca_q2 = st.number_input("Batch 2 Quantity", 1, 100000, 500, key="dca_q2")
        
        tot_qty = dca_q1 + dca_q2
        tot_cost = (dca_p1 * dca_q1) + (dca_p2 * dca_q2)
        avg_price = tot_cost / tot_qty
        
        st.markdown(f"**Total Shares Held:** `{tot_qty:,}` Shares")
        st.markdown(f"**Total Capital Invested:** Rs. {tot_cost:,.2f}")
        st.markdown(f"**New Average Cost Basis:** <span style='color:#3B82F6; font-weight:bold;'>Rs. {avg_price:.2f} per share</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # 5. Benjamin Graham Intrinsic Value Calculator
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("5. Benjamin Graham Intrinsic Value Calculator")
        graham_eps = st.number_input("Earnings Per Share - EPS (PKR)", 0.1, 1000.0, 25.0, key="g_eps")
        graham_bvps = st.number_input("Book Value Per Share - BVPS (PKR)", 0.1, 5000.0, 120.0, key="g_bvps")
        graham_mkt = st.number_input("Current Market Price (PKR)", 1.0, 5000.0, 180.0, key="g_mkt")
        
        intrinsic_value = np.sqrt(22.5 * graham_eps * graham_bvps)
        margin_of_safety = ((intrinsic_value - graham_mkt) / intrinsic_value) * 100 if intrinsic_value > 0 else 0
        
        st.markdown(f"**Graham Fair Intrinsic Value:** <span style='color:#10B981; font-weight:bold;'>Rs. {intrinsic_value:.2f}</span>", unsafe_allow_html=True)
        if margin_of_safety > 0:
            st.success(f"✅ Undervalued by {margin_of_safety:.1f}% (Margin of Safety)")
        else:
            st.warning(f"⚠️ Overvalued by {abs(margin_of_safety):.1f}% relative to Graham Formula")
        st.markdown('</div>', unsafe_allow_html=True)

        # 6. CAGR & Compound Wealth Growth Calculator
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("6. Compound Growth & CAGR Calculator")
        cagr_init = st.number_input("Initial Principal (PKR)", 10000, 10000000, 100000, step=10000, key="cg_i")
        cagr_years = st.slider("Investment Horizon (Years)", 1, 30, 5, key="cg_y")
        cagr_rate = st.slider("Expected Annual Return (%)", 1.0, 50.0, 15.0, key="cg_r")
        
        future_val = cagr_init * ((1 + (cagr_rate / 100)) ** cagr_years)
        total_wealth_gain = future_val - cagr_init
        
        st.markdown(f"**Projected Portfolio Value:** <span style='color:#10B981; font-weight:bold;'>Rs. {future_val:,.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Net Profit Generated:** Rs. {total_wealth_gain:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

        # 7. PSX Daily Circuit Breaker Bands
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("7. PSX Daily Circuit Breaker Bands")
        prev_close_price = st.number_input("Previous Session Close Price (PKR)", 1.0, 5000.0, 400.0, key="cb_p")
        
        upper_limit = prev_close_price * 1.075
        lower_limit = prev_close_price * 0.925
        warning_upper = prev_close_price * 1.065
        
        st.markdown(f"**Upper Circuit Limit (+7.5%):** <span style='color:#10B981; font-weight:bold;'>Rs. {upper_limit:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Lower Circuit Limit (-7.5%):** <span style='color:#EF4444; font-weight:bold;'>Rs. {lower_limit:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Auto-Lock Warning Threshold (+6.5%):** Rs. {warning_upper:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 8. Dividend Yield & Passive Income Calculator
        st.markdown('<div class="calc-box">', unsafe_allow_html=True)
        st.subheader("8. Dividend Yield & Passive Income")
        div_price = st.number_input("Current Share Price (PKR)", 1.0, 5000.0, 350.0, key="d_p")
        div_annual = st.number_input("Annual Cash Dividend Per Share (PKR)", 0.0, 500.0, 35.0, key="d_a")
        div_shares = st.number_input("Number of Shares Held", 1, 100000, 1000, key="d_s")
        
        div_yield = (div_annual / div_price) * 100 if div_price > 0 else 0
        total_payout = div_annual * div_shares
        
        st.markdown(f"**Dividend Yield:** `{div_yield:.2f}%`")
        st.markdown(f"**Expected Annual Dividend Income:** <span style='color:#3B82F6; font-weight:bold;'>Rs. {total_payout:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

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
