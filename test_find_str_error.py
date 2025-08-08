#!/usr/bin/env python3
"""Find the str.get() error by adding debug prints."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Monkey patch the scanner method to add debug prints
import src.analysis.scanner as scanner_module

# Get the original method
original_method = scanner_module.PMCCScanner._enhanced_stock_data_to_dict

def debug_enhanced_stock_data_to_dict(self, enhanced_data):
    """Wrapped version with debug prints."""
    print("\n🔍 DEBUG: Starting _enhanced_stock_data_to_dict")
    print(f"   Enhanced data type: {type(enhanced_data)}")
    print(f"   Enhanced data keys: {list(enhanced_data.keys()) if isinstance(enhanced_data, dict) else 'Not a dict'}")
    
    # Check each key
    if isinstance(enhanced_data, dict):
        for key, value in enhanced_data.items():
            print(f"\n   Checking key '{key}':")
            print(f"      Type: {type(value)}")
            if isinstance(value, str):
                print(f"      String value: '{value[:50]}...'")
    
    try:
        # Call original method
        return original_method(self, enhanced_data)
    except AttributeError as e:
        if "'str' object has no attribute 'get'" in str(e):
            print(f"\n🚨 ERROR CAUGHT: {e}")
            # Print current processing context
            import traceback
            traceback.print_exc()
        raise

# Replace the method
scanner_module.PMCCScanner._enhanced_stock_data_to_dict = debug_enhanced_stock_data_to_dict

# Now run the test
from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner
import logging

logging.basicConfig(level=logging.WARNING)  # Reduce noise

def test():
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
    
    # Create a mock scanner
    class MockScanner:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
    
    mock_scanner = MockScanner()
    
    # Call the conversion method
    print("\nCalling _enhanced_stock_data_to_dict...")
    try:
        converted = PMCCScanner._enhanced_stock_data_to_dict(mock_scanner, enhanced_data)
        print("✅ Conversion successful!")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")

if __name__ == "__main__":
    test()