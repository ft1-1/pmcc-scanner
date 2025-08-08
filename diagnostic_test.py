#\!/usr/bin/env python3
"""
Diagnostic test to identify provider factory issues
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traceback
from src.config import get_settings
from src.api.provider_factory import DataProviderFactory

print("="*60)
print("PMCC SCANNER DIAGNOSTIC TEST")
print("="*60)

print("\n1. Configuration Check:")
try:
    settings = get_settings()
    print(f"✓ Settings loaded: {type(settings)}")
    print(f"✓ EODHD configured: {bool(settings.eodhd and settings.eodhd.api_token)}")
    print(f"✓ Claude configured: {bool(settings.claude and settings.claude.api_key)}")
    print(f"✓ MarketData configured: {bool(settings.marketdata and settings.marketdata.api_token)}")
except Exception as e:
    print(f"✗ Configuration error: {e}")
    traceback.print_exc()

print("\n2. Provider Factory Initialization:")
try:
    factory = DataProviderFactory()
    print(f"✓ Factory created: {type(factory)}")
    
    # Check internal state
    if hasattr(factory, '_providers'):
        print(f"✓ Internal providers dict: {len(factory._providers)} providers")
        for name, provider in factory._providers.items():
            print(f"  - {name}: {type(provider)}")
    else:
        print("✗ No _providers attribute found")
    
    # Check provider status
    status = factory.get_provider_status()
    print(f"✓ Status method works: {status}")
    
except Exception as e:
    print(f"✗ Factory error: {e}")
    traceback.print_exc()

print("\n3. Direct Provider Import Test:")
try:
    from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
    from src.api.providers.claude_provider import ClaudeProvider
    print("✓ Provider classes can be imported")
except ImportError as e:
    print(f"✗ Provider import error: {e}")

print("\n4. Provider Instantiation Test:")
try:
    from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
    from src.api.data_provider import ProviderType
    
    settings = get_settings()
    if settings.eodhd and settings.eodhd.api_token:
        config = {'api_token': settings.eodhd.api_token}
        provider = EnhancedEODHDProvider(ProviderType.ENHANCED_EODHD, config)
        print("✓ EODHD provider can be instantiated")
    else:
        print("✗ EODHD config missing")
        
except Exception as e:
    print(f"✗ Direct provider instantiation error: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
