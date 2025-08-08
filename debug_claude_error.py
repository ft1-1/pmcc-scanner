#!/usr/bin/env python3
"""Debug Claude analysis error"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.api.provider_factory import SyncDataProviderFactory
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.analysis.scanner import PMCCScanner

def test_enhanced_data_conversion():
    """Test the _enhanced_stock_data_to_dict method"""
    print("Testing enhanced data conversion...")
    
    try:
        # Create scanner instance
        settings = get_settings()
        factory = SyncDataProviderFactory()
        scanner = PMCCScanner(provider_factory=factory)
        
        # Get enhanced EODHD provider
        eodhd_provider = factory.get_provider("get_fundamental_data", preferred_provider="EODHD")
        if eodhd_provider and hasattr(eodhd_provider, 'config'):
            sync_provider = SyncEnhancedEODHDProvider(
                provider_type="EODHD",
                config=eodhd_provider.config
            )
            
            # Get comprehensive data
            print("\nFetching comprehensive data for KSS...")
            response = sync_provider.get_comprehensive_enhanced_data('KSS')
            
            if response.is_success and response.data:
                print(f"Data type: {type(response.data)}")
                print(f"Data keys: {list(response.data.keys()) if isinstance(response.data, dict) else 'Not a dict'}")
                
                # Test the conversion method
                print("\nTesting _enhanced_stock_data_to_dict...")
                try:
                    converted_data = scanner._enhanced_stock_data_to_dict(response.data)
                    print(f"Conversion successful!")
                    print(f"Converted data keys: {list(converted_data.keys())}")
                    
                    # Save for inspection
                    with open('data/debug_converted_data.json', 'w') as f:
                        json.dump(converted_data, f, indent=2, default=str)
                    print("Saved converted data to data/debug_converted_data.json")
                    
                except Exception as e:
                    print(f"Conversion error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"Failed to get comprehensive data: {response.error}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_data_conversion()