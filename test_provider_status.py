#!/usr/bin/env python3
"""
Test script to check provider availability and status.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.settings import get_settings
from src.api.provider_factory import SyncDataProviderFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """Check provider availability."""
    logger.info("=== PMCC Scanner Provider Status ===")
    
    try:
        # Initialize settings and factory
        settings = get_settings()
        factory = SyncDataProviderFactory(settings)
        
        logger.info(f"Settings loaded: {settings.environment}")
        logger.info(f"Factory initialized successfully")
        
        # Test each provider type
        provider_types = ['eodhd', 'enhanced_eodhd', 'marketdata', 'claude']
        
        for provider_type in provider_types:
            try:
                provider = factory.get_provider(provider_type)
                if provider:
                    logger.info(f"✓ {provider_type}: Available")
                    logger.info(f"  Type: {type(provider).__name__}")
                else:
                    logger.info(f"✗ {provider_type}: Not available")
            except Exception as e:
                logger.info(f"✗ {provider_type}: Error - {e}")
        
        # Check configuration
        logger.info("\n=== Configuration Status ===")
        logger.info(f"EODHD API Token: {'✓ Set' if settings.eodhd_api_token else '✗ Missing'}")
        logger.info(f"MarketData API Token: {'✓ Set' if settings.api_token else '✗ Missing'}")
        logger.info(f"Claude API Key: {'✓ Set' if settings.claude and settings.claude.api_key else '✗ Missing'}")
        
        # Show available providers
        available = settings.get_available_providers()
        logger.info(f"Available providers: {available}")
        
        # Show specific provider configs
        logger.info(f"EODHD configured: {settings.eodhd is not None and settings.eodhd.is_configured if settings.eodhd else False}")
        logger.info(f"MarketData configured: {settings.marketdata is not None and settings.marketdata.is_configured if settings.marketdata else False}")
        logger.info(f"Claude configured: {settings.claude is not None and settings.claude.is_configured if settings.claude else False}")
        
    except Exception as e:
        logger.error(f"Error checking providers: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()