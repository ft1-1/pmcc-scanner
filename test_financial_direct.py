#!/usr/bin/env python3
"""Direct test of financial data from EODHD provider"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.config import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
import asyncio

async def test_financial_data():
    """Test that financial data is properly included from EODHD"""
    print("\n=== Testing Financial Data from EODHD ===\n")
    
    # Initialize components
    settings = get_settings()
    
    # Create EODHD provider directly
    if not settings.eodhd or not settings.eodhd.api_token:
        print("✗ EODHD API token not configured")
        return
        
    print("Creating EODHD provider...")
    config = {
        'api_token': settings.eodhd.api_token,
        'enable_caching': True,
        'cache_ttl_hours': 24
    }
    
    provider = EnhancedEODHDProvider(ProviderType.EODHD, config)
    
    # Test with KSS stock
    symbol = 'KSS'
    print(f"Testing with symbol: {symbol}")
    
    try:
        # Get comprehensive enhanced data
        print("\n1. Fetching comprehensive enhanced data...")
        response = await provider.get_comprehensive_enhanced_data(symbol)
        
        if response.is_success:
            enhanced_data = response.data
            print("✓ Enhanced data fetched successfully")
            
            # Check fundamentals
            fundamentals = enhanced_data.get('fundamentals', {})
            print(f"\nFundamentals type: {type(fundamentals)}")
            
            if isinstance(fundamentals, dict):
                # Check for financial statement sections
                sections_to_check = ['balance_sheet', 'income_statement', 'cash_flow', 'analyst_sentiment']
                
                print("\n2. Checking for financial statement sections in fundamentals:")
                for section in sections_to_check:
                    if section in fundamentals:
                        section_data = fundamentals[section]
                        if section_data and isinstance(section_data, dict):
                            # Count non-zero values
                            non_zero_count = sum(1 for v in section_data.values() if v and v != 0)
                            print(f"  ✓ {section}: Found with {len(section_data)} fields ({non_zero_count} non-zero)")
                            
                            # Show sample data
                            if section == 'balance_sheet':
                                print(f"     - Total Assets: ${section_data.get('total_assets', 'N/A')}M")
                                print(f"     - Total Debt: ${section_data.get('total_debt', 'N/A')}M")
                                print(f"     - Cash: ${section_data.get('cash_and_equivalents', 'N/A')}M")
                                print(f"     - Quarter Date: {section_data.get('quarter_date', 'N/A')}")
                            elif section == 'cash_flow':
                                print(f"     - Operating Cash Flow: ${section_data.get('operating_cash_flow', 'N/A')}M")
                                print(f"     - Free Cash Flow: ${section_data.get('free_cash_flow', 'N/A')}M")
                                print(f"     - Quarter Date: {section_data.get('quarter_date', 'N/A')}")
                        else:
                            print(f"  ✗ {section}: Empty or not a dict")
                    else:
                        print(f"  ✗ {section}: Not found in fundamentals")
                
                # Save the enhanced data for inspection
                with open('test_enhanced_data.json', 'w') as f:
                    json.dump(enhanced_data, f, indent=2, default=str)
                print("\n✓ Full enhanced data saved to test_enhanced_data.json")
                
            else:
                print(f"✗ Fundamentals is not a dict: {type(fundamentals)}")
        else:
            print(f"✗ Failed to fetch enhanced data: {response.error}")
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(test_financial_data())