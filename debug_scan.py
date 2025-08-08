#!/usr/bin/env python3
"""Debug the scan to see why opportunities aren't showing up."""

import logging
from src.config import get_settings
from src.api.provider_factory import SyncDataProviderFactory
from src.analysis.scanner import PMCCScanner
from src.analysis.scanner import ScanConfiguration

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_scan():
    """Debug the scan process."""
    settings = get_settings()
    
    # Create scanner
    factory = SyncDataProviderFactory()
    scanner = PMCCScanner(provider_factory=factory)
    
    # Create scan config
    config = ScanConfiguration()
    print(f"Min total score: {config.min_total_score}")
    print(f"Custom symbols: {config.custom_symbols}")
    
    # Run scan
    results = scanner.scan(config)
    
    print(f"\nScan Results:")
    print(f"  Stocks screened: {results.stocks_screened}")
    print(f"  Stocks passed screening: {results.stocks_passed_screening}")
    print(f"  Options analyzed: {results.options_analyzed}")
    print(f"  Opportunities found: {results.opportunities_found}")
    print(f"  Top opportunities: {len(results.top_opportunities)}")
    
    # Debug: Check all opportunities before filtering
    print("\nDEBUG: Checking opportunity scores...")
    
    # Let's scan KSS directly to see the scores
    symbol = "KSS"
    print(f"\nScanning {symbol} directly...")
    candidates = scanner.scan_symbol(symbol, config)
    
    for i, candidate in enumerate(candidates):
        print(f"\nOpportunity {i+1}:")
        print(f"  Symbol: {candidate.symbol}")
        print(f"  Total Score: {candidate.total_score}")
        print(f"  Liquidity Score: {candidate.liquidity_score}")
        print(f"  Strategy Score: {candidate.strategy_score}")
        print(f"  Risk Score: {candidate.risk_score}")
        if hasattr(candidate, 'analysis') and candidate.analysis:
            print(f"  Net Debit: ${candidate.analysis.net_debit}")
            print(f"  Long Call: {candidate.analysis.long_call.strike}C @ {candidate.analysis.long_call.expiration_date}")
            print(f"  Short Call: {candidate.analysis.short_call.strike}C @ {candidate.analysis.short_call.expiration_date}")

if __name__ == "__main__":
    debug_scan()