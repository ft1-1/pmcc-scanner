#!/usr/bin/env python3
"""Test stock screening functionality."""

import logging
from src.config import get_settings
from src.api.provider_factory import SyncDataProviderFactory

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_screening():
    """Test the stock screening process."""
    settings = get_settings()
    factory = SyncDataProviderFactory()
    
    # Check provider status
    print('Provider Status:')
    status = factory.get_provider_status()
    for provider, info in status.items():
        print(f"  {provider}: {info}")
    
    # Try screening stocks
    print('\nTrying to screen stocks...')
    screener_provider = factory.get_provider_for_operation('screen_stocks')
    print(f'Screener provider: {screener_provider}')
    
    if screener_provider:
        try:
            stocks = screener_provider.screen_stocks()
            print(f'Found {len(stocks)} stocks')
            if stocks:
                print(f'First 5 stocks: {stocks[:5]}')
        except Exception as e:
            print(f'Error screening stocks: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('No provider available for screening')
    
    # Check if KSS is being used for testing
    print(f'\nTest mode enabled: {settings.test_mode}')
    print(f'Test symbols: {settings.test_symbols}')

if __name__ == "__main__":
    test_screening()