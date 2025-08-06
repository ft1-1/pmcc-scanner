#!/usr/bin/env python3
"""
Example usage of the new EODHD DataProvider implementations.

This script demonstrates how to use both the async and sync EODHD providers
that implement the DataProvider interface while leveraging EODHD's strengths
in stock screening and comprehensive options data.
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.providers import EODHDProvider, SyncEODHDProvider, create_sync_eodhd_provider
from src.api.data_provider import ProviderType, ScreeningCriteria


async def demo_async_eodhd_provider():
    """Demonstrate the async EODHD provider."""
    print("=== Async EODHD Provider Demo ===")
    
    # Configuration
    config = {
        'api_token': os.getenv('EODHD_API_TOKEN', 'demo'),
        'timeout': 30.0,
        'max_retries': 3,
        'screening_cache_ttl_hours': 24,
        'enable_tradetime_filtering': True,
        'tradetime_lookback_days': 5
    }
    
    # Create provider
    provider = EODHDProvider(ProviderType.EODHD, config)
    
    try:
        # 1. Health Check
        print("\n1. Health Check")
        health = await provider.health_check()
        print(f"   Status: {health.status}")
        print(f"   Latency: {health.latency_ms:.1f}ms" if health.latency_ms else "   Latency: N/A")
        
        # 2. Stock Screening (EODHD's strength)
        print("\n2. Stock Screening - Market Cap $50M-$5B")
        criteria = ScreeningCriteria(
            min_market_cap=Decimal('50000000'),    # $50M
            max_market_cap=Decimal('5000000000'),  # $5B
            min_price=Decimal('5.00'),             # Above $5
            max_price=Decimal('500.00'),           # Below $500
            min_volume=500000,                     # Min daily volume
            exchanges=['NYSE', 'NASDAQ'],
            exclude_penny_stocks=True,
            exclude_etfs=True
        )
        
        # Estimate credits first
        credits = provider.estimate_credits_required('screen_stocks', criteria=criteria)
        print(f"   Estimated credits: {credits}")
        
        # Note: Actual screening would consume credits, so we skip for demo
        print("   (Skipping actual screening to preserve API credits)")
        
        # 3. Stock Quote
        print("\n3. Stock Quote - AAPL")
        quote_response = await provider.get_stock_quote('AAPL')
        if quote_response.is_success:
            quote = quote_response.data
            print(f"   Symbol: {quote.symbol}")
            print(f"   Last: ${quote.last}")
            print(f"   Volume: {quote.volume:,}" if quote.volume else "   Volume: N/A")
            print(f"   Provider: {quote_response.provider_name}")
            print(f"   Latency: {quote_response.response_latency_ms:.1f}ms")
        else:
            print(f"   Error: {quote_response.error}")
        
        # 4. Multiple Stock Quotes
        print("\n4. Multiple Stock Quotes")
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        quotes_response = await provider.get_stock_quotes(symbols)
        if quotes_response.is_success and quotes_response.data:
            print(f"   Retrieved {len(quotes_response.data)} quotes:")
            for quote in quotes_response.data[:3]:  # Show first 3
                print(f"     {quote.symbol}: ${quote.last}")
        
        # 5. Options Chain
        print("\n5. Options Chain - AAPL (limited date range)")
        exp_from = date.today() + timedelta(days=30)
        exp_to = date.today() + timedelta(days=60)
        
        options_response = await provider.get_options_chain('AAPL', exp_from, exp_to)
        if options_response.is_success and options_response.data:
            chain = options_response.data
            print(f"   Underlying: {chain.underlying}")
            print(f"   Underlying Price: ${chain.underlying_price}")
            print(f"   Total Contracts: {len(chain.contracts)}")
            
            # Show some sample contracts
            calls = [c for c in chain.contracts if c.side.value == 'call'][:3]
            if calls:
                print("   Sample Call Contracts:")
                for contract in calls:
                    print(f"     Strike ${contract.strike} Exp {contract.expiration} Delta {contract.delta:.3f}")
        
        # 6. Provider Information
        print("\n6. Provider Information")
        info = provider.get_provider_info()
        print(f"   Type: {info['type']}")
        print(f"   Name: {info['name']}")
        print(f"   Supports Screening: {info['supports_screening']}")
        print(f"   Supports Greeks: {info['supports_greeks']}")
        print(f"   Supports Batch Quotes: {info['supports_batch_quotes']}")
        
    finally:
        await provider.close()
    
    print("\n✓ Async provider demo completed")


def demo_sync_eodhd_provider():
    """Demonstrate the sync EODHD provider."""
    print("\n\n=== Sync EODHD Provider Demo ===")
    
    # Create provider using factory function
    provider = create_sync_eodhd_provider(
        api_token=os.getenv('EODHD_API_TOKEN', 'demo'),
        timeout=30.0,
        max_retries=3,
        screening_cache_ttl_hours=24
    )
    
    try:
        # 1. Health Check
        print("\n1. Health Check")
        health = provider.health_check()
        print(f"   Status: {health.status}")
        print(f"   Latency: {health.latency_ms:.1f}ms" if health.latency_ms else "   Latency: N/A")
        
        # 2. Stock Quote
        print("\n2. Stock Quote - AAPL")
        quote_response = provider.get_stock_quote('AAPL')
        if quote_response.is_success:
            quote = quote_response.data
            print(f"   Symbol: {quote.symbol}")
            print(f"   Last: ${quote.last}")
            print(f"   Provider: {quote_response.provider_name}")
        else:
            print(f"   Error: {quote_response.error}")
        
        # 3. Credits Estimation
        print("\n3. Credits Estimation")
        screening_credits = provider.estimate_credits_required('screen_stocks')
        quote_credits = provider.estimate_credits_required('get_stock_quote')
        options_credits = provider.estimate_credits_required('get_options_chain')
        batch_credits = provider.estimate_credits_required('get_stock_quotes', symbols=['A', 'B', 'C'])
        
        print(f"   Screening: {screening_credits} credits (expensive!)")
        print(f"   Single Quote: {quote_credits} credit")
        print(f"   Options Chain: {options_credits} credit")
        print(f"   3 Batch Quotes: {batch_credits} credits")
        
        # 4. Provider Statistics
        print("\n4. Provider Statistics")
        stats = provider.get_screening_stats()
        print(f"   Cache Size: {stats['cache_size']}")
        print(f"   Cache TTL: {stats['cache_ttl_hours']} hours")
        print(f"   Request Count: {stats['request_count']}")
        print(f"   Error Count: {stats['error_count']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        
        # 5. EODHD-Specific Methods
        print("\n5. EODHD-Specific Features")
        print(f"   Supports all DataProvider operations: {all(provider.supports_operation(op) for op in ['screen_stocks', 'get_options_chain', 'get_stock_quote', 'get_greeks'])}")
        
        # Note: PMCC-specific methods available but skipped to preserve credits
        print("   (PMCC universe and optimized options methods available)")
        
    finally:
        provider.close()
    
    print("\n✓ Sync provider demo completed")


def main():
    """Run the EODHD provider demonstrations."""
    print("EODHD DataProvider Implementation Demo")
    print("=====================================")
    print("This demo shows how the new EODHD providers wrap the existing")
    print("EODHDClient functionality while implementing the DataProvider interface.")
    print("\nKey Benefits:")
    print("- Native stock screening (EODHD's strength)")
    print("- Comprehensive options data with Greeks")
    print("- Proper rate limiting and credit management")
    print("- Caching for expensive operations")
    print("- Both async and sync interfaces")
    
    # Run async demo
    asyncio.run(demo_async_eodhd_provider())
    
    # Run sync demo
    demo_sync_eodhd_provider()
    
    print("\n" + "="*60)
    print("Demo completed successfully!")
    print("Both async and sync EODHD providers are ready for use.")
    print("They maintain all existing EODHDClient functionality while")
    print("providing the standardized DataProvider interface.")


if __name__ == "__main__":
    main()