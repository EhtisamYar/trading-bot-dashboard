import streamlit as st
import pandas as pd
import ccxt
import time
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="🚀 Elite Trading Dashboard", layout="wide")
st.title("🤖 Ultimate Trading Bot Dashboard")
st.markdown("### Live Market Scanner & Deep Dive Analysis (Crypto)")

# ------------------ SIDEBAR ------------------
st.sidebar.header("⚙️ Navigation")
mode = st.sidebar.radio(
    "Select Mode",
    ["🔍 Ultimate Bot (Deep Dive)", "⚡ Elite Scanner (Market Scan)"]
)

# ------------------ HELPER FUNCTIONS ------------------
@st.cache_data(ttl=300)
def get_top_coins(limit=40):
    """Fetch top 40 coins by 24h volume from Binance"""
    try:
        exchange = ccxt.binance()
        tickers = exchange.fetch_tickers()
        coins = []
        for symbol, ticker in tickers.items():
            if symbol.endswith('/USDT') and ticker.get('quoteVolume'):
                volume = ticker['quoteVolume']
                if volume > 1000000:
                    coins.append({
                        'symbol': symbol.split('/')[0],
                        'price': ticker['last'],
                        'volume': volume,
                        'change': ticker['percentage'] if ticker.get('percentage') else 0
                    })
        coins.sort(key=lambda x: x['volume'], reverse=True)
        return coins[:limit]
    except Exception as e:
        st.error(f"Error fetching top coins: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_ohlcv(symbol):
    """Fetch 5-min OHLCV data from Binance"""
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(f'{symbol}/USDT', '5m', limit=60)
        if not ohlcv or len(ohlcv) < 30:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        # st.warning(f"Could not fetch data for {symbol}: {e}")
        return None

def analyze_coin(df, current_price):
    """Calculate RSI, MACD, BB, SMA50, ATR and generate score"""
    if df is None or len(df) < 30:
        return None
    
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    
    # Indicators
    rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
    macd_indicator = MACD(close=close)
    macd_hist = float(macd_indicator.macd_diff().iloc[-1])
    bb = BollingerBands(close=close, window=20, window_dev=2)
    bb_high = float(bb.bollinger_hband().iloc[-1])
    bb_low = float(bb.bollinger_lband().iloc[-1])
    sma_50 = float(SMAIndicator(close=close, window=50).sma_indicator().iloc[-1])
    atr = float(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])
    
    price_change = ((current_price - close.iloc[-2]) / close.iloc[-2]) * 100 if len(close) > 1 else 0
    
    # Scoring Logic (-5 to +5)
    score = 0
    if rsi < 30: score += 2
    if rsi > 70: score -= 2
    if macd_hist > 0: score += 1.5
    if macd_hist < 0: score -= 1.5
    if current_price < bb_low: score += 1.5
    if current_price > bb_high: score -= 1.5
    if current_price > sma_50: score += 1.5
    if current_price < sma_50: score -= 1.5
    if price_change > 2: score += 1
    if price_change < -2: score -= 1
    
    # Probability (0 to 100)
    prob = 50 + (score / 5) * 50
    prob = max(5, min(95, prob))
    
    direction = "BUY" if score > 0.5 else "SELL" if score < -0.5 else "HOLD"
    
    return {
        "rsi": rsi,
        "macd_hist": macd_hist,
        "score": score,
        "probability": prob,
        "direction": direction,
        "sma_50": sma_50,
        "bb_low": bb_low,
        "bb_high": bb_high,
        "atr": atr,
        "price_change": price_change,
        "current_price": current_price
    }

# ------------------ MODE 1: ULTIMATE BOT ------------------
if mode == "🔍 Ultimate Bot (Deep Dive)":
    st.header("🌍 Ultimate Bot – Single Coin Deep Dive (Crypto Only)")
    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("Enter Coin Symbol (e.g., BTC, ETH, SOL)", value="BTC").strip().upper()
    with col2:
        analyze_btn = st.button("🔍 Analyze", use_container_width=True)
    
    if analyze_btn and symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            try:
                exchange = ccxt.binance()
                ticker = exchange.fetch_ticker(f'{symbol}/USDT')
                price = ticker['last']
            except:
                st.error(f"Could not fetch price for {symbol}. Make sure it's a valid crypto pair.")
                st.stop()
            
            df = fetch_ohlcv(symbol)
            if df is None:
                st.error(f"Not enough historical data for {symbol}.")
                st.stop()
            
            analysis = analyze_coin(df, price)
            if analysis is None:
                st.error("Analysis failed.")
                st.stop()
            
            # Display Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price", f"${price:.4f}", f"{analysis['price_change']:.2f}%")
            col2.metric("RSI", f"{analysis['rsi']:.1f}", "Oversold" if analysis['rsi']<30 else "Overbought" if analysis['rsi']>70 else "Neutral")
            col3.metric("Signal", analysis['direction'], f"Confidence {analysis['probability']:.1f}%")
            col4.metric("Score", f"{analysis['score']:.2f}")
            
            with st.expander("📊 Detailed Analysis", expanded=True):
                st.write(f"**MACD Histogram:** {analysis['macd_hist']:.3f}")
                st.write(f"**SMA 50:** ${analysis['sma_50']:.4f}")
                st.write(f"**Bollinger Upper:** ${analysis['bb_high']:.4f} | **Lower:** ${analysis['bb_low']:.4f}")
                st.write(f"**ATR (14):** ${analysis['atr']:.4f}")
                if analysis['atr'] > 0:
                    st.write(f"**Stop-Loss:** ${analysis['current_price'] - (analysis['atr']*1.5):.4f}")
                    st.write(f"**Take-Profit:** ${analysis['current_price'] + (analysis['atr']*3):.4f}")
            
            # Chart
            st.subheader("📈 Price Chart (5-minute candles)")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='Price'
            ))
            fig.add_hline(y=analysis['sma_50'], line_dash="dash", line_color="orange", annotation_text="SMA 50")
            fig.update_layout(height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# ------------------ MODE 2: ELITE SCANNER ------------------
else:
    st.header("⚡ Elite Scanner – Top 40 Coins (80%+ Confidence)")
    
    if st.button("🔄 Run Scan Now", use_container_width=True):
        with st.spinner("Scanning market..."):
            top_coins = get_top_coins(limit=40)
            if not top_coins:
                st.error("Failed to fetch top coins.")
                st.stop()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []
            
            def scan_one(coin):
                symbol = coin['symbol']
                price = coin['price']
                df = fetch_ohlcv(symbol)
                if df is None:
                    return None
                analysis = analyze_coin(df, price)
                if analysis and analysis['probability'] >= 80:
                    return {
                        'symbol': symbol,
                        'price': price,
                        'rsi': analysis['rsi'],
                        'score': analysis['score'],
                        'prob': analysis['probability'],
                        'direction': analysis['direction'],
                        'change': analysis['price_change']
                    }
                return None
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(scan_one, coin) for coin in top_coins]
                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    if result:
                        results.append(result)
                    progress_bar.progress((i+1)/len(top_coins))
                    status_text.text(f"Scanned {i+1}/{len(top_coins)} coins... ({len(results)} signals found)")
            
            if results:
                df_results = pd.DataFrame(results)
                df_results = df_results.sort_values('prob', ascending=False)
                
                st.success(f"✅ Found {len(results)} high-confidence signals (80%+)")
                st.dataframe(df_results, use_container_width=True)
                
                fig = px.bar(df_results, x='symbol', y='prob', color='direction',
                             title="Signal Confidence by Coin",
                             labels={'prob':'Confidence %', 'symbol':'Coin'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📊 Top 3 Signals")
                for idx, row in df_results.head(3).iterrows():
                    with st.expander(f"🔹 #{idx+1} {row['symbol']} | {row['direction']} | {row['prob']}%"):
                        st.write(f"**Price:** ${row['price']:.4f}")
                        st.write(f"**RSI:** {row['rsi']:.1f}")
                        st.write(f"**Score:** {row['score']:.2f}")
                        st.write(f"**Change:** {row['change']:.2f}%")
            else:
                st.warning("😴 No high-confidence signals found right now.")