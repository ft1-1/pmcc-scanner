#!/usr/bin/env python3
"""Test comprehensive EODHD data collection"""

import os
import json
from datetime import datetime
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

# Test comprehensive data collection
symbol = 'KSS'
print(f"Collecting comprehensive data for {symbol}...")

try:
    # 1. Live/EOD price
    print("\n1. Fetching live price...")
    live_price = api.get_live_stock_prices(
        date_from=datetime.now().strftime('%Y-%m-%d'),
        date_to=datetime.now().strftime('%Y-%m-%d'),
        ticker=symbol
    )
    print(f"   Live price data: {len(live_price) if isinstance(live_price, list) else 'Not a list'} items")
    
    # 2. Fundamental data
    print("\n2. Fetching fundamentals...")
    fundamentals = api.get_fundamentals_data(ticker=symbol)
    print(f"   Fundamental data keys: {list(fundamentals.keys()) if isinstance(fundamentals, dict) else 'Not a dict'}")
    
    # 3. Historical prices (30 days)
    print("\n3. Fetching historical prices...")
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    historical = api.get_eod_historical_stock_market_data(
        symbol=symbol,
        period='d',
        from_date=start_date.strftime('%Y-%m-%d'),
        to_date=end_date.strftime('%Y-%m-%d')
    )
    print(f"   Historical data: {len(historical) if isinstance(historical, list) else 'Not a list'} days")
    
    # 4. News
    print("\n4. Fetching news...")
    news = api.financial_news(
        s=f'{symbol}.US',
        from_date=start_date.strftime('%Y-%m-%d'),
        to_date=end_date.strftime('%Y-%m-%d'),
        limit=5
    )
    print(f"   News items: {len(news) if isinstance(news, list) else 'Not a list'}")
    
    # 5. Sentiment
    print("\n5. Fetching sentiment...")
    sentiment = api.get_sentiment(
        s=symbol,
        from_date=start_date.strftime('%Y-%m-%d'),
        to_date=end_date.strftime('%Y-%m-%d')
    )
    print(f"   Sentiment data type: {type(sentiment).__name__}")
    
    # 6. Technical indicators
    print("\n6. Fetching technical indicators...")
    indicators = {}
    
    # RSI
    try:
        rsi = api.get_technical_indicator_data(
            ticker=f'{symbol}.US',
            function='rsi',
            period=14,
            date_from=(end_date - timedelta(days=60)).strftime('%Y-%m-%d'),
            date_to=end_date.strftime('%Y-%m-%d')
        )
        indicators['rsi'] = rsi
        print(f"   RSI data: {len(rsi) if isinstance(rsi, list) else type(rsi).__name__}")
    except Exception as e:
        print(f"   RSI error: {e}")
    
    # Save all data
    comprehensive_data = {
        'symbol': symbol,
        'timestamp': datetime.now().isoformat(),
        'live_price': live_price,
        'fundamentals': fundamentals,
        'historical_prices': historical,
        'news': news,
        'sentiment': sentiment,
        'technical_indicators': indicators
    }
    
    output_file = 'data/test_eodhd_comprehensive_kss.json'
    with open(output_file, 'w') as f:
        json.dump(comprehensive_data, f, indent=2, default=str)
    
    print(f"\n✅ Data saved to {output_file}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()