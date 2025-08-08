#!/usr/bin/env python3
"""Test comprehensive enhanced data collection"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.api.provider_factory import DataProviderFactory
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider

async def test_comprehensive_data():
    """Test comprehensive data collection for KSS"""
    print("Testing comprehensive enhanced data collection...")
    
    try:
        # Initialize settings and factory
        settings = get_settings()
        factory = DataProviderFactory()
        
        # Get enhanced EODHD provider
        enhanced_provider = await factory.get_provider('enhanced_eodhd')
        if not enhanced_provider:
            print("Enhanced EODHD provider not available")
            return
            
        print(f"Provider type: {type(enhanced_provider)}")
        
        # Test comprehensive data collection
        print("\nCollecting comprehensive data for KSS...")
        response = await enhanced_provider.get_comprehensive_enhanced_data('KSS')
        
        print(f"Response status: {response.status}")
        print(f"Response is_success: {response.is_success}")
        print(f"Response data type: {type(response.data)}")
        
        if response.is_success and response.data:
            # Save the data for inspection
            output_file = "data/test_comprehensive_kss.json"
            with open(output_file, 'w') as f:
                json.dump(response.data, f, indent=2, default=str)
            print(f"\nData saved to {output_file}")
            
            # Print summary
            print("\nData summary:")
            for key, value in response.data.items():
                if isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
                elif isinstance(value, dict):
                    print(f"  {key}: {len(value)} fields")
                else:
                    print(f"  {key}: {type(value).__name__}")
        else:
            print(f"Failed to get data: {response.error}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_comprehensive_data())