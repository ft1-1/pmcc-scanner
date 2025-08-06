#!/usr/bin/env python3
"""
MarketData.app API Client Demo

This script demonstrates how to use the MarketData API client to:
1. Fetch stock quotes
2. Retrieve option chains  
3. Find PMCC candidate positions
4. Handle rate limiting and errors

Before running:
1. Set your API token in .env file or environment variable
2. Install dependencies: pip install -r requirements.txt

Usage:
    python examples/api_client_demo.py
"""

import asyncio
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api import MarketDataClient, MarketDataError
from models.api_models import OptionSide


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_stock_quotes(client: MarketDataClient):
    """Demonstrate stock quote functionality."""
    logger.info("=== Stock Quotes Demo ===")
    
    # Get single stock quote
    logger.info("Fetching AAPL stock quote...")
    response = await client.get_stock_quote('AAPL')
    
    if response.is_success:
        quote = response.data
        logger.info(f"AAPL Quote:")
        logger.info(f"  Last: ${quote.last}")
        logger.info(f"  Bid: ${quote.bid} x {quote.bid_size}")
        logger.info(f"  Ask: ${quote.ask} x {quote.ask_size}")
        logger.info(f"  Volume: {quote.volume:,}")
        logger.info(f"  Spread: ${quote.spread} ({quote.spread_percentage:.2f}%)")
    else:
        logger.error(f"Failed to get AAPL quote: {response.error}")
    
    # Get multiple stock quotes
    logger.info("\nFetching multiple stock quotes...")
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
    responses = await client.get_stock_quotes(symbols)
    
    logger.info("Stock Quotes Summary:")
    for symbol, response in responses.items():
        if response.is_success:
            quote = response.data
            logger.info(f"  {symbol}: ${quote.last} (Vol: {quote.volume:,})")
        else:
            logger.error(f"  {symbol}: Error - {response.error}")


async def demo_option_chains(client: MarketDataClient):
    """Demonstrate option chain functionality."""
    logger.info("\n=== Option Chains Demo ===")
    
    # Get option expirations first
    logger.info("Fetching AAPL option expirations...")
    response = await client.get_option_expirations('AAPL')
    
    if response.is_success:
        expirations = response.data[:5]  # First 5 expirations
        logger.info(f"Available expirations (first 5): {expirations}")
        
        # Get option chain for first expiration
        if expirations:
            first_expiration = expirations[0]
            logger.info(f"\nFetching option chain for {first_expiration}...")
            
            chain_response = await client.get_option_chain(
                'AAPL',
                expiration=first_expiration,
                strike_limit=20  # Limit strikes to reduce API usage
            )
            
            if chain_response.is_success:
                chain = chain_response.data
                logger.info(f"Option Chain for AAPL:")
                logger.info(f"  Underlying: {chain.underlying} @ ${chain.underlying_price}")
                logger.info(f"  Total contracts: {len(chain.contracts)}")
                
                # Show calls and puts separately
                calls = chain.get_calls()
                puts = chain.get_puts()
                logger.info(f"  Calls: {len(calls)}, Puts: {len(puts)}")
                
                # Show a few example contracts
                logger.info("\nExample Call Contracts:")
                for contract in calls[:3]:
                    logger.info(f"  {contract.option_symbol}: "
                              f"Strike ${contract.strike}, "
                              f"Bid ${contract.bid}, Ask ${contract.ask}, "
                              f"Delta {contract.delta}")
                
            else:
                logger.error(f"Failed to get option chain: {chain_response.error}")
    else:
        logger.error(f"Failed to get expirations: {response.error}")


async def demo_pmcc_scanning(client: MarketDataClient):
    """Demonstrate PMCC candidate scanning."""
    logger.info("\n=== PMCC Scanning Demo ===")
    
    symbol = 'AAPL'
    logger.info(f"Scanning {symbol} for PMCC opportunities...")
    
    # Get full option chain
    response = await client.get_option_chain(symbol)
    
    if not response.is_success:
        logger.error(f"Failed to get option chain: {response.error}")
        return
    
    chain = response.data
    logger.info(f"Analyzing {len(chain.contracts)} contracts...")
    
    # Find LEAPS calls (potential long leg)
    leaps_calls = chain.get_leaps_calls(min_delta=Decimal('0.70'))
    logger.info(f"Found {len(leaps_calls)} LEAPS calls with delta >= 0.70")
    
    # Find short-term calls (potential short leg)
    short_calls = chain.get_short_calls(
        min_dte=21, max_dte=45,
        min_delta=Decimal('0.20'), max_delta=Decimal('0.35')
    )
    logger.info(f"Found {len(short_calls)} short calls (21-45 DTE, delta 0.20-0.35)")
    
    # Find valid PMCC combinations
    pmcc_candidates = []
    
    for leaps_call in leaps_calls[:5]:  # Limit to first 5 LEAPS
        for short_call in short_calls:
            # PMCC rules: short strike > long strike
            if short_call.strike > leaps_call.strike:
                # Calculate net debit (cost)
                if leaps_call.ask and short_call.bid:
                    net_debit = leaps_call.ask - short_call.bid
                    
                    # Only consider if net debit is reasonable
                    if net_debit > 0 and net_debit < leaps_call.strike * Decimal('0.3'):
                        pmcc_candidates.append({
                            'long_call': leaps_call,
                            'short_call': short_call,
                            'net_debit': net_debit,
                            'strike_width': short_call.strike - leaps_call.strike,
                            'max_profit': short_call.strike - leaps_call.strike - net_debit
                        })
    
    # Sort by max profit
    pmcc_candidates.sort(key=lambda x: x['max_profit'], reverse=True)
    
    logger.info(f"\nFound {len(pmcc_candidates)} potential PMCC positions:")
    
    for i, candidate in enumerate(pmcc_candidates[:3]):  # Show top 3
        long_call = candidate['long_call']
        short_call = candidate['short_call']
        
        logger.info(f"\nPMCC Candidate #{i+1}:")
        logger.info(f"  Long Call:  {long_call.option_symbol}")
        logger.info(f"    Strike: ${long_call.strike}, DTE: {long_call.dte}, Delta: {long_call.delta}")
        logger.info(f"    Ask: ${long_call.ask}")
        logger.info(f"  Short Call: {short_call.option_symbol}")
        logger.info(f"    Strike: ${short_call.strike}, DTE: {short_call.dte}, Delta: {short_call.delta}")
        logger.info(f"    Bid: ${short_call.bid}")
        logger.info(f"  Net Debit: ${candidate['net_debit']:.2f}")
        logger.info(f"  Max Profit: ${candidate['max_profit']:.2f}")
        logger.info(f"  Strike Width: ${candidate['strike_width']}")


async def demo_error_handling(client: MarketDataClient):
    """Demonstrate error handling."""
    logger.info("\n=== Error Handling Demo ===")
    
    # Try to get quote for invalid symbol
    logger.info("Attempting to fetch quote for invalid symbol 'INVALID'...")
    response = await client.get_stock_quote('INVALID')
    
    if not response.is_success:
        logger.info(f"Expected error received: {response.error}")
    else:
        logger.info("Unexpected success - API might accept any symbol")
    
    # Check rate limiting status
    stats = client.get_stats()
    logger.info(f"\nClient Statistics:")
    logger.info(f"  Requests made: {stats['requests_made']}")
    logger.info(f"  Requests failed: {stats['requests_failed']}")
    logger.info(f"  Rate limit hits: {stats['rate_limit_hits']}")
    logger.info(f"  Daily usage: {stats['daily_usage']}/{stats.get('daily_limit', 'unlimited')}")
    logger.info(f"  Active requests: {stats['active_requests']}/{stats['concurrent_limit']}")


async def main():
    """Main demo function."""
    logger.info("MarketData.app API Client Demo")
    logger.info("=" * 50)
    
    # Check for API token
    api_token = os.getenv('MARKETDATA_API_TOKEN')
    if not api_token:
        logger.warning("No API token found. Some features may not work.")
        logger.info("Set MARKETDATA_API_TOKEN environment variable or add to .env file")
    
    # Create client
    async with MarketDataClient(plan_type='free') as client:
        # Test API connection
        logger.info("Testing API connection...")
        is_healthy = await client.health_check()
        
        if not is_healthy:
            logger.error("API health check failed. Check your connection and token.")
            return
        
        logger.info("API connection successful!")
        
        try:
            # Run demos
            await demo_stock_quotes(client)
            await demo_option_chains(client)
            await demo_pmcc_scanning(client)
            await demo_error_handling(client)
            
        except MarketDataError as e:
            logger.error(f"MarketData API error: {e}")
            if hasattr(e, 'retry_after') and e.retry_after:
                logger.info(f"Suggested retry after: {e.retry_after:.1f} seconds")
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        
        finally:
            # Final stats
            stats = client.get_stats()
            logger.info(f"\nFinal Statistics:")
            logger.info(f"  Total requests: {stats['requests_made']}")
            logger.info(f"  Failed requests: {stats['requests_failed']}")
            logger.info(f"  API credits used: {stats['daily_usage']}")


if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    from pathlib import Path
    env_file = Path(__file__).parent.parent / '.env'
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # Run the demo
    asyncio.run(main())