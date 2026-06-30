import yfinance as yf
import requests
import ccxt
import time
from textblob import TextBlob
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 70)
print("🌍 ULTIMATE MULTI-SOURCE LIVE DATA & SIGNAL BOT")
print("   Sources: Binance | Coinbase | Kraken | DexScreener | CoinGecko | Yahoo Finance")
print("=" * 70)

# --- USER INPUT ---
symbol_input = input("\n🔍 Enter symbol (e.g., BTC, ETH, SUI, DOGE, PEPE, AAPL, TSLA): ").strip().upper()

if not symbol_input:
    symbol_input = "BTC"
    print(f"⚠️ Defaulting to {symbol_input}")

print(f"\n📡 Scanning ALL sources for {symbol_input}...\n")
print("-" * 70)

# ============================================================================
# 1. PRICE FETCHERS (MULTIPLE SOURCES)
# ============================================================================

def fetch_binance(symbol):
    """Binance - Fastest, most liquid"""
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker(f'{symbol}/USDT')
        ohlcv = exchange.fetch_ohlcv(f'{symbol}/USDT', '1m', limit=500)
        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
        else:
            df = None
        return {
            "source": "Binance",
            "price": ticker['last'],
            "high": ticker['high'],
            "low": ticker['low'],
            "volume": ticker['baseVolume'],
            "df": df,
            "success": True
        }
    except:
        return {"success": False, "source": "Binance"}

def fetch_coinbase(symbol):
    """Coinbase - Popular US exchange"""
    try:
        exchange = ccxt.coinbase()
        ticker = exchange.fetch_ticker(f'{symbol}/USDT')
        return {
            "source": "Coinbase",
            "price": ticker['last'],
            "high": ticker['high'],
            "low": ticker['low'],
            "volume": ticker['baseVolume'],
            "df": None,
            "success": True
        }
    except:
        return {"success": False, "source": "Coinbase"}

def fetch_kraken(symbol):
    """Kraken - European favorite"""
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(f'{symbol}/USDT')
        return {
            "source": "Kraken",
            "price": ticker['last'],
            "high": ticker['high'],
            "low": ticker['low'],
            "volume": ticker['baseVolume'],
            "df": None,
            "success": True
        }
    except:
        return {"success": False, "source": "Kraken"}

def fetch_dexscreener(symbol):
    """DexScreener - Any token (shitcoins, DEX, new listings)"""
    try:
        url = f'https://api.dexscreener.com/latest/dex/search?q={symbol}'
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('pairs') and len(data['pairs']) > 0:
            pair = data['pairs'][0]
            return {
                "source": f"DexScreener ({pair.get('dexId', 'DEX')})",
                "price": float(pair['priceUsd']),
                "high": float(pair.get('priceHigh', pair['priceUsd'])),
                "low": float(pair.get('priceLow', pair['priceUsd'])),
                "volume": float(pair.get('volumeUsd', 0)),
                "df": None,
                "success": True
            }
        return {"success": False, "source": "DexScreener"}
    except:
        return {"success": False, "source": "DexScreener"}

def fetch_coingecko(symbol):
    """CoinGecko - Global average price, market cap, volume"""
    try:
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'USDT': 'tether',
            'BNB': 'binancecoin', 'SOL': 'solana', 'XRP': 'ripple',
            'ADA': 'cardano', 'DOGE': 'dogecoin', 'DOT': 'polkadot',
            'LINK': 'chainlink', 'AVAX': 'avalanche-2', 'MATIC': 'matic-network',
            'UNI': 'uniswap', 'LTC': 'litecoin', 'BCH': 'bitcoin-cash',
            'ATOM': 'cosmos', 'ETC': 'ethereum-classic', 'SUI': 'sui'
        }
        gecko_id = symbol_map.get(symbol, symbol.lower())
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={gecko_id}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true'
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and gecko_id in data:
            price = data[gecko_id]['usd']
            return {
                "source": "CoinGecko",
                "price": price,
                "high": price * 1.02,  # Approx high
                "low": price * 0.98,   # Approx low
                "volume": data[gecko_id].get('usd_24h_vol', 0),
                "df": None,
                "success": True
            }
        return {"success": False, "source": "CoinGecko"}
    except:
        return {"success": False, "source": "CoinGecko"}

import time
from functools import wraps

def retry_on_timeout(max_retries=3, base_delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "timeout" in str(e).lower() or "curl" in str(e).lower():
                        delay = base_delay * (2 ** attempt)  # 2, 4, 8 seconds
                        print(f"      ⏳ Retry {attempt+1}/{max_retries} after {delay}s...")
                        time.sleep(delay)
                    else:
                        raise
            return {"success": False, "source": "Yahoo"}
        return wrapper
    return decorator

@retry_on_timeout(max_retries=3, base_delay=2)
def fetch_yahoo(symbol):
    """Yahoo Finance - Stocks & Crypto backup"""
    try:
        # Crypto ke liye Yahoo ka format: BTC-USD, ETH-USD, etc.
        # BNB ka ticker Yahoo par 'BNB-USD' nahi hai, shayad 'BNBUSD=X' try karo
        yf_symbol = symbol
        if symbol not in ["AAPL", "TSLA", "AMZN", "MSFT", "GOOGL", "NVDA"]:
            # Crypto ke liye kuch alag format ho sakta hai
            yf_symbol = f"{symbol}-USD"  # default
            # Special cases:
            if symbol == "BNB":
                yf_symbol = "BNB-USD"  # try this
        ticker = yf.Ticker(yf_symbol)
        # timeout 30 seconds
        data = ticker.history(period="5d", interval="1m", progress=False, timeout=30)
        if data.empty:
            # Try with =X suffix for crypto
            yf_symbol_alt = f"{symbol}USD=X"
            ticker_alt = yf.Ticker(yf_symbol_alt)
            data = ticker_alt.history(period="5d", interval="1m", progress=False, timeout=30)
        if data.empty:
            return {"success": False, "source": "Yahoo"}
        df = data
        return {
            "source": "Yahoo Finance",
            "price": float(df['Close'].iloc[-1]),
            "high": float(df['High'].iloc[-1]),
            "low": float(df['Low'].iloc[-1]),
            "volume": float(df['Volume'].iloc[-1]),
            "df": df,
            "success": True
        }
    except Exception as e:
        # Silently fail, let other sources handle
        return {"success": False, "source": "Yahoo"}

# ============================================================================
# 2. MASTER FETCHER (TRY ALL SOURCES, GET THE BEST)
# ============================================================================

def fetch_from_all_sources(symbol):
    print("   🔍 Scanning sources...")
    sources = [
        fetch_binance,
        fetch_coinbase,
        fetch_kraken,
        fetch_dexscreener,
        fetch_coingecko,
        fetch_yahoo
    ]
    
    results = []
    for fetcher in sources:
        print(f"      Trying {fetcher.__name__.replace('fetch_', '').title()}...", end=" ")
        result = fetcher(symbol)
        if result.get('success'):
            print("✅ Found!")
            results.append(result)
        else:
            print("❌ Not found.")
    
    if not results:
        return None
    
    # Sort by priority: Binance > Coinbase > Kraken > DexScreener > CoinGecko > Yahoo
    # We'll just pick the first one found as default (Binance is first)
    # But we want the most reliable: Binance if available, else DexScreener, else Yahoo
    priority_order = ['Binance', 'Coinbase', 'Kraken', 'DexScreener', 'CoinGecko', 'Yahoo Finance']
    for source_name in priority_order:
        for r in results:
            if source_name in r['source']:
                return r
    
    return results[0]  # Fallback

# ============================================================================
# 3. NEWS FETCHER (MULTIPLE SOURCES)
# ============================================================================

def fetch_news_cryptopanic(symbol):
    """CryptoPanic - Crypto news aggregator (FREE, no API key for public)"""
    try:
        url = f'https://cryptopanic.com/api/v1/posts/?auth_token=8f3c2c5c9c3c3c3c3c3c3c3c3c3c3c3c&public=true&currencies={symbol}'
        # Note: The above token is a dummy. For production, get free token from cryptopanic.com
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            headlines = []
            for post in data.get('results', [])[:5]:
                if 'title' in post:
                    headlines.append(post['title'])
            if headlines:
                combined = " ".join(headlines)
                blob = TextBlob(combined)
                return blob.sentiment.polarity, headlines
    except:
        pass
    
    # Fallback: Yahoo Finance News (already working)
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            headlines = []
            for news in data.get('news', [])[:5]:
                if 'title' in news:
                    headlines.append(news['title'])
            if headlines:
                combined = " ".join(headlines)
                blob = TextBlob(combined)
                return blob.sentiment.polarity, headlines
    except:
        pass
    
    return 0.0, ["No news available"]

# ============================================================================
# 4. TECHNICAL ANALYSIS
# ============================================================================

def analyze_technical(df):
    if df is None or len(df) < 30:
        return None
    
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    volume = df['Volume'].squeeze()
    
    current_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    day_change = ((current_price - prev_price) / prev_price) * 100
    
    # Indicators
    rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
    macd_indicator = MACD(close=close)
    macd_histogram = float(macd_indicator.macd_diff().iloc[-1])
    
    bb = BollingerBands(close=close, window=20, window_dev=2)
    bb_high = float(bb.bollinger_hband().iloc[-1])
    bb_low = float(bb.bollinger_lband().iloc[-1])
    
    atr = float(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])
    sma_50 = float(SMAIndicator(close=close, window=50).sma_indicator().iloc[-1])
    sma_20 = float(SMAIndicator(close=close, window=20).sma_indicator().iloc[-1])
    
    stoch = StochasticOscillator(high=high, low=low, close=close, window=14)
    stoch_k = float(stoch.stoch().iloc[-1])
    stoch_d = float(stoch.stoch_signal().iloc[-1])
    
    # Score
    tech_score = 0
    if rsi < 30: tech_score += 1
    if rsi > 70: tech_score -= 1
    if macd_histogram > 0: tech_score += 1
    if macd_histogram < 0: tech_score -= 1
    if current_price < bb_low: tech_score += 1
    if current_price > bb_high: tech_score -= 1
    if current_price > sma_50: tech_score += 1
    if current_price < sma_50: tech_score -= 1
    if stoch_k < 20 and stoch_d < 20: tech_score += 1
    if stoch_k > 80 and stoch_d > 80: tech_score -= 1
    
    return {
        "current_price": current_price,
        "day_change": day_change,
        "rsi": rsi,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "macd_histogram": macd_histogram,
        "bb_high": bb_high,
        "bb_low": bb_low,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "atr": atr,
        "tech_score": tech_score
    }

# ============================================================================
# 5. MAIN EXECUTION
# ============================================================================

# --- FETCH DATA FROM ALL SOURCES ---
best_data = fetch_from_all_sources(symbol_input)

if not best_data:
    print(f"\n❌ No data found for {symbol_input} from any source.")
    exit()

print("\n" + "-" * 70)
print(f"✅ BEST SOURCE FOUND: {best_data['source']}")
print("-" * 70)

# --- GET NEWS ---
sentiment_score, news_headlines = fetch_news_cryptopanic(symbol_input)

# --- TECHNICAL ANALYSIS ---
df = best_data.get('df')
analysis = analyze_technical(df) if df is not None else None

# If no df from the best source, try to get from Yahoo as fallback
if analysis is None:
    try:
        yf_symbol = symbol_input if symbol_input in ["AAPL", "TSLA", "AMZN", "MSFT", "GOOGL", "NVDA"] else f"{symbol_input}-USD"
        df_yahoo = yf.download(yf_symbol, period="3d", interval="1m", progress=False)
        if not df_yahoo.empty:
            analysis = analyze_technical(df_yahoo)
    except:
        pass

# --- GENERATE SIGNAL ---
tech_score = analysis['tech_score'] if analysis else 0
total_score = (tech_score * 0.6) + (sentiment_score * 0.4)

if total_score > 1.2:
    signal, confidence = "🟢 STRONG BUY", min(abs(total_score) / 2.0, 1.0) * 100
elif total_score > 0.5:
    signal, confidence = "🟢 BUY", min(abs(total_score) / 2.0, 1.0) * 100
elif total_score < -1.2:
    signal, confidence = "🔴 STRONG SELL", min(abs(total_score) / 2.0, 1.0) * 100
elif total_score < -0.5:
    signal, confidence = "🔴 SELL", min(abs(total_score) / 2.0, 1.0) * 100
else:
    signal, confidence = "⏸️ HOLD", 50

# --- DISPLAY REPORT ---
print("\n" + "=" * 70)
print(f"📈 ULTIMATE REPORT: {symbol_input}")
print("=" * 70)

print(f"\n📊 PRICE SUMMARY")
print("-" * 50)
print(f"   Source:               {best_data['source']}")
print(f"   Current Price:        ${best_data['price']:.6f}")
if best_data.get('high'):
    print(f"   High (24h):           ${best_data['high']:.6f}")
if best_data.get('low'):
    print(f"   Low (24h):            ${best_data['low']:.6f}")
if best_data.get('volume'):
    print(f"   Volume:               {best_data['volume']:,.0f}")

if analysis:
    print(f"\n📊 TECHNICAL ANALYSIS")
    print("-" * 50)
    print(f"   Price Change (1m):    {analysis['day_change']:.2f}%")
    print(f"   RSI (14):             {analysis['rsi']:.1f}")
    status = "OVERSOLD 🔥" if analysis['rsi'] < 30 else "OVERBOUGHT ⚠️" if analysis['rsi'] > 70 else "NEUTRAL"
    print(f"   ⚡ RSI Status:         {status}")
    print(f"   MACD Histogram:       {analysis['macd_histogram']:.3f}")
    print(f"   ⚡ MACD Status:       {'BULLISH 🟢' if analysis['macd_histogram'] > 0 else 'BEARISH 🔴'}")
    print(f"   Stochastic K/D:       {analysis['stoch_k']:.1f} / {analysis['stoch_d']:.1f}")
    print(f"   SMA 20:               ${analysis['sma_20']:.6f}")
    print(f"   SMA 50:               ${analysis['sma_50']:.6f}")
    print(f"   ATR (14):             ${analysis['atr']:.6f}")
    bb_pos = "Above Upper (Overbought)" if analysis['current_price'] > analysis['bb_high'] else "Below Lower (Oversold)" if analysis['current_price'] < analysis['bb_low'] else "Inside Bands"
    print(f"   Bollinger Position:   {bb_pos}")
    print(f"   Technical Score:      {analysis['tech_score']:.1f} / 10")

print(f"\n📰 NEWS SENTIMENT")
print("-" * 50)
print(f"   Sentiment Score:      {sentiment_score:.2f} (Range: -1 to +1)")
if sentiment_score > 0.2:
    print("   🔥 Sentiment:          POSITIVE")
elif sentiment_score < -0.2:
    print("   🔥 Sentiment:          NEGATIVE")
else:
    print("   🔥 Sentiment:          NEUTRAL")

if news_headlines:
    print(f"\n📰 Top Headlines:")
    for i, h in enumerate(news_headlines[:3]):
        print(f"   {i+1}. {h[:80]}{'...' if len(h) > 80 else ''}")

print(f"\n🎯 FINAL SIGNAL")
print("=" * 70)
print(f"   {signal}")
print(f"   Confidence:           {confidence:.1f}%")
print(f"   Total Score:          {total_score:.2f}")
print("=" * 70)

if analysis and analysis['atr'] > 0:
    print(f"\n💰 RISK MANAGEMENT")
    print("-" * 50)
    print(f"   Risk per trade:       2% of capital")
    pos_size = (10000 * 0.02) / (analysis['atr'] * 1.5)
    print(f"   Position Size:        {pos_size:.2f} units")
    print(f"   Stop-Loss:            ${analysis['current_price'] - (analysis['atr'] * 1.5):.6f}")
    print(f"   Take-Profit:          ${analysis['current_price'] + (analysis['atr'] * 3):.6f}")

print("\n" + "=" * 70)
print(f"✅ Analysis Complete! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
print("\n💡 Tip: Try 'BTC', 'ETH', 'SUI', 'PEPE', 'DOGE', 'AAPL', 'TSLA'")