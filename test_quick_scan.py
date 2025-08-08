#!/usr/bin/env python3
"""Quick test of complete workflow with limited stocks."""

import asyncio
import logging
from src.config import get_settings
from src.analysis.scanner import PMCCScanner
from src.config.provider_config import ProviderConfigurationManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_workflow():
    """Test complete enhanced workflow with a few stocks."""
    print("\n=== PMCC AI Enhancement Workflow Test ===\n")
    
    # Get settings and create scanner
    settings = get_settings()
    scanner = PMCCScanner.create_with_provider_factory(settings)
    
    # Test with just a few liquid stocks
    test_symbols = ["AAPL", "MSFT", "SPY"]
    
    print(f"Testing with symbols: {test_symbols}")
    print(f"Provider architecture:")
    print(f"  - Options data: MarketData.app")
    print(f"  - Fundamentals: EODHD")
    print(f"  - AI Analysis: Claude")
    
    # Run scan
    print("\nRunning enhanced PMCC scan...")
    results = await scanner.scan_symbols(test_symbols)
    
    if results:
        print(f"\n✅ Scan completed! Found {len(results)} opportunities")
        
        # Show first result
        if results:
            first = results[0]
            print(f"\nExample opportunity: {first.get('symbol', 'Unknown')}")
            print(f"  PMCC Score: {first.get('pmcc_score', 0):.2f}")
            if 'ai_analysis' in first:
                print(f"  AI Score: {first['ai_analysis'].get('score', 0):.2f}")
                print(f"  AI Reasoning: {first['ai_analysis'].get('reasoning', 'N/A')[:100]}...")
            else:
                print("  AI Analysis: Not available")
    else:
        print("\n❌ No opportunities found")
    
    print("\n✅ Workflow test complete!")
    
    # Test provider routing
    print("\n=== Provider Routing Test ===")
    factory = scanner.provider_factory
    
    operations = ["get_options_chain", "screen_stocks", "get_fundamental_data", "get_stock_quote"]
    for op in operations:
        provider = factory.get_provider(op)
        if provider:
            print(f"  {op} → {provider.__class__.__name__}")
        else:
            print(f"  {op} → No provider available")

if __name__ == "__main__":
    asyncio.run(test_workflow())