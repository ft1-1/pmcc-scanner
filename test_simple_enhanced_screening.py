#!/usr/bin/env python3
"""Simple test of enhanced EODHD screening."""

import asyncio
from decimal import Decimal

from src.config.settings import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType, ScreeningCriteria

async def main():
    settings = get_settings()
    
    config = {
        'api_token': settings.eodhd.api_token,
        'base_url': settings.eodhd.base_url,
        'timeout': settings.eodhd.timeout_seconds
    }
    
    provider = EnhancedEODHDProvider(ProviderType.EODHD, config)
    
    criteria = ScreeningCriteria(
        min_market_cap=Decimal('50000000'),
        max_market_cap=Decimal('5000000000'),
        min_volume=100000,
        exchanges=['NYSE', 'NASDAQ'],
        limit=5000
    )
    
    print("Starting enhanced EODHD screening test...")
    print(f"Requesting up to {criteria.limit} stocks")
    print("Using market cap range splitting to bypass API limits")
    
    try:
        response = await provider.screen_stocks(criteria)
        
        if response.is_success and response.data:
            total = len(response.data.results)
            print(f"\n✅ SUCCESS: Retrieved {total} stocks!")
            
            if total > 0:
                print("\nFirst 5 stocks:")
                for i, stock in enumerate(response.data.results[:5]):
                    market_cap_m = float(stock.market_capitalization or 0) / 1000000
                    print(f"{i+1}. {stock.code}: ${market_cap_m:.0f}M - {stock.name}")
        else:
            print(f"\n❌ FAILED: {response.error}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(main())