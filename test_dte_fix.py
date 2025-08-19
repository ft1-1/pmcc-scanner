#!/usr/bin/env python3
"""Test script to verify DTE fix."""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import get_settings
from src.api.providers.marketdata_provider import MarketDataProvider
from src.models.api_models import APIStatus

async def test_dte():
    """Test if DTE is properly calculated."""
    settings = get_settings()
    
    # Create provider
    provider = MarketDataProvider(settings)
    await provider.initialize()
    
    # Fetch option chain
    print("Fetching ANF option chain...")
    response = await provider.get_options_chain("ANF")
    
    if response.status == APIStatus.OK and response.data:
        chain = response.data
        print(f"\nUnderlying: {chain.underlying}")
        print(f"Underlying price: {chain.underlying_price}")
        print(f"Total contracts: {len(chain.contracts)}")
        
        # Check LEAPS contracts
        leaps_count = 0
        for contract in chain.contracts:
            if contract.side.value == 'call' and contract.dte and 180 <= contract.dte <= 730:
                leaps_count += 1
                if leaps_count <= 3:  # Show first 3
                    print(f"\nLEAPS Contract:")
                    print(f"  Strike: ${contract.strike}")
                    print(f"  DTE: {contract.dte}")
                    print(f"  Delta: {contract.delta}")
                    print(f"  OI: {contract.open_interest}")
                    print(f"  Underlying price: {contract.underlying_price}")
                    print(f"  Moneyness: {contract.moneyness}")
        
        print(f"\nTotal LEAPS found: {leaps_count}")
    else:
        print(f"Error: {response.error}")
    
    await provider.close()

if __name__ == "__main__":
    asyncio.run(test_dte())