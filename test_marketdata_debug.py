#!/usr/bin/env python3
"""Debug MarketData.app option chain issue."""

import os
import sys
import logging
from src.config import get_settings
from src.api.provider_factory import SyncDataProviderFactory
from src.api.provider_factory import ProviderType

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

def test_marketdata_provider():
    """Test MarketData.app provider configuration and option chain support."""
    print("=== MarketData.app Provider Debug ===\n")
    
    # Get settings
    settings = get_settings()
    print(f"MarketData API Token present: {bool(settings.marketdata.api_token)}")
    print(f"Preferred options provider: {settings.providers.preferred_options_provider}")
    
    # Create factory with provider configuration
    from src.config.provider_config import ProviderConfigurationManager
    from src.api.provider_factory import FallbackStrategy
    
    # Create configuration manager
    config_manager = ProviderConfigurationManager(settings)
    provider_configs = config_manager.get_provider_configs()
    
    print(f"Found {len(provider_configs)} provider configurations")
    
    # Create factory
    factory = SyncDataProviderFactory(fallback_strategy=FallbackStrategy.OPERATION_SPECIFIC)
    
    # Register providers
    for config in provider_configs:
        factory.register_provider(config)
        print(f"Registered provider: {config.provider_type}")
    
    # Check available providers
    available = factory.list_available_providers()
    print(f"\nAvailable providers: {available}")
    
    # Check provider configs
    print("\nProvider configurations:")
    print(f"Provider configs count: {len(factory.provider_configs)}")
    for provider_type, config in factory.provider_configs.items():
        print(f"\n{provider_type}:")
        print(f"  Supported operations: {config.supported_operations}")
        print(f"  Has 'get_options_chain': {'get_options_chain' in config.supported_operations}")
    
    # Check if factory was initialized
    print(f"\nFactory providers count: {len(factory.providers)}")
    print(f"Factory circuit breakers: {len(factory.circuit_breakers)}")
    
    # Try to get provider for options chain
    print("\n\nTrying to get provider for 'get_options_chain'...")
    
    # First check if MarketData provider can be created
    print("\nChecking MarketData provider creation...")
    marketdata_provider = factory._get_or_create_provider(ProviderType.MARKETDATA)
    if marketdata_provider:
        print(f"MarketData provider created: {marketdata_provider.__class__.__name__}")
    else:
        print("Failed to create MarketData provider!")
    
    provider = factory.get_provider(
        "get_options_chain",
        preferred_provider=ProviderType.MARKETDATA
    )
    
    if provider:
        print(f"Success! Got provider: {provider.__class__.__name__}")
    else:
        print("Failed to get provider!")
    
    # Test the provider directly
    if provider:
        print("\nTesting option chain retrieval for AAPL...")
        try:
            response = provider.get_options_chain("AAPL")
            if response.is_success:
                print("✅ Option chain retrieved successfully!")
                if response.data:
                    print(f"   Got {len(response.data.contracts)} contracts")
            else:
                print(f"❌ Failed: {response.error}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_marketdata_provider()