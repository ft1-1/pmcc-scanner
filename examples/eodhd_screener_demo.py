#!/usr/bin/env python3
"""
Demo script showing how to use the EODHD Screener API integration.

This example demonstrates:
1. Setting up EODHD client for stock screening
2. Using EODHD to filter stocks by market cap
3. Integrating EODHD with the existing stock screener
4. Hybrid approach: EODHD for initial screening, MarketData for options analysis
"""

import asyncio
import logging
import os
import sys
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.eodhd_client import EODHDClient
from api.sync_marketdata_client import SyncMarketDataClient
from analysis.stock_screener import StockScreener, ScreeningCriteria
from config.settings import load_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_eodhd_basic_screening():
    """Demo basic EODHD screening functionality."""
    logger.info("=== EODHD Basic Screening Demo ===")
    
    # Initialize EODHD client
    eodhd_client = EODHDClient()
    
    try:
        async with eodhd_client:
            # Test health check
            logger.info("Testing EODHD API connection...")
            health = await eodhd_client.health_check()
            logger.info(f"EODHD API Health: {'OK' if health else 'FAILED'}")
            
            if not health:
                logger.error("EODHD API is not accessible. Check your API token.")
                return
            
            # Screen for PMCC-suitable stocks
            logger.info("Screening stocks with market cap $50M - $5B...")
            response = await eodhd_client.screen_by_market_cap(
                min_market_cap=50_000_000,    # $50M
                max_market_cap=5_000_000_000, # $5B
                limit=20
            )
            
            if response.is_success:
                screener_data = response.data
                logger.info(f"Found {len(screener_data.results)} stocks matching criteria")
                
                # Show top 10 results
                for i, result in enumerate(screener_data.results[:10], 1):
                    market_cap_b = result.market_cap_billions or Decimal('0')
                    logger.info(
                        f"{i:2d}. {result.code:6s} - {result.name[:30]:30s} "
                        f"Market Cap: ${market_cap_b:6.1f}B Exchange: {result.exchange}"
                    )
                
                # Get just the symbols for further processing
                symbols = screener_data.get_symbols()
                logger.info(f"Symbol list: {symbols[:10]}{'...' if len(symbols) > 10 else ''}")
                
                return symbols
            else:
                logger.error(f"EODHD screening failed: {response.error}")
                return []
    
    except Exception as e:
        logger.error(f"Error in EODHD demo: {e}")
        return []


async def demo_eodhd_convenience_method():
    """Demo the convenience method for getting PMCC universe."""
    logger.info("=== EODHD Convenience Method Demo ===")
    
    eodhd_client = EODHDClient()
    
    try:
        # Use the convenience method
        symbols = await eodhd_client.get_pmcc_universe(limit=50)
        
        logger.info(f"Retrieved {len(symbols)} symbols for PMCC universe")
        logger.info(f"Symbols: {symbols[:15]}{'...' if len(symbols) > 15 else ''}")
        
        return symbols
    
    except Exception as e:
        logger.error(f"Error in convenience method demo: {e}")
        return []


def demo_hybrid_screening():
    """Demo hybrid screening: EODHD + MarketData integration."""
    logger.info("=== Hybrid Screening Demo ===")
    
    try:
        # Load settings
        settings = load_settings()
        
        # Initialize both clients
        eodhd_client = EODHDClient()
        marketdata_client = SyncMarketDataClient()
        
        # Initialize stock screener with both clients
        screener = StockScreener(
            api_client=marketdata_client,
            eodhd_client=eodhd_client
        )
        
        # Create screening criteria
        criteria = ScreeningCriteria(
            min_market_cap=Decimal('100'),    # $100M minimum
            max_market_cap=Decimal('2000'),   # $2B maximum
            min_price=Decimal('20'),          # $20 minimum price
            max_price=Decimal('200'),         # $200 maximum price
            require_leaps=True,               # Must have LEAPS
            require_weekly_options=True       # Must have weekly options
        )
        
        # Screen using EODHD universe
        logger.info("Screening EODHD universe with PMCC criteria...")
        results = screener.screen_universe(
            universe="EODHD_PMCC",  # This will use EODHD for initial screening
            criteria=criteria,
            max_results=20
        )
        
        logger.info(f"Found {len(results)} stocks meeting all PMCC criteria")
        
        # Display results
        for i, result in enumerate(results[:10], 1):
            price = result.quote.last or result.quote.mid or Decimal('0')
            volume = result.quote.volume or 0
            
            logger.info(
                f"{i:2d}. {result.symbol:6s} - Price: ${price:6.2f} "
                f"Volume: {volume:>8,} Score: {result.screening_score or 0:5.1f}"
            )
        
        return results
    
    except Exception as e:
        logger.error(f"Error in hybrid screening demo: {e}")
        return []


def demo_traditional_screening():
    """Demo traditional screening without EODHD for comparison."""
    logger.info("=== Traditional Screening Demo (for comparison) ===")
    
    try:
        # Initialize MarketData client only
        marketdata_client = SyncMarketDataClient()
        screener = StockScreener(api_client=marketdata_client)
        
        # Screen using predefined universe
        results = screener.screen_universe(
            universe="SP500",  # Predefined universe
            max_results=10
        )
        
        logger.info(f"Traditional screening found {len(results)} results")
        
        for i, result in enumerate(results[:5], 1):
            price = result.quote.last or result.quote.mid or Decimal('0')
            logger.info(f"{i}. {result.symbol} - ${price:.2f}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in traditional screening demo: {e}")
        return []


async def main():
    """Run all demos."""
    logger.info("Starting EODHD Screener Integration Demo")
    logger.info("=" * 50)
    
    # Check environment variables
    if not os.getenv('EODHD_API_TOKEN'):
        logger.error(
            "EODHD_API_TOKEN environment variable not set. "
            "Please set it to run the EODHD demos."
        )
        logger.info("You can still run the traditional screening demo.")
        demo_traditional_screening()
        return
    
    if not os.getenv('MARKETDATA_API_TOKEN'):
        logger.error(
            "MARKETDATA_API_TOKEN environment variable not set. "
            "Please set it to run the full hybrid demo."
        )
    
    try:
        # Run EODHD-only demos
        await demo_eodhd_basic_screening()
        print()
        
        await demo_eodhd_convenience_method()
        print()
        
        # Run hybrid demo if both APIs are available
        if os.getenv('MARKETDATA_API_TOKEN'):
            demo_hybrid_screening()
            print()
        
        # Run traditional demo for comparison
        if os.getenv('MARKETDATA_API_TOKEN'):
            demo_traditional_screening()
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    
    logger.info("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())