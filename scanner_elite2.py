import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

MIN_VOLUME_USD = 1000000
TOP_N = 40
CONFIDENCE_THRESHOLD = 80
MAX_WORKERS = 10
SCAN_INTERVAL = 300

def get_top_coins_by_volume():
    print("\n📡 Fetching top USDT pairs from Binance...")
    try:
        exchange = ccxt.binance()
        markets = exchange.load_markets()
        usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]
        print(f"   Found {len(usdt_pairs)} USDT pairs. Fetching volumes...")
        tickers = exchange.fetch_tickers()
        coins = []
        for symbol in usdt_pairs:
            ticker = tickers.get(symbol)
            if ticker and ticker.get('quoteVolume'):
                volume = ticker['quoteVolume']
                if volume > MIN_VOLUME_USD:
                    coins.append({
                        'symbol': symbol.split('/')[0],
                        'volume': volume,
                        'price': ticker['last']
                    })
        coins.sort(key=lambda x: x['volume'], reverse=True)
        top_coins = coins[:TOP_N]
        print(f"   ✅ Top {len(top_coins)} coins selected (by 24h volume)")
        return top_coins
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def fetch_ohlcv(symbol):
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

def quick_analyze(df, current_price):
    if df is None or len(df) < 50:
        return None
    
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    
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
    
    raw_prob = 50 + (score / 5) * 50
    probability = max(5, min(95, raw_prob))
    direction = "🟢 BUY" if score > 0.5 else "🔴 SELL" if score < -0.5 else "⏸️ HOLD"
    
    return {
        "rsi": rsi, "macd_hist": macd_hist, "score": score,
        "probability": probability, "direction": direction,
        "price_change": price_change, "atr": atr
    }

def scan_coin_parallel(coin):
    symbol = coin['symbol']
    price = coin['price']
    df = fetch_ohlcv(symbol)
    if df is None:
        return None
    analysis = quick_analyze(df, price)
    if analysis and analysis['probability'] >= CONFIDENCE_THRESHOLD:
        return {
            'symbol': symbol,
            'price': price,
            'rsi': analysis['rsi'],
            'score': analysis['score'],
            'probability': analysis['probability'],
            'direction': analysis['direction'],
            'price_change': analysis['price_change'],
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
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scan_coin_parallel, coin): coin for coin in top_coins}
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                results.append(result)
            if completed % 5 == 0 or completed == len(top_coins):
                print(f"   ⏳ Scanned {completed}/{len(top_coins)} coins... ({len(results)} high-confidence signals found)")
    
    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

def run():
    print("\n" + "=" * 80)
    print("🚀 ELITE MARKET SCANNER (OPTIMIZED - PARALLEL FETCHING)")
    print("   🔍 Scanning TOP 40 liquid coins...")
    print("   ⚡ Parallel processing: 10x faster!")
    print("=" * 80)
    
    scan_count = 0
    
    while True:
        scan_count += 1
        print("\n" + "=" * 80)
        print(f"🚀 ELITE SCAN #{scan_count} (Parallel Mode)")
        print("=" * 80)
        
        start = time.time()
        results = scan_market()
        duration = time.time() - start
        
        print("\n" + "=" * 80)
        print(f"🔥 ELITE SIGNALS ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"   Total coins scanned: {TOP_N} | High-confidence signals: {len(results)}")
        print("=" * 80)
        
        if not results:
            print("\n   😴 No high-confidence signals found right now.")
        else:
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
        
        print(f"\n⏱️ Scan completed in {duration:.1f} seconds")
        print(f"⏳ Next scan in {SCAN_INTERVAL//60} minutes... (Press Ctrl+C to stop)")
        
        try:
            time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 Scanner stopped.")
            break

if __name__ == "__main__":
    run()