import ccxt
import requests
import time
from datetime import datetime
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

print("=" * 80)
print("🚀 ELITE MARKET SCANNER (OPTIMIZED - PARALLEL FETCHING)")
print("   🔍 Scanning TOP 40 liquid coins...")
print("   ⚡ Parallel processing: 10x faster!")
print("=" * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

MIN_VOLUME_USD = 1000000   # Minimum 24h volume
TOP_N = 40                 # Top 40 coins (fast + accurate)
SCAN_INTERVAL = 300        # 5 minutes
CONFIDENCE_THRESHOLD = 80  # Show only 80%+ confidence
MAX_WORKERS = 10           # 10 threads parallel mein fetch karenge

# ============================================================================
# 1. GET TOP COINS BY VOLUME (Fast)
# ============================================================================

def get_top_coins_by_volume():
    print("\n📡 Fetching top USDT pairs from Binance...")
    try:
        exchange = ccxt.binance()
        markets = exchange.load_markets()
        
        # Sirf USDT pairs
        usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]
        print(f"   Found {len(usdt_pairs)} USDT pairs. Fetching volumes...")
        
        # Fetch all tickers in one go (fast)
        tickers = exchange.fetch_tickers()
        
        coins = []
        for symbol in usdt_pairs:
            ticker = tickers.get(symbol)
            if ticker and ticker.get('quoteVolume'):
                volume = ticker['quoteVolume']
                if volume > MIN_VOLUME_USD:
                    base = symbol.split('/')[0]
                    coins.append({
                        'symbol': base,
                        'volume': volume,
                        'price': ticker['last'],
                        'low': ticker['low'],
                        'high': ticker['high']
                    })
        
        # Sort by volume
        coins.sort(key=lambda x: x['volume'], reverse=True)
        top_coins = coins[:TOP_N]
        
        print(f"   ✅ Top {len(top_coins)} coins selected (by 24h volume)")
        return top_coins
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

# ============================================================================
# 2. FETCH SINGLE COIN DATA (Thread-safe)
# ============================================================================

def fetch_coin_data(symbol):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(f'{symbol}/USDT', '5m', limit=60)
        if not ohlcv or len(ohlcv) < 50:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except:
        return None

# ============================================================================
# 3. TECHNICAL ANALYSIS
# ============================================================================

def analyze_coin(df, current_price):
    if df is None or len(df) < 50:
        return None
    
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    volume = df['Volume'].squeeze()
    
    # Indicators
    rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
    
    macd_indicator = MACD(close=close)
    macd_line = float(macd_indicator.macd().iloc[-1])
    macd_signal = float(macd_indicator.macd_signal().iloc[-1])
    macd_hist = macd_line - macd_signal
    
    bb = BollingerBands(close=close, window=20, window_dev=2)
    bb_high = float(bb.bollinger_hband().iloc[-1])
    bb_low = float(bb.bollinger_lband().iloc[-1])
    
    sma_50 = float(SMAIndicator(close=close, window=50).sma_indicator().iloc[-1])
    atr = float(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])
    
    price_change = ((current_price - close.iloc[-2]) / close.iloc[-2]) * 100 if len(close) > 1 else 0
    
    # SCORE (-5 to +5)
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
    
    # Probability
    raw_prob = 50 + (score / 5) * 50
    probability = max(5, min(95, raw_prob))
    
    if score > 0.5:
        direction = "🟢 BUY"
    elif score < -0.5:
        direction = "🔴 SELL"
    else:
        direction = "⏸️ HOLD"
    
    return {
        "rsi": rsi,
        "macd_hist": macd_hist,
        "price": current_price,
        "score": score,
        "probability": probability,
        "direction": direction,
        "sma_50": sma_50,
        "bb_low": bb_low,
        "bb_high": bb_high,
        "atr": atr,
        "price_change": price_change,
        "rsi_signal": "🔥 Oversold" if rsi < 30 else "⚠️ Overbought" if rsi > 70 else "Neutral",
        "macd_signal": "Bullish" if macd_hist > 0 else "Bearish",
        "bb_signal": "Below Lower" if current_price < bb_low else "Above Upper" if current_price > bb_high else "Inside Bands",
        "sma_signal": "Above SMA50" if current_price > sma_50 else "Below SMA50"
    }

# ============================================================================
# 4. PARALLEL SCANNER (FAST!)
# ============================================================================

def scan_coin_parallel(coin):
    symbol = coin['symbol']
    price = coin['price']
    df = fetch_coin_data(symbol)
    if df is None:
        return None
    analysis = analyze_coin(df, price)
    if analysis and analysis['probability'] >= CONFIDENCE_THRESHOLD:
        return {
            'symbol': symbol,
            'price': price,
            'rsi': analysis['rsi'],
            'score': analysis['score'],
            'probability': analysis['probability'],
            'direction': analysis['direction'],
            'price_change': analysis['price_change'],
            'rsi_signal': analysis['rsi_signal'],
            'macd_signal': analysis['macd_signal'],
            'bb_signal': analysis['bb_signal'],
            'sma_signal': analysis['sma_signal'],
            'atr': analysis['atr']
        }
    return None

def scan_market():
    top_coins = get_top_coins_by_volume()
    if not top_coins:
        return []
    
    print(f"\n📊 Scanning {len(top_coins)} coins in parallel ({MAX_WORKERS} threads)...\n")
    
    results = []
    completed = 0
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = {executor.submit(scan_coin_parallel, coin): coin for coin in top_coins}
        
        # Process results as they complete
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                results.append(result)
            
            # Progress
            if completed % 5 == 0 or completed == len(top_coins):
                print(f"   ⏳ Scanned {completed}/{len(top_coins)} coins... ({len(results)} high-confidence signals found)")
    
    # Sort by probability
    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

# ============================================================================
# 5. DISPLAY
# ============================================================================

def display_results(results, scan_time):
    print("\n" + "=" * 80)
    print(f"🔥 ELITE SIGNALS ({scan_time.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"   Total coins scanned: {TOP_N} | High-confidence signals: {len(results)}")
    print("=" * 80)
    
    if not results:
        print("\n   😴 No high-confidence signals found right now.")
        return
    
    print(f"\n{'Symbol':<8} {'Price':<14} {'Direction':<12} {'Probability':<14} {'RSI':<8} {'Score':<8}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['symbol']:<8} ${r['price']:<13,.4f} {r['direction']:<12} {r['probability']:<13}% {r['rsi']:<8.1f} {r['score']:<8.2f}")
    
    print("\n📊 TOP 3 DETAILS")
    print("-" * 40)
    for idx, r in enumerate(results[:3]):
        print(f"\n🔹 #{idx+1} {r['symbol']} | {r['direction']} | {r['probability']}%")
        print(f"   Price: ${r['price']:.4f} | RSI: {r['rsi']:.1f} | Score: {r['score']:.2f}")
        print(f"   📈 Change: {r['price_change']:.2f}% | ATR: {r['atr']:.4f}")

# ============================================================================
# 6. MAIN LOOP
# ============================================================================

scan_count = 0

while True:
    scan_count += 1
    print("\n" + "=" * 80)
    print(f"🚀 ELITE SCAN #{scan_count} (Parallel Mode)")
    print("=" * 80)
    
    start = time.time()
    results = scan_market()
    duration = time.time() - start
    
    display_results(results, datetime.now())
    
    print(f"\n⏱️ Scan completed in {duration:.1f} seconds")
    print(f"⏳ Next scan in {SCAN_INTERVAL//60} minutes...")
    
    try:
        time.sleep(SCAN_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Scanner stopped.")
        break