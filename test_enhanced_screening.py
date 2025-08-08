#!/usr/bin/env python3
"""Test the enhanced EODHD provider's market cap range splitting."""

import asyncio
import logging
from decimal import Decimal

from src.config.settings import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType, ScreeningCriteria

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_enhanced_screening():
    """Test EODHD screening with market cap range splitting."""
    try:
        # Get settings
        settings = get_settings()
        
        # Create provider
        config = {
            'api_token': settings.eodhd.api_token,
            'base_url': settings.eodhd.base_url,
            'timeout': settings.eodhd.timeout_seconds
        }
        
        provider = EnhancedEODHDProvider(ProviderType.EODHD, config)
        
        # Create screening criteria
        criteria = ScreeningCriteria(
            min_market_cap=Decimal('50000000'),    # $50M
            max_market_cap=Decimal('5000000000'),  # $5B
            min_volume=100000,
            exchanges=['NYSE', 'NASDAQ'],
            limit=5000  # Request 5000 stocks
        )
        
        logger.info(f"Testing enhanced EODHD screening with criteria: {criteria}")
        logger.info("This should use market cap range splitting to bypass API limits...")
        
        # Test screening
        response = await provider.screen_stocks(criteria)
        
        if response.is_success and response.data:
            total_stocks = len(response.data.results)
            logger.info(f"\n✅ SUCCESS: Retrieved {total_stocks} stocks!")
            
            # Show sample results
            if total_stocks > 0:
                logger.info("\nTop 10 stocks by market cap:")
                for i, stock in enumerate(response.data.results[:10]):
                    market_cap_b = float(stock.market_capitalization or 0) / 1000000000
                    logger.info(f"  {i+1}. {stock.code}: ${market_cap_b:.2f}B - {stock.name}")
                
                logger.info(f"\nTotal stocks retrieved: {total_stocks}")
                
                # Show distribution by market cap ranges
                ranges = {
                    '$4B-$5B': 0,
                    '$3B-$4B': 0,
                    '$2B-$3B': 0,
                    '$1B-$2B': 0,
                    '$500M-$1B': 0,
                    '$250M-$500M': 0,
                    '$100M-$250M': 0,
                    '$50M-$100M': 0
                }
                
                for stock in response.data.results:
                    market_cap = float(stock.market_capitalization or 0)
                    if market_cap >= 4000000000:
                        ranges['$4B-$5B'] += 1
                    elif market_cap >= 3000000000:
                        ranges['$3B-$4B'] += 1
                    elif market_cap >= 2000000000:
                        ranges['$2B-$3B'] += 1
                    elif market_cap >= 1000000000:
                        ranges['$1B-$2B'] += 1
                    elif market_cap >= 500000000:
                        ranges['$500M-$1B'] += 1
                    elif market_cap >= 250000000:
                        ranges['$250M-$500M'] += 1
                    elif market_cap >= 100000000:
                        ranges['$100M-$250M'] += 1
                    else:
                        ranges['$50M-$100M'] += 1
                
                logger.info("\nStock distribution by market cap range:")
                for range_name, count in ranges.items():
                    if count > 0:
                        logger.info(f"  {range_name}: {count} stocks")
            
        else:
            logger.error(f"❌ FAILED: {response.error}")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(test_enhanced_screening())