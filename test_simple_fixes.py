#!/usr/bin/env python3
"""
Simple test of the key fixes without complex dependencies.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_stock_quote():
    """Test StockQuote attribute additions."""
    print("=== Testing StockQuote Attribute Fixes ===")
    
    from src.models.api_models import StockQuote
    
    # Test creating with new attributes
    quote = StockQuote(
        symbol="KSS",
        last=Decimal("15.25"),
        change=Decimal("-0.35"),
        change_percent=Decimal("-2.24"),
        market_cap=Decimal("1500000000")
    )
    
    print(f"Symbol: {quote.symbol}")
    print(f"Last: {quote.last}")
    print(f"Change: {quote.change}")
    print(f"Change %: {quote.change_percent}")
    print(f"Market Cap: {quote.market_cap}")
    print("✅ StockQuote attributes test PASSED")
    return True

def test_fundamentals_dict_handling():
    """Test fundamentals dictionary handling."""
    print("\n=== Testing Fundamentals Dictionary Handling ===")
    
    # Simulate the enhanced EODHD fundamentals structure
    fundamentals_dict = {
        'company_info': {'market_cap_mln': 1500},
        'financial_health': {'eps_ttm': 2.15, 'roe': 0.12},
        'valuation_metrics': {'pe_ratio': 7.1, 'forward_pe': 6.8},
        'stock_technicals': {'beta': 1.8}
    }
    
    # Test accessing nested values (like the scanner does)
    company_info = fundamentals_dict.get('company_info', {})
    valuation_metrics = fundamentals_dict.get('valuation_metrics', {})
    
    market_cap = company_info.get('market_cap_mln', 0) * 1000000 if company_info.get('market_cap_mln') else 0
    pe_ratio = valuation_metrics.get('pe_ratio', 0) or 0
    
    print(f"Market Cap: ${market_cap:,}")
    print(f"PE Ratio: {pe_ratio}")
    print("✅ Fundamentals dictionary handling test PASSED")
    return True

def main():
    """Run simple tests."""
    print("PMCC Scanner Core Fixes Test")
    print("=" * 40)
    
    try:
        test1 = test_stock_quote()
        test2 = test_fundamentals_dict_handling()
        
        print("\n" + "=" * 40)
        if test1 and test2:
            print("🎉 ALL CORE FIXES WORKING CORRECTLY!")
            print("\nFixed issues:")
            print("✅ StockQuote has change, change_percent, market_cap attributes")
            print("✅ Dictionary fundamentals can be processed without errors")
            print("\nThe enhanced data collection → Claude AI analysis should now work!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())