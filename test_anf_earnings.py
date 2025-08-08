#!/usr/bin/env python3
"""Test ANF earnings with updated date handling."""

import asyncio
from datetime import datetime
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.config import get_settings

async def test_anf_earnings():
    """Test ANF earnings data collection."""
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
    
    print("Testing ANF earnings data with updated date range...")
    print("="*80)
    
    # Test get_earnings_data
    earnings_response = await provider.get_earnings_data('ANF')
    
    if earnings_response.is_success and earnings_response.data:
        data = earnings_response.data
        print(f"✅ Got earnings data")
        
        if isinstance(data, dict) and 'earnings' in data:
            earnings_list = data['earnings']
            print(f"Total earnings events: {len(earnings_list)}")
            
            today = datetime.now().date()
            
            print("\nAll ANF earnings events:")
            for event in earnings_list:
                date_str = event.get('date', 'N/A')
                report_date_str = event.get('report_date', 'N/A')
                
                # Determine if future based on report_date
                is_future = False
                if report_date_str != 'N/A':
                    report_dt = datetime.strptime(report_date_str, '%Y-%m-%d').date()
                    is_future = report_dt > today
                
                status = "FUTURE" if is_future else "PAST"
                
                print(f"\n{status} Earnings:")
                print(f"  Quarter End: {date_str}")
                print(f"  Report Date: {report_date_str}")
                print(f"  Time: {event.get('before_after_market', 'N/A')}")
                print(f"  EPS Estimate: {event.get('estimate', 'N/A')}")
                print(f"  EPS Actual: {event.get('actual', 'N/A')}")
    else:
        print(f"❌ Failed to get earnings data")
    
    await provider.close()

if __name__ == "__main__":
    asyncio.run(test_anf_earnings())