#!/usr/bin/env python3
"""Test our enhanced EODHD provider implementation."""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.api.data_provider import ProviderType

async def test_enhanced_provider():
    """Test our enhanced provider implementation."""
    print("🔍 Testing Our Enhanced EODHD Provider Implementation")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    
    # Create provider config
    provider_config = {
        'api_token': settings.eodhd_api_token,
        'enable_caching': False,  # Disable caching for testing
        'cache_ttl_hours': 0
    }
    
    # Create async provider
    provider = EnhancedEODHDProvider(
        provider_type=ProviderType.EODHD,
        config=provider_config
    )
    
    ticker = 'KSS'
    errors = []
    
    print(f"\n📊 Testing API calls for {ticker}")
    print("-" * 60)
    
    # 1. Test Fundamental Data
    print("\n1️⃣ Testing Fundamental Data")
    try:
        response = await provider.get_fundamental_data(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__}")
            if hasattr(data, '__dict__'):
                print(f"   Attributes: {list(vars(data).keys())[:5]}...")
            elif isinstance(data, dict):
                print(f"   Keys: {list(data.keys())[:5]}...")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Fundamental data: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Fundamental data exception: {e}")
    
    # 2. Test Live Price
    print("\n2️⃣ Testing Live Price")
    try:
        response = await provider.get_live_price(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__}")
            print(f"   Data: {data}")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Live price: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Live price exception: {e}")
    
    # 3. Test Economic Events
    print("\n3️⃣ Testing Economic Events")
    try:
        response = await provider.get_economic_events()
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__} with {len(data) if isinstance(data, list) else 'N/A'} items")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Economic events: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Economic events exception: {e}")
    
    # 4. Test Company News
    print("\n4️⃣ Testing Company News")
    try:
        response = await provider.get_company_news(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__} with {len(data) if isinstance(data, list) else 'N/A'} items")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Company news: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Company news exception: {e}")
    
    # 5. Test Technical Indicators
    print("\n5️⃣ Testing Technical Indicators")
    try:
        response = await provider.get_technical_indicators_comprehensive(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__}")
            if isinstance(data, dict):
                for indicator, values in data.items():
                    if values is None:
                        print(f"   {indicator}: None")
                    elif isinstance(values, list):
                        print(f"   {indicator}: {len(values)} data points")
                    else:
                        print(f"   {indicator}: {type(values).__name__}")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Technical indicators: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Technical indicators exception: {e}")
    
    # 6. Test Comprehensive Enhanced Data
    print("\n6️⃣ Testing Comprehensive Enhanced Data")
    try:
        response = await provider.get_comprehensive_enhanced_data(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__}")
            if isinstance(data, dict):
                print("   Available data categories:")
                for key, value in data.items():
                    if value is None:
                        print(f"     {key}: None")
                    elif isinstance(value, list):
                        print(f"     {key}: {len(value)} items")
                    elif isinstance(value, dict):
                        print(f"     {key}: {len(value)} fields")
                    else:
                        print(f"     {key}: {type(value).__name__}")
        else:
            print(f"❌ Failed: {response.error}")
            errors.append(f"Comprehensive data: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        errors.append(f"Comprehensive data exception: {e}")
    
    # Close provider
    await provider.close()
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    if errors:
        print(f"❌ Found {len(errors)} errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ All API calls successful!")
    
    return len(errors) == 0

# Test sync provider wrapper
def test_sync_provider():
    """Test sync provider wrapper."""
    print("\n\n🔍 Testing Sync Enhanced EODHD Provider Wrapper")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    
    # Create provider config
    provider_config = {
        'api_token': settings.eodhd_api_token,
        'enable_caching': False,
        'cache_ttl_hours': 0
    }
    
    # Create sync provider
    sync_provider = SyncEnhancedEODHDProvider(
        provider_type=ProviderType.EODHD,
        config=provider_config
    )
    
    ticker = 'KSS'
    
    print(f"\n📊 Testing Comprehensive Enhanced Data via Sync Wrapper for {ticker}")
    print("-" * 60)
    
    try:
        response = sync_provider.get_comprehensive_enhanced_data(ticker)
        if response.is_success:
            data = response.data
            print(f"✅ Success: {type(data).__name__}")
            
            # Save data for inspection
            output_file = "data/our_enhanced_provider_test.json"
            Path("data").mkdir(exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Data saved to {output_file}")
            
            # Check specific issues
            if isinstance(data, dict):
                # Check live price
                if 'live_price' in data:
                    live_price = data['live_price']
                    print(f"\n🔍 Live Price Check:")
                    print(f"   Type: {type(live_price).__name__}")
                    if isinstance(live_price, dict):
                        code = live_price.get('code', 'N/A')
                        print(f"   Code: {code}")
                        if code and not code.startswith(ticker):
                            print(f"   ⚠️ WARNING: Code doesn't match ticker!")
                
                # Check technical indicators
                if 'technical_indicators' in data:
                    tech = data['technical_indicators']
                    print(f"\n🔍 Technical Indicators Check:")
                    print(f"   Type: {type(tech).__name__}")
                    if isinstance(tech, dict):
                        for ind, val in tech.items():
                            if val is None:
                                print(f"   ⚠️ {ind}: None")
                            elif isinstance(val, str):
                                print(f"   ⚠️ {ind}: String value!")
                            else:
                                print(f"   ✅ {ind}: OK")
        else:
            print(f"❌ Failed: {response.error}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return True

if __name__ == "__main__":
    # Run async test
    success = asyncio.run(test_enhanced_provider())
    
    # Run sync test
    test_sync_provider()
    
    print("\n✅ Testing complete!")