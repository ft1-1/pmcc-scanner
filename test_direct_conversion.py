#!/usr/bin/env python3
"""Test the conversion method directly with mock data."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
import logging

# Minimal logging
logging.basicConfig(level=logging.ERROR)

def test_conversion():
    """Test conversion with actual enhanced data."""
    
    # Get settings
    settings = get_settings()
    
    # Create enhanced provider
    provider_config = {
        'api_token': settings.eodhd_api_token,
        'enable_caching': False,
        'cache_ttl_hours': 0
    }
    
    enhanced_provider = SyncEnhancedEODHDProvider(
        provider_type=ProviderType.EODHD,
        config=provider_config
    )
    
    # Get comprehensive data
    print("Getting comprehensive enhanced data for KSS...")
    response = enhanced_provider.get_comprehensive_enhanced_data("KSS")
    
    if not response.is_success:
        print(f"Failed to get data: {response.error}")
        return
    
    enhanced_data = response.data
    print("Got enhanced data")
    
    # Now manually call each part of the conversion to find the error
    print("\nTesting conversion step by step...")
    
    # Import the scanner module and patch the method
    from src.analysis import scanner as scanner_module
    
    # Create a test instance
    class TestScanner:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
    
    test_scanner = TestScanner()
    
    # Get the method
    method = scanner_module.PMCCScanner._enhanced_stock_data_to_dict
    
    # Patch it to add debugging
    def debug_wrapper(self, enhanced_data):
        result = {'data_completeness': {}}
        
        print("\n1. Checking comprehensive_data type...")
        comprehensive_data = enhanced_data if isinstance(enhanced_data, dict) else None
        print(f"   Type: {type(comprehensive_data)}")
        
        if comprehensive_data:
            print("\n2. Processing quote data...")
            if 'quote' in comprehensive_data and comprehensive_data['quote']:
                quote_data = comprehensive_data['quote']
                print(f"   Quote type: {type(quote_data)}")
            
            print("\n3. Processing live_price data...")
            if 'live_price' in comprehensive_data and comprehensive_data['live_price']:
                live_price = comprehensive_data['live_price']
                print(f"   Live price type: {type(live_price)}")
                if isinstance(live_price, dict):
                    print(f"   Live price keys: {list(live_price.keys())}")
            
            print("\n4. Processing fundamentals...")
            if 'fundamentals' in comprehensive_data and comprehensive_data['fundamentals']:
                fund = comprehensive_data['fundamentals']
                print(f"   Fundamentals type: {type(fund)}")
                if hasattr(fund, '__dict__'):
                    print(f"   Fundamentals attributes: {list(vars(fund).keys())[:5]}...")
            
            print("\n5. Processing news...")
            if 'news' in comprehensive_data and comprehensive_data['news']:
                news_data = comprehensive_data['news']
                print(f"   News type: {type(news_data)}")
                if isinstance(news_data, list) and len(news_data) > 0:
                    print(f"   First news item type: {type(news_data[0])}")
                    if isinstance(news_data[0], dict):
                        print(f"   First news item keys: {list(news_data[0].keys())}")
                        # Check sentiment field
                        if 'sentiment' in news_data[0]:
                            print(f"   News sentiment type: {type(news_data[0]['sentiment'])}")
            
            print("\n6. Processing technical indicators...")
            if 'technical_indicators' in comprehensive_data and comprehensive_data['technical_indicators']:
                tech_data = comprehensive_data['technical_indicators']
                print(f"   Tech indicators type: {type(tech_data)}")
                if isinstance(tech_data, dict):
                    for ind_name, ind_data in tech_data.items():
                        print(f"   {ind_name}: {type(ind_data)}")
                        if isinstance(ind_data, list) and len(ind_data) > 0:
                            print(f"      First item type: {type(ind_data[0])}")
                            if isinstance(ind_data[0], dict):
                                print(f"      Keys: {list(ind_data[0].keys())}")
                        elif isinstance(ind_data, str):
                            print(f"      STRING VALUE: '{ind_data[:50]}...'")
            
            print("\n7. Processing earnings...")
            if 'earnings' in comprehensive_data and comprehensive_data['earnings']:
                earnings_data = comprehensive_data['earnings']
                print(f"   Earnings type: {type(earnings_data)}")
                if isinstance(earnings_data, dict):
                    print(f"   Earnings keys: {list(earnings_data.keys())}")
                    if 'earnings' in earnings_data:
                        print(f"   Earnings['earnings'] type: {type(earnings_data['earnings'])}")
            
            print("\n8. Processing sentiment...")
            if 'sentiment' in comprehensive_data and comprehensive_data['sentiment']:
                sentiment_data = comprehensive_data['sentiment']
                print(f"   Sentiment type: {type(sentiment_data)}")
                if isinstance(sentiment_data, dict):
                    print(f"   Sentiment keys: {list(sentiment_data.keys())}")
                    first_key = list(sentiment_data.keys())[0] if sentiment_data else None
                    if first_key:
                        print(f"   Sentiment['{first_key}'] type: {type(sentiment_data[first_key])}")
        
        # Now try the actual conversion
        print("\n9. Attempting actual conversion...")
        try:
            return method(self, enhanced_data)
        except AttributeError as e:
            print(f"\n❌ FOUND THE ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # Test the wrapper
    try:
        result = debug_wrapper(test_scanner, enhanced_data)
        print("\n✅ Conversion successful!")
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")

if __name__ == "__main__":
    test_conversion()