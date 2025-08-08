#!/usr/bin/env python3
"""Compare example API calls with our implementation."""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from eodhd import APIClient

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('EODHD_API_TOKEN')
api = APIClient(api_key)

print("🔍 EODHD API Call Structure Comparison")
print("=" * 60)

# Test dates
today = datetime.now()
dates = {
    'today': today.strftime('%Y-%m-%d'),
    'thirty_days_ago': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
    'sixty_days_ago': (today - timedelta(days=60)).strftime('%Y-%m-%d'),
    'six_months_ago': (today - timedelta(days=180)).strftime('%Y-%m-%d'),
    'one_year_ago': (today - timedelta(days=365)).strftime('%Y-%m-%d'),
    'hundred_days_ago': (today - timedelta(days=100)).strftime('%Y-%m-%d')
}

ticker = 'KSS'

# Store results for comparison
results = {}

print(f"\n📊 Testing API calls for {ticker}")
print(f"Test date: {dates['today']}")
print("-" * 60)

# 1. ECONOMIC EVENTS
print("\n1️⃣ Economic Events API")
print("Example call: api.get_economic_events_data(date_from, date_to, country, comparison, offset, limit)")
try:
    econ_events = api.get_economic_events_data(
        date_from=dates['six_months_ago'],
        date_to=dates['today'],
        country='US',
        comparison='mom',
        offset=0,
        limit=30
    )
    results['economic_events'] = {
        'success': True,
        'type': type(econ_events).__name__,
        'count': len(econ_events) if isinstance(econ_events, list) else 'N/A',
        'sample': econ_events[0] if isinstance(econ_events, list) and len(econ_events) > 0 else econ_events
    }
    print(f"✅ Success: {results['economic_events']['type']} with {results['economic_events']['count']} items")
except Exception as e:
    results['economic_events'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 2. FINANCIAL NEWS
print("\n2️⃣ Financial News API")
print("Example call: api.financial_news(s, t, from_date, to_date, limit, offset)")
try:
    news = api.financial_news(
        s=f'{ticker}.US',
        t=None,
        from_date=dates['thirty_days_ago'],
        to_date=dates['today'],
        limit=5,
        offset=0
    )
    results['news'] = {
        'success': True,
        'type': type(news).__name__,
        'count': len(news) if isinstance(news, list) else 'N/A',
        'sample': news[0] if isinstance(news, list) and len(news) > 0 else news
    }
    print(f"✅ Success: {results['news']['type']} with {results['news']['count']} items")
except Exception as e:
    results['news'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 3. FUNDAMENTAL DATA
print("\n3️⃣ Fundamental Data API")
print("Example call: api.get_fundamentals_data(ticker)")
try:
    fundamentals = api.get_fundamentals_data(ticker=ticker)
    results['fundamentals'] = {
        'success': True,
        'type': type(fundamentals).__name__,
        'top_keys': list(fundamentals.keys())[:5] if isinstance(fundamentals, dict) else 'N/A'
    }
    print(f"✅ Success: {results['fundamentals']['type']} with keys: {results['fundamentals']['top_keys']}")
except Exception as e:
    results['fundamentals'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 4. LIVE PRICE - Test different parameter orders
print("\n4️⃣ Live Price API")
print("Testing different parameter combinations...")

# Test A: Named parameters (ticker first)
print("  A) Named params - ticker first:")
try:
    live_price_a = api.get_live_stock_prices(
        ticker=ticker,
        date_from=dates['today'],
        date_to=dates['today']
    )
    results['live_price_named'] = {
        'success': True,
        'type': type(live_price_a).__name__,
        'data': live_price_a
    }
    print(f"    ✅ Success: {type(live_price_a).__name__}")
    if isinstance(live_price_a, dict):
        for k, v in live_price_a.items():
            print(f"      {k}: {v}")
except Exception as e:
    results['live_price_named'] = {'success': False, 'error': str(e)}
    print(f"    ❌ Failed: {e}")

# Test B: Positional parameters (wrong order - dates first)
print("  B) Positional params - dates first (wrong):")
try:
    live_price_b = api.get_live_stock_prices(
        dates['today'],
        dates['today'],
        ticker
    )
    results['live_price_positional_wrong'] = {
        'success': True,
        'type': type(live_price_b).__name__,
        'data': live_price_b
    }
    print(f"    ✅ Result: {type(live_price_b).__name__}")
    if isinstance(live_price_b, dict):
        for k, v in live_price_b.items():
            if k == 'code':
                print(f"      {k}: {v} ⚠️ (Notice ticker is wrong!)")
except Exception as e:
    results['live_price_positional_wrong'] = {'success': False, 'error': str(e)}
    print(f"    ❌ Failed: {e}")

# 5. EARNINGS DATA
print("\n5️⃣ Earnings Data API")
print("Example call: api.get_upcoming_earnings_data(from_date, to_date, symbols)")
try:
    earnings = api.get_upcoming_earnings_data(
        from_date=dates['one_year_ago'],
        to_date=dates['today'],
        symbols=ticker
    )
    results['earnings'] = {
        'success': True,
        'type': type(earnings).__name__,
        'keys': list(earnings.keys()) if isinstance(earnings, dict) else 'N/A'
    }
    print(f"✅ Success: {results['earnings']['type']} with keys: {results['earnings']['keys']}")
except Exception as e:
    results['earnings'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 6. HISTORICAL PRICES
print("\n6️⃣ Historical Prices API")
print("Example call: api.get_eod_historical_stock_market_data(symbol, period, from_date, to_date, order)")
try:
    historical = api.get_eod_historical_stock_market_data(
        symbol=ticker,
        period='d',
        from_date=dates['thirty_days_ago'],
        to_date=dates['today'],
        order='d'
    )
    results['historical'] = {
        'success': True,
        'type': type(historical).__name__,
        'length': len(historical) if hasattr(historical, '__len__') else 'N/A'
    }
    print(f"✅ Success: {results['historical']['type']} with {results['historical']['length']} records")
except Exception as e:
    results['historical'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 7. SENTIMENT DATA
print("\n7️⃣ Sentiment Data API")
print("Example call: api.get_sentiment(s, from_date, to_date)")
try:
    sentiment = api.get_sentiment(
        s=ticker,
        from_date=dates['thirty_days_ago'],
        to_date=dates['today']
    )
    results['sentiment'] = {
        'success': True,
        'type': type(sentiment).__name__,
        'data': sentiment
    }
    print(f"✅ Success: {results['sentiment']['type']}")
except Exception as e:
    results['sentiment'] = {'success': False, 'error': str(e)}
    print(f"❌ Failed: {e}")

# 8. TECHNICAL INDICATORS
print("\n8️⃣ Technical Indicators API")
print("Example call: api.get_technical_indicator_data(ticker, function, period, date_from, date_to, order, splitadjusted_only)")

indicators = [
    {'name': 'rsi', 'function': 'rsi', 'period': 14, 'days_back': 60},
    {'name': 'volatility', 'function': 'volatility', 'period': 30, 'days_back': 60},
    {'name': 'atr', 'function': 'atr', 'period': 14, 'days_back': 60}
]

for indicator in indicators:
    print(f"\n  Testing {indicator['name']}:")
    try:
        days_back = (today - timedelta(days=indicator['days_back'])).strftime('%Y-%m-%d')
        result = api.get_technical_indicator_data(
            ticker=f'{ticker}.US',
            function=indicator['function'],
            period=indicator['period'],
            date_from=days_back,
            date_to=dates['today'],
            order='d',
            splitadjusted_only='0'
        )
        results[f'technical_{indicator["name"]}'] = {
            'success': True,
            'type': type(result).__name__,
            'length': len(result) if isinstance(result, list) else 'N/A',
            'sample': result[0] if isinstance(result, list) and len(result) > 0 else result
        }
        print(f"    ✅ Success: {type(result).__name__} with {len(result) if isinstance(result, list) else 'N/A'} records")
        if isinstance(result, list) and len(result) > 0:
            print(f"       Latest: {result[0]}")
    except Exception as e:
        results[f'technical_{indicator["name"]}'] = {'success': False, 'error': str(e)}
        print(f"    ❌ Failed: {e}")

# Save results for analysis
print("\n" + "=" * 60)
print("💾 Saving comparison results...")
output_file = "data/api_comparison_results.json"
Path("data").mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"Results saved to {output_file}")

# Summary
print("\n📊 Summary:")
success_count = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('success', False))
total_count = len(results)
print(f"Successful API calls: {success_count}/{total_count}")

print("\n🔑 Key Findings:")
print("1. Live Price API: ticker parameter must be first or named")
print("2. Technical indicators: Use ticker with .US suffix")
print("3. News API: Use ticker with .US suffix")
print("4. All date formats: YYYY-MM-DD")
print("5. Most APIs return lists except fundamentals (dict) and live price (dict)")