#!/usr/bin/env python3
"""Test scanner conversion to find the exact error."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner
import logging

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_scanner_conversion():
    """Test scanner conversion with enhanced data."""
    print("🧪 Testing Scanner Conversion")
    print("=" * 60)
    
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
    print("\n1️⃣ Getting comprehensive enhanced data for KSS...")
    response = enhanced_provider.get_comprehensive_enhanced_data("KSS")
    
    if not response.is_success:
        print(f"❌ Failed to get data: {response.error}")
        return False
    
    enhanced_data = response.data
    print(f"✅ Got enhanced data: {type(enhanced_data)}")
    
    # Save raw data
    with open("data/test_enhanced_data_raw.json", 'w') as f:
        # Convert FundamentalMetrics to dict for JSON serialization
        data_copy = enhanced_data.copy()
        if 'fundamentals' in data_copy and hasattr(data_copy['fundamentals'], '__dict__'):
            # Convert FundamentalMetrics object to dict
            fund_obj = data_copy['fundamentals']
            data_copy['fundamentals'] = {
                'market_capitalization': float(fund_obj.market_capitalization) if fund_obj.market_capitalization else 0,
                'pe_ratio': float(fund_obj.pe_ratio) if fund_obj.pe_ratio else 0,
                'pb_ratio': float(fund_obj.pb_ratio) if fund_obj.pb_ratio else 0,
                'ps_ratio': float(fund_obj.ps_ratio) if fund_obj.ps_ratio else 0,
                'roe': float(fund_obj.roe) if fund_obj.roe else 0,
                'roa': float(fund_obj.roa) if fund_obj.roa else 0,
                'profit_margin': float(fund_obj.profit_margin) if fund_obj.profit_margin else 0,
                'debt_to_equity': float(fund_obj.debt_to_equity) if fund_obj.debt_to_equity else 0,
                'revenue_growth_rate': float(fund_obj.revenue_growth_rate) if fund_obj.revenue_growth_rate else 0,
                'earnings_growth_rate': float(fund_obj.earnings_growth_rate) if fund_obj.earnings_growth_rate else 0,
            }
        json.dump(data_copy, f, indent=2, default=str)
    
    # Create a mock scanner for testing
    print("\n2️⃣ Testing scanner conversion method...")
    
    class MockScanner:
        def __init__(self):
            self.logger = logger
    
    mock_scanner = MockScanner()
    
    try:
        # Call the conversion method
        print("   Calling _enhanced_stock_data_to_dict...")
        converted = PMCCScanner._enhanced_stock_data_to_dict(mock_scanner, enhanced_data)
        print(f"✅ Conversion successful!")
        
        # Save converted data
        with open("data/test_enhanced_data_converted.json", 'w') as f:
            json.dump(converted, f, indent=2, default=str)
        
        # Check specific fields
        print("\n3️⃣ Checking converted data structure:")
        if 'quote' in converted:
            print(f"   Quote: {converted['quote']}")
        if 'fundamentals' in converted:
            print(f"   Fundamentals type: {type(converted['fundamentals'])}")
            if isinstance(converted['fundamentals'], dict):
                print(f"   Fundamentals keys: {list(converted['fundamentals'].keys())[:5]}...")
        if 'technical_indicators' in converted:
            print(f"   Technical indicators: {converted['technical_indicators']}")
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to find the exact location
        print("\n🔍 Debugging the error location...")
        print(f"Enhanced data keys: {list(enhanced_data.keys())}")
        
        # Check each data type
        for key, value in enhanced_data.items():
            print(f"\n   {key}:")
            print(f"     Type: {type(value)}")
            if value is None:
                print(f"     Value: None")
            elif isinstance(value, str):
                print(f"     String value: '{value[:100]}...'")
            elif isinstance(value, list) and len(value) > 0:
                print(f"     List length: {len(value)}")
                print(f"     First item type: {type(value[0])}")
            elif isinstance(value, dict):
                print(f"     Dict keys: {list(value.keys())[:5]}...")
            elif hasattr(value, '__dict__'):
                print(f"     Object attributes: {list(vars(value).keys())[:5]}...")
        
        return False
    
    return True

if __name__ == "__main__":
    success = test_scanner_conversion()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")