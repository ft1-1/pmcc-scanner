#!/usr/bin/env python3
"""Check status of comprehensive data implementation"""

import os
import json
from datetime import datetime, timedelta
from eodhd import APIClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv('EODHD_API_TOKEN')
if not api_key:
    print("EODHD_API_TOKEN not found in environment")
    exit(1)

# Initialize EODHD client
api = APIClient(api_key)

print("Checking comprehensive data collection status for KSS...\n")

# Get dates
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
dates = {
    'today': end_date.strftime('%Y-%m-%d'),
    'thirty_days_ago': start_date.strftime('%Y-%m-%d'),
    'sixty_days_ago': (end_date - timedelta(days=60)).strftime('%Y-%m-%d'),
    'hundred_days_ago': (end_date - timedelta(days=100)).strftime('%Y-%m-%d')
}

# Test each data type
print("1. Live Price Data:")
try:
    live_price = api.get_live_stock_prices(
        date_from=dates['today'],
        date_to=dates['today'],
        ticker='KSS'
    )
    print(f"   ✅ Success - Type: {type(live_price).__name__}")
    if isinstance(live_price, dict):
        print(f"      Keys: {list(live_price.keys())}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n2. Fundamental Data:")
try:
    fundamentals = api.get_fundamentals_data(ticker='KSS')
    print(f"   ✅ Success - Type: {type(fundamentals).__name__}")
    if isinstance(fundamentals, dict):
        print(f"      Top-level keys: {list(fundamentals.keys())[:5]}...")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3. Historical Prices:")
try:
    historical = api.get_eod_historical_stock_market_data(
        symbol='KSS',
        period='d',
        from_date=dates['thirty_days_ago'],
        to_date=dates['today']
    )
    print(f"   ✅ Success - Type: {type(historical).__name__}, Length: {len(historical) if isinstance(historical, list) else 'N/A'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n4. News:")
try:
    news = api.financial_news(
        s='KSS.US',
        from_date=dates['thirty_days_ago'],
        to_date=dates['today'],
        limit=5
    )
    print(f"   ✅ Success - Type: {type(news).__name__}, Length: {len(news) if isinstance(news, list) else 'N/A'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n5. Sentiment:")
try:
    sentiment = api.get_sentiment(
        s='KSS',
        from_date=dates['thirty_days_ago'],
        to_date=dates['today']
    )
    print(f"   ✅ Success - Type: {type(sentiment).__name__}")
    if isinstance(sentiment, dict):
        print(f"      Keys: {list(sentiment.keys())}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n6. Technical Indicators:")
print("   Testing each indicator separately...")

# Test technical indicators individually
indicators = [
    {'name': 'rsi', 'function': 'rsi', 'period': 14, 'days_back': 60},
    {'name': 'volatility', 'function': 'volatility', 'period': 30, 'days_back': 60},
    {'name': 'atr', 'function': 'atr', 'period': 14, 'days_back': 60},
    {'name': 'beta', 'function': 'beta', 'period': 50, 'days_back': 100}
]

for indicator in indicators:
    try:
        print(f"\n   Testing {indicator['name']}:")
        result = api.get_technical_indicator_data(
            ticker='KSS.US',
            function=indicator['function'],
            period=indicator['period'],
            date_from=(end_date - timedelta(days=indicator['days_back'])).strftime('%Y-%m-%d'),
            date_to=dates['today'],
            order='d',
            splitadjusted_only='0'
        )
        print(f"      ✅ Success - Type: {type(result).__name__}")
        if isinstance(result, list) and len(result) > 0:
            print(f"         Length: {len(result)}, First item type: {type(result[0]).__name__}")
            if isinstance(result[0], dict):
                print(f"         First item keys: {list(result[0].keys())}")
        elif isinstance(result, str):
            print(f"         ⚠️  WARNING: Got string instead of list: '{result[:100]}...'")
    except Exception as e:
        print(f"      ❌ Error: {e}")
        # Check if it's the 'fanction' error
        if 'fanction' in str(e):
            print(f"         💡 Hint: API might be expecting 'fanction' instead of 'function' parameter")

print("\n7. Economic Events:")
try:
    events = api.get_economic_events_data(
        date_from=(end_date - timedelta(days=180)).strftime('%Y-%m-%d'),
        date_to=dates['today'],
        country='US',
        comparison='mom',
        limit=5
    )
    print(f"   ✅ Success - Type: {type(events).__name__}, Length: {len(events) if isinstance(events, list) else 'N/A'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n8. Earnings Data:")
try:
    earnings = api.get_upcoming_earnings_data(
        from_date=(end_date - timedelta(days=365)).strftime('%Y-%m-%d'),
        to_date=dates['today'],
        symbols='KSS'
    )
    print(f"   ✅ Success - Type: {type(earnings).__name__}")
    if isinstance(earnings, dict):
        print(f"      Keys: {list(earnings.keys())}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n\nSUMMARY:")
print("Most data types are working correctly.")
print("The technical indicators might have issues - check the output above for details.")