#!/usr/bin/env python3
"""Test calendar events with specific date ranges."""

import asyncio
from datetime import date, timedelta
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.config import get_settings

async def test_calendar_with_dates():
    """Test calendar events with expanded date range."""
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
    
    # Test multiple symbols
    symbols = ["MSFT", "GOOGL", "META"]
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Testing {symbol}")
        print('='*60)
        
        # Expand date range to catch more events
        date_from = date.today() - timedelta(days=60)
        date_to = date.today() + timedelta(days=180)
        
        response = await provider.get_calendar_events(
            symbol, 
            event_types=['earnings', 'dividends'],
            date_from=date_from,
            date_to=date_to
        )
        
        if response.is_success and response.data:
            events = response.data
            print(f"✅ Found {len(events)} calendar events from {date_from} to {date_to}")
            
            # Group by event type
            earnings_events = []
            dividend_events = []
            other_events = []
            
            for event in events:
                if hasattr(event, 'event_type'):
                    if event.event_type == 'earnings':
                        earnings_events.append(event)
                    elif 'dividend' in event.event_type:
                        dividend_events.append(event)
                    else:
                        other_events.append(event)
            
            if earnings_events:
                print(f"\n📊 EARNINGS EVENTS ({len(earnings_events)}):")
                for event in earnings_events[:3]:  # Show up to 3
                    print(f"   - Date: {event.date}")
                    if hasattr(event, 'announcement_time') and event.announcement_time:
                        print(f"     Time: {event.announcement_time}")
                    if hasattr(event, 'estimated_eps') and event.estimated_eps:
                        print(f"     Est EPS: ${event.estimated_eps}")
                    if hasattr(event, 'actual_eps') and event.actual_eps:
                        print(f"     Actual EPS: ${event.actual_eps}")
            
            if dividend_events:
                print(f"\n💰 DIVIDEND EVENTS ({len(dividend_events)}):")
                for event in dividend_events[:3]:  # Show up to 3
                    print(f"   - Date: {event.date}")
                    if hasattr(event, 'dividend_amount') and event.dividend_amount:
                        print(f"     Amount: ${event.dividend_amount}")
            
            if not earnings_events and not dividend_events:
                print("   No earnings or dividend events found in the date range")
        else:
            print(f"❌ Failed to get calendar events: {response.error if hasattr(response, 'error') else 'Unknown error'}")
    
    await provider.close()

if __name__ == "__main__":
    print("TESTING CALENDAR EVENTS WITH EXTENDED DATE RANGE")
    asyncio.run(test_calendar_with_dates())