#!/usr/bin/env python3
"""Test conversion line by line."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Monkey patch the dict.get method to catch string issues
original_get = dict.get

def debug_get(self, key, default=None):
    # Check if self is actually a dict
    if not isinstance(self, dict):
        print(f"🚨 ERROR: get() called on non-dict: {type(self)}")
        raise TypeError(f"get() called on {type(self)} instead of dict")
    return original_get(self, key, default)

dict.get = debug_get

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner
import logging

logging.basicConfig(level=logging.ERROR)

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
    
    # Create a test scanner
    class TestScanner:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
    
    test_scanner = TestScanner()
    
    # Test conversion
    print("\nTesting conversion...")
    try:
        result = PMCCScanner._enhanced_stock_data_to_dict(test_scanner, enhanced_data)
        print("✅ Conversion successful!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Restore original
dict.get = original_get

if __name__ == "__main__":
    test()