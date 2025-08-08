#!/usr/bin/env python3
"""Test that we're getting future earnings dates."""

import asyncio
from datetime import datetime, date, timedelta
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.config import get_settings

async def test_future_earnings():
    """Test future earnings collection."""
    settings = get_settings()
    
    provider = EnhancedEODHDProvider(
        provider_type=ProviderType.EODHD,
        config={
            'api_token': settings.eodhd.api_token,
            'base_url': settings.eodhd.base_url,
            'exchange': 'US',
            'timeout': settings.eodhd.timeout_seconds,
            'max_retries': settings.eodhd.max_retries
        }
    )
    
    # Test with companies likely to have earnings coming up
    symbols = ["AAPL", "MSFT", "GOOGL"]
    today = date.today()
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Testing {symbol}")
        print('='*60)
        
        # Test get_earnings_data (which now extends into the future)
        print("\n1. Testing get_earnings_data() with future dates...")
        earnings_response = await provider.get_earnings_data(symbol)
        
        if earnings_response.is_success and earnings_response.data:
            print(f"✅ Got earnings data")
            
            # Parse the response
            earnings_data = earnings_response.data
            if isinstance(earnings_data, dict):
                print(f"   Response type: {type(earnings_data)}")
                print(f"   Keys: {list(earnings_data.keys())}")
                
                # The EODHD API returns earnings in a specific format
                earnings_list = earnings_data.get('earnings', [])
                if earnings_list:
                    future_earnings = []
                    past_earnings = []
                    
                    for event in earnings_list:
                        event_date_str = event.get('date', '')
                        if event_date_str:
                            try:
                                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                                if event_date > today:
                                    future_earnings.append(event)
                                else:
                                    past_earnings.append(event)
                            except:
                                pass
                    
                    print(f"\n   📅 FUTURE EARNINGS: {len(future_earnings)}")
                    for event in future_earnings[:3]:  # Show up to 3
                        print(f"      - Date: {event.get('date')}")
                        print(f"        EPS Estimate: {event.get('eps_estimate', 'N/A')}")
                        print(f"        Has Actual: {'eps_actual' in event}")
                    
                    print(f"\n   📊 PAST EARNINGS: {len(past_earnings)}")
                    for event in past_earnings[:2]:  # Show 2 most recent
                        print(f"      - Date: {event.get('date')}")
                        print(f"        EPS Actual: {event.get('eps_actual', 'N/A')}")
                        print(f"        EPS Estimate: {event.get('eps_estimate', 'N/A')}")
        else:
            print(f"❌ Failed to get earnings data: {earnings_response.error if hasattr(earnings_response, 'error') else 'Unknown'}")
        
        # Test comprehensive enhanced data
        print("\n2. Testing comprehensive enhanced data...")
        enhanced_response = await provider.get_comprehensive_enhanced_data(symbol)
        
        if enhanced_response.is_success and enhanced_response.data:
            data = enhanced_response.data
            
            # Check earnings data
            if 'earnings' in data:
                print("✅ Earnings included in comprehensive data")
            
            # Check calendar events
            if 'calendar_events' in data:
                print("✅ Calendar events included in comprehensive data")
                cal_events = data['calendar_events']
                if cal_events:
                    earnings_events = [e for e in cal_events if hasattr(e, 'event_type') and e.event_type == 'earnings']
                    print(f"   Found {len(earnings_events)} earnings events in calendar")
        
    await provider.close()

if __name__ == "__main__":
    print("TESTING FUTURE EARNINGS DATA COLLECTION")
    asyncio.run(test_future_earnings())