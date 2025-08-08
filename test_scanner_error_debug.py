#!/usr/bin/env python3
"""Debug the exact location of the str.get() error."""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner
import logging

# Enable super detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s:%(lineno)d - %(message)s')

def test_with_monkey_patch():
    """Test with monkey-patched str to find where .get() is called."""
    
    # Monkey patch str to catch .get() calls
    original_getattr = str.__getattribute__
    
    def debug_getattr(self, name):
        if name == 'get':
            print(f"\n🚨 FOUND IT! str.get() called on value: '{self[:50]}...'")
            traceback.print_stack()
            raise AttributeError(f"'str' object has no attribute 'get' - value was: '{self[:50]}...'")
        return original_getattr(self, name)
    
    str.__getattribute__ = debug_getattr
    
    try:
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
        print(f"Got enhanced data")
        
        # Create a mock scanner
        class MockScanner:
            def __init__(self):
                self.logger = logging.getLogger(__name__)
        
        mock_scanner = MockScanner()
        
        # Call the conversion method
        print("Calling _enhanced_stock_data_to_dict...")
        converted = PMCCScanner._enhanced_stock_data_to_dict(mock_scanner, enhanced_data)
        print("Conversion successful!")
        
    finally:
        # Restore original
        str.__getattribute__ = original_getattr

if __name__ == "__main__":
    test_with_monkey_patch()