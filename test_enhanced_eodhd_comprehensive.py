#!/usr/bin/env python3
"""
Test script for comprehensive enhanced EODHD data collection.

This script tests the new comprehensive data collection methods in the enhanced
EODHD provider, including all 8 data types:
1. Economic Events
2. Company News  
3. Fundamental Data (filtered)
4. Live Price
5. Earnings Data
6. Historical Prices
7. Sentiment Analysis
8. Technical Indicators
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType

async def test_comprehensive_data_collection():
    """Test comprehensive enhanced data collection for a sample stock"""
    
    print("Enhanced EODHD Comprehensive Data Collection Test")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    
    # Check if EODHD is configured
    if not settings.eodhd.api_token:
        print("❌ EODHD API token not configured. Please set EODHD_API_TOKEN environment variable.")
        return
    
    # Initialize provider
    provider_config = {
        'api_token': settings.eodhd.api_token,
        'base_url': settings.eodhd.base_url,
        'timeout': settings.eodhd.timeout_seconds,
        'enable_caching': True,
        'cache_ttl_hours': 24
    }
    
    provider = EnhancedEODHDProvider(ProviderType.EODHD, provider_config)
    
    # Test symbol
    symbol = 'AAPL'
    
    print(f"Testing comprehensive data collection for {symbol}...")
    print()
    
    try:
        # Test comprehensive data collection
        print("🔄 Collecting all 8 types of enhanced data...")
        response = await provider.get_comprehensive_enhanced_data(symbol)
        
        if response.is_success:
            data = response.data
            print("✅ Comprehensive data collection successful!")
            print()
            
            # Display summary of collected data
            print("📊 Data Collection Summary:")
            print("-" * 40)
            for data_type, content in data.items():
                if content:
                    if isinstance(content, list):
                        count = len(content)
                        print(f"✅ {data_type}: {count} items")
                        # Show sample of first item for lists
                        if count > 0 and isinstance(content[0], dict):
                            sample_keys = list(content[0].keys())[:3]
                            print(f"   Sample keys: {sample_keys}")
                    elif isinstance(content, dict):
                        count = len(content)
                        print(f"✅ {data_type}: {count} fields")
                        # Show sample keys for dicts
                        if count > 0:
                            sample_keys = list(content.keys())[:5]
                            print(f"   Sample keys: {sample_keys}")
                    else:
                        print(f"✅ {data_type}: Available")
                else:
                    print(f"❌ {data_type}: No data")
            
            print()
            
            # Test individual data collection methods
            print("🔍 Testing individual data collection methods:")
            print("-" * 50)
            
            # 1. Economic Events
            try:
                econ_response = await provider.get_economic_events()
                status = "✅" if econ_response.is_success else "❌"
                print(f"{status} Economic Events: {'Success' if econ_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Economic Events: Error - {str(e)[:50]}...")
            
            # 2. Company News
            try:
                news_response = await provider.get_company_news(symbol)
                status = "✅" if news_response.is_success else "❌"
                print(f"{status} Company News: {'Success' if news_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Company News: Error - {str(e)[:50]}...")
            
            # 3. Live Price
            try:
                price_response = await provider.get_live_price(symbol)
                status = "✅" if price_response.is_success else "❌"
                print(f"{status} Live Price: {'Success' if price_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Live Price: Error - {str(e)[:50]}...")
            
            # 4. Earnings Data
            try:
                earnings_response = await provider.get_earnings_data(symbol)
                status = "✅" if earnings_response.is_success else "❌"
                print(f"{status} Earnings Data: {'Success' if earnings_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Earnings Data: Error - {str(e)[:50]}...")
            
            # 5. Historical Prices
            try:
                hist_response = await provider.get_historical_prices(symbol)
                status = "✅" if hist_response.is_success else "❌"
                print(f"{status} Historical Prices: {'Success' if hist_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Historical Prices: Error - {str(e)[:50]}...")
            
            # 6. Sentiment Data
            try:
                sentiment_response = await provider.get_sentiment_data(symbol)
                status = "✅" if sentiment_response.is_success else "❌"
                print(f"{status} Sentiment Data: {'Success' if sentiment_response.is_success else 'Failed'}")
            except Exception as e:
                print(f"❌ Sentiment Data: Error - {str(e)[:50]}...")
            
            # 7. Technical Indicators
            try:
                tech_response = await provider.get_technical_indicators_comprehensive(symbol)
                status = "✅" if tech_response.is_success else "❌"
                print(f"{status} Technical Indicators: {'Success' if tech_response.is_success else 'Failed'}")
                if tech_response.is_success and tech_response.data:
                    indicators = list(tech_response.data.keys())
                    print(f"   Available indicators: {indicators}")
            except Exception as e:
                print(f"❌ Technical Indicators: Error - {str(e)[:50]}...")
            
            # 8. Fundamental Data (filtered)
            try:
                fund_response = await provider.get_fundamental_data(symbol)
                status = "✅" if fund_response.is_success else "❌"
                print(f"{status} Fundamental Data (filtered): {'Success' if fund_response.is_success else 'Failed'}")
                if fund_response.is_success and fund_response.data:
                    if isinstance(fund_response.data, dict):
                        sections = list(fund_response.data.keys())
                        print(f"   Available sections: {sections}")
            except Exception as e:
                print(f"❌ Fundamental Data: Error - {str(e)[:50]}...")
            
            print()
            
            # Display filtered fundamental data structure if available
            if 'fundamentals' in data and data['fundamentals']:
                print("📈 Filtered Fundamental Data Structure:")
                print("-" * 45)
                fundamentals = data['fundamentals']
                for section, content in fundamentals.items():
                    if isinstance(content, dict):
                        field_count = len(content)
                        print(f"  {section}: {field_count} fields")
                        # Show a few sample fields
                        sample_fields = list(content.keys())[:3]
                        for field in sample_fields:
                            value = content[field]
                            if isinstance(value, (int, float)) and value is not None:
                                print(f"    - {field}: {value}")
                            elif isinstance(value, str) and len(value) < 50:
                                print(f"    - {field}: {value}")
                    else:
                        print(f"  {section}: {type(content).__name__}")
                print()
            
            # Save sample data to file for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol}_comprehensive_enhanced_data_{timestamp}.json"
            try:
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"💾 Sample data saved to: {filename}")
            except Exception as e:
                print(f"⚠️  Could not save data to file: {e}")
            
            # Provider statistics
            print()
            print("📊 Provider Performance:")
            print("-" * 30)
            print(f"Total API requests: {provider._request_count}")
            print(f"Error count: {provider._error_count}")
            print(f"Latency: {response.provider_metadata.response_latency_ms:.0f}ms")
            print(f"Provider: {response.provider_metadata.provider_name}")
            
        else:
            print(f"❌ Comprehensive data collection failed: {response.error}")
            if response.error:
                print(f"Error details: {response.error.message}")
    
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await provider.close()

def main():
    """Main function to run the comprehensive test"""
    try:
        asyncio.run(test_comprehensive_data_collection())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())