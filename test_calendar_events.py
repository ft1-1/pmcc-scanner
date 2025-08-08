#!/usr/bin/env python3
"""Test that calendar events (earnings dates) are being collected in enhanced data."""

import asyncio
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.config import get_settings

async def test_calendar_events():
    """Test calendar events collection."""
    settings = get_settings()
    
    # Create enhanced EODHD provider
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
    
    symbol = "AAPL"
    print(f"\n🔍 Testing enhanced data collection for {symbol}...")
    
    # Test comprehensive enhanced data
    print("\n1. Testing get_comprehensive_enhanced_data()...")
    response = await provider.get_comprehensive_enhanced_data(symbol)
    
    if response.is_success and response.data:
        data = response.data
        print(f"✅ Successfully collected enhanced data")
        print(f"   Data keys: {list(data.keys())}")
        
        # Check if calendar_events is included
        if 'calendar_events' in data:
            print(f"\n✅ CALENDAR EVENTS INCLUDED!")
            calendar_events = data['calendar_events']
            if calendar_events:
                print(f"   Found {len(calendar_events)} calendar events:")
                for event in calendar_events[:3]:  # Show first 3
                    if isinstance(event, dict):
                        print(f"   - {event.get('event_type', 'Unknown')}: {event.get('date', 'No date')}")
                    else:
                        print(f"   - {event.event_type}: {event.date}")
            else:
                print("   No calendar events found for this period")
        else:
            print("\n❌ CALENDAR EVENTS NOT INCLUDED in comprehensive data!")
    else:
        print(f"❌ Failed to collect enhanced data: {response.error}")
    
    # Test calendar events directly
    print("\n2. Testing get_calendar_events() directly...")
    calendar_response = await provider.get_calendar_events(symbol)
    
    if calendar_response.is_success:
        events = calendar_response.data
        print(f"✅ Direct calendar events call successful")
        if events:
            print(f"   Found {len(events)} events:")
            for event in events[:5]:  # Show first 5
                if hasattr(event, 'event_type'):
                    print(f"   - {event.event_type}: {event.date} {getattr(event, 'announcement_time', '')}")
                    if event.event_type == 'earnings' and hasattr(event, 'estimated_eps'):
                        print(f"     EPS estimate: ${event.estimated_eps}")
                else:
                    print(f"   - Raw event: {event}")
        else:
            print("   No calendar events found")
    else:
        print(f"❌ Failed to get calendar events: {calendar_response.error}")
    
    await provider.close()

if __name__ == "__main__":
    print("=" * 80)
    print("CALENDAR EVENTS COLLECTION TEST")
    print("=" * 80)
    asyncio.run(test_calendar_events())