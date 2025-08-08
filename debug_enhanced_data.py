#!/usr/bin/env python3
"""Debug enhanced data conversion issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType
import logging
import json

logging.basicConfig(level=logging.ERROR)

def inspect_enhanced_data():
    """Get enhanced data and inspect its structure."""
    
    settings = get_settings()
    
    provider_config = {
        'api_token': settings.eodhd_api_token,
        'enable_caching': False,
        'cache_ttl_hours': 0
    }
    
    enhanced_provider = SyncEnhancedEODHDProvider(
        provider_type=ProviderType.EODHD,
        config=provider_config
    )
    
    print("Getting comprehensive enhanced data for KSS...")
    response = enhanced_provider.get_comprehensive_enhanced_data("KSS")
    
    if not response.is_success:
        print(f"Failed to get data: {response.error}")
        return
    
    enhanced_data = response.data
    print(f"\nEnhanced data type: {type(enhanced_data)}")
    
    # Check each component
    if isinstance(enhanced_data, dict):
        print("\nChecking all data components:")
        for key, value in enhanced_data.items():
            print(f"\n{key}:")
            print(f"  Type: {type(value)}")
            
            if value is None:
                print("  Value: None")
            elif isinstance(value, str):
                print(f"  STRING VALUE: '{value[:100]}...'")
            elif isinstance(value, dict):
                print(f"  Keys: {list(value.keys())}")
                # Check for nested strings
                for k, v in value.items():
                    if isinstance(v, str):
                        print(f"    {k}: STRING '{v[:50]}...'")
                    elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
                        print(f"    {k}: LIST OF STRINGS")
            elif isinstance(value, list):
                print(f"  Length: {len(value)}")
                if len(value) > 0:
                    print(f"  First item type: {type(value[0])}")
    
    # Save to file for inspection
    with open('enhanced_data_dump.json', 'w') as f:
        def serialize(obj):
            if hasattr(obj, '__dict__'):
                return {**{'_type': type(obj).__name__}, **obj.__dict__}
            return str(obj)
        
        json.dump(enhanced_data, f, indent=2, default=serialize)
    print("\nSaved full data to enhanced_data_dump.json")

if __name__ == "__main__":
    inspect_enhanced_data()