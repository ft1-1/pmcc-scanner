#!/usr/bin/env python3
"""
Test script for EODHD Screener functionality.

This script demonstrates how to use the EODHD API to screen stocks
by market capitalization for the PMCC Scanner.
"""

import asyncio
import logging
import os
import sys
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.eodhd_client import EODHDClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run EODHD screener tests."""
    logger.info("Starting EODHD Screener Test")
    logger.info("=" * 60)
    
    async with EODHDClient() as client:
        # Test 1: Health check
        logger.info("\nTest 1: API Health Check")
        health = await client.health_check()
        logger.info(f"API Status: {'✓ Connected' if health else '✗ Failed'}")
        
        if not health:
            logger.error("Cannot proceed without API connection")
            return
        
        # Test 2: PMCC Universe ($50M - $5B)
        logger.info("\nTest 2: PMCC Universe Screening ($50M - $5B)")
        response = await client.screen_by_market_cap(
            min_market_cap=50_000_000,      # $50M
            max_market_cap=5_000_000_000,   # $5B
            limit=100
        )
        
        if response.is_success:
            results = response.data.results
            logger.info(f"Found {len(results)} stocks in PMCC range")
            
            # Group by market cap
            ranges = {
                "$50M-$500M": [s for s in results if s.market_capitalization < 500_000_000],
                "$500M-$1B": [s for s in results if 500_000_000 <= s.market_capitalization < 1_000_000_000],
                "$1B-$5B": [s for s in results if s.market_capitalization >= 1_000_000_000]
            }
            
            logger.info("\nDistribution by market cap:")
            for range_name, stocks in ranges.items():
                logger.info(f"  {range_name}: {len(stocks)} stocks")
            
            # Show examples
            logger.info("\nExample stocks from each range:")
            for range_name, stocks in ranges.items():
                if stocks:
                    logger.info(f"\n{range_name}:")
                    for stock in stocks[:3]:
                        cap_str = f"${stock.market_cap_billions:.2f}B" if stock.market_capitalization >= 1_000_000_000 else f"${stock.market_cap_millions:.1f}M"
                        logger.info(f"  {stock.code:<6} {cap_str:>8} - {stock.name[:40]}")
        else:
            logger.error(f"Screening failed: {response.error}")
        
        # Test 3: Get symbols for further processing
        logger.info("\nTest 3: Get Symbol List")
        symbols = await client.get_pmcc_universe(limit=20)
        logger.info(f"Retrieved {len(symbols)} symbols")
        logger.info(f"Symbols: {', '.join(symbols)}")
        
        # Show API usage stats
        logger.info("\nAPI Usage Statistics:")
        stats = client.get_stats()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
    
    logger.info("\n" + "=" * 60)
    logger.info("EODHD Screener Test Completed")


if __name__ == "__main__":
    asyncio.run(main())