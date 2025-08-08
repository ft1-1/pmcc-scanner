#!/usr/bin/env python3
"""Test enhanced data structure to debug the 'str' object issue."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType

def main():
    """Test enhanced data collection for KSS."""
    try:
        # Get settings
        settings = get_settings()
        
        # Create enhanced EODHD provider
        provider_config = {
            'api_token': settings.eodhd_api_token,
            'enable_caching': True,
            'cache_ttl_hours': 1
        }
        
        enhanced_provider = SyncEnhancedEODHDProvider(
            provider_type=ProviderType.EODHD,
            config=provider_config
        )
        
        print("🧪 Testing comprehensive enhanced data for KSS...")
        
        response = enhanced_provider.get_comprehensive_enhanced_data("KSS")
        
        if not response.is_success:
            print(f"❌ Failed to get data: {response.error}")
            return False
        
        enhanced_data = response.data
        
        # Save raw data for inspection
        output_file = "data/kss_enhanced_data_structure.json"
        Path("data").mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(enhanced_data, f, indent=2, default=str)
        print(f"💾 Raw data saved to {output_file}")
        
        # Analyze technical indicators structure
        if 'technical_indicators' in enhanced_data:
            tech_data = enhanced_data['technical_indicators']
            print(f"\n📊 Technical Indicators Analysis:")
            print(f"  Type: {type(tech_data)}")
            
            if isinstance(tech_data, dict):
                for indicator_name, indicator_data in tech_data.items():
                    print(f"\n  {indicator_name}:")
                    print(f"    Type: {type(indicator_data)}")
                    
                    if indicator_data is None:
                        print(f"    Value: None")
                    elif isinstance(indicator_data, str):
                        print(f"    String value: '{indicator_data[:100]}{'...' if len(indicator_data) > 100 else ''}'")
                    elif isinstance(indicator_data, list):
                        print(f"    List length: {len(indicator_data)}")
                        if len(indicator_data) > 0:
                            first = indicator_data[0]
                            print(f"    First item type: {type(first)}")
                            if isinstance(first, dict):
                                print(f"    First item keys: {list(first.keys())}")
                                # Show the actual values
                                for key, value in first.items():
                                    print(f"      {key}: {value} ({type(value).__name__})")
                            else:
                                print(f"    First item value: {first}")
                    elif isinstance(indicator_data, dict):
                        print(f"    Dictionary keys: {list(indicator_data.keys())}")
                        # Show the actual values
                        for key, value in indicator_data.items():
                            print(f"      {key}: {value} ({type(value).__name__})")
                    else:
                        print(f"    Other type: {indicator_data}")
        
        # Now test what happens in the scanner conversion
        print(f"\n🔄 Testing scanner conversion...")
        from src.analysis.scanner import PMCCScanner
        
        class TempScanner:
            def __init__(self):
                import logging
                self.logger = logging.getLogger(__name__)
        
        temp_scanner = TempScanner()
        conversion_method = PMCCScanner._enhanced_stock_data_to_dict
        
        try:
            converted_data = conversion_method(temp_scanner, enhanced_data)
            print(f"✅ Conversion successful!")
            
            # Check converted technical indicators
            if 'technical_indicators' in converted_data:
                print(f"\n📈 Converted technical indicators:")
                for key, value in converted_data['technical_indicators'].items():
                    print(f"  {key}: {value} ({type(value).__name__})")
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()