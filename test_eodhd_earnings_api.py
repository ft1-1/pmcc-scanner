#!/usr/bin/env python3
"""Test EODHD upcoming earnings API directly."""

import os
from datetime import datetime, timedelta
from eodhd import APIClient
from src.config import get_settings

def test_eodhd_earnings_api():
    """Test the EODHD upcoming earnings API."""
    settings = get_settings()
    api_token = settings.eodhd.api_token
    
    # Create EODHD client
    client = APIClient(api_token)
    
    # Test date ranges
    today = datetime.now()
    date_from = today.strftime('%Y-%m-%d')
    date_to = (today + timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f"Testing EODHD upcoming earnings API")
    print(f"Date range: {date_from} to {date_to}")
    print("="*80)
    
    # Test 1: Get all upcoming earnings in date range
    print("\n1. Testing general upcoming earnings (no symbol filter)...")
    try:
        response = client.get_upcoming_earnings_data(
            from_date=date_from,
            to_date=date_to
        )
        
        if response:
            print(f"✅ Got response: {type(response)}")
            if isinstance(response, dict):
                print(f"   Keys: {list(response.keys())}")
                if 'earnings' in response:
                    earnings_list = response['earnings']
                    print(f"   Total earnings events: {len(earnings_list)}")
                    
                    # Show first few
                    for i, event in enumerate(earnings_list[:5]):
                        print(f"\n   Event {i+1}:")
                        print(f"     Symbol: {event.get('code', 'N/A')}")
                        print(f"     Date: {event.get('date', 'N/A')}")
                        print(f"     EPS Estimate: {event.get('estimate', 'N/A')}")
                        print(f"     Time: {event.get('before_after_market', 'N/A')}")
            else:
                print(f"   Unexpected response type: {response}")
        else:
            print("❌ No response from API")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Get upcoming earnings for specific symbols
    symbols = ['AAPL.US', 'MSFT.US', 'ANF.US']
    
    for symbol in symbols:
        print(f"\n2. Testing upcoming earnings for {symbol}...")
        try:
            response = client.get_upcoming_earnings_data(
                from_date=date_from,
                to_date=date_to,
                symbols=symbol
            )
            
            if response:
                print(f"✅ Got response")
                if isinstance(response, dict) and 'earnings' in response:
                    earnings_list = response['earnings']
                    print(f"   Earnings events for {symbol}: {len(earnings_list)}")
                    
                    for event in earnings_list:
                        event_date = event.get('date', 'N/A')
                        if event_date != 'N/A':
                            # Check if future
                            event_dt = datetime.strptime(event_date, '%Y-%m-%d')
                            is_future = event_dt.date() > today.date()
                            
                            print(f"\n   Date: {event_date} {'(FUTURE)' if is_future else '(PAST)'}")
                            print(f"   EPS Estimate: {event.get('estimate', 'N/A')}")
                            print(f"   Time: {event.get('before_after_market', 'N/A')}")
                            
                            # Check if actual results are present
                            if 'actual' in event:
                                print(f"   EPS Actual: {event.get('actual', 'N/A')} (historical)")
                else:
                    print(f"   No earnings data in response")
            else:
                print("❌ No response")
                
        except Exception as e:
            print(f"❌ Error for {symbol}: {e}")
    
    # Test 3: Try different date ranges
    print("\n3. Testing different date ranges...")
    
    # Try next earnings season (typically Jan/Apr/Jul/Oct)
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1
    
    # Find next earnings month (quarterly)
    earnings_months = [1, 4, 7, 10]
    next_earnings_month = min([m for m in earnings_months if m >= next_month] or [earnings_months[0]])
    if next_earnings_month < next_month:
        next_year += 1
    
    season_start = datetime(next_year, next_earnings_month, 1)
    season_end = season_start + timedelta(days=45)
    
    print(f"\nTrying earnings season: {season_start.strftime('%Y-%m-%d')} to {season_end.strftime('%Y-%m-%d')}")
    
    try:
        response = client.get_upcoming_earnings_data(
            from_date=season_start.strftime('%Y-%m-%d'),
            to_date=season_end.strftime('%Y-%m-%d'),
            symbols='AAPL.US'
        )
        
        if response and 'earnings' in response:
            print(f"✅ Found {len(response['earnings'])} earnings events for AAPL in next earnings season")
        else:
            print("❌ No earnings found in next earnings season")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_eodhd_earnings_api()