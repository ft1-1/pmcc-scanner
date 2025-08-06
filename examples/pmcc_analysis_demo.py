#!/usr/bin/env python3
"""
PMCC Analysis Demo

Demonstrates the usage of the PMCC analysis engine with example data.
This script shows how to:
1. Set up the scanner with configuration
2. Screen stocks for PMCC suitability  
3. Analyze options chains for opportunities
4. Calculate comprehensive risk metrics
5. Export results

Note: This demo uses mock data. In production, you would configure
a real MarketData.app API client with your API token.
"""

import os
import sys
from decimal import Decimal
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from analysis.scanner import PMCCScanner, ScanConfiguration
from analysis.stock_screener import ScreeningCriteria
from analysis.options_analyzer import LEAPSCriteria, ShortCallCriteria
from api.marketdata_client import MarketDataClient


def create_demo_scanner():
    """Create a scanner with demo configuration."""
    
    # Note: In production, use your actual API token
    # api_client = MarketDataClient(api_token="your_token_here")
    
    # For demo, we'll use a mock client
    from unittest.mock import Mock
    api_client = Mock()
    
    return PMCCScanner(api_client)


def demo_scan_configuration():
    """Demonstrate different scan configurations."""
    
    print("=== PMCC Scan Configuration Examples ===\n")
    
    # Conservative configuration
    conservative_config = ScanConfiguration(
        universe="SP500",
        max_stocks_to_screen=50,
        screening_criteria=ScreeningCriteria(
            min_market_cap=Decimal('1000'),  # $1B+ market cap
            max_market_cap=Decimal('10000'), # Up to $10B
            min_price=Decimal('25'),
            max_price=Decimal('300'),
            min_daily_volume=2_000_000,
            require_leaps=True,
            require_weekly_options=True,
            min_iv_rank=Decimal('40'),
            max_iv_rank=Decimal('70')
        ),
        leaps_criteria=LEAPSCriteria(
            min_dte=365,  # 1+ year
            max_dte=730,  # Up to 2 years
            min_delta=Decimal('0.80'),  # Deep ITM
            max_delta=Decimal('0.90'),
            min_open_interest=100,
            max_bid_ask_spread_pct=Decimal('3.0')  # Tight spreads
        ),
        short_criteria=ShortCallCriteria(
            min_dte=28,   # 4+ weeks
            max_dte=42,   # 6 weeks max
            min_delta=Decimal('0.25'),
            max_delta=Decimal('0.35'),
            min_open_interest=50,
            max_bid_ask_spread_pct=Decimal('8.0')
        ),
        account_size=Decimal('250000'),  # $250k account
        max_risk_per_trade=Decimal('0.015'),  # 1.5% risk per trade
        max_opportunities=15,
        min_total_score=Decimal('70')
    )
    
    print("Conservative Configuration:")
    print(f"  - Universe: {conservative_config.universe}")
    print(f"  - Market Cap: ${conservative_config.screening_criteria.min_market_cap}M - ${conservative_config.screening_criteria.max_market_cap}M")
    print(f"  - LEAPS Delta: {conservative_config.leaps_criteria.min_delta} - {conservative_config.leaps_criteria.max_delta}")
    print(f"  - Short Delta: {conservative_config.short_criteria.min_delta} - {conservative_config.short_criteria.max_delta}")
    print(f"  - Min Score: {conservative_config.min_total_score}\n")
    
    # Aggressive configuration
    aggressive_config = ScanConfiguration(
        universe="NASDAQ100",
        screening_criteria=ScreeningCriteria(
            min_market_cap=Decimal('100'),   # Smaller companies
            max_market_cap=Decimal('5000'),
            min_price=Decimal('15'),
            max_price=Decimal('500'),
            min_daily_volume=1_000_000,
            min_iv_rank=Decimal('50'),  # Higher volatility
            max_iv_rank=Decimal('85')
        ),
        leaps_criteria=LEAPSCriteria(
            min_dte=270,  # 9+ months
            min_delta=Decimal('0.75'),  # Less conservative
            max_bid_ask_spread_pct=Decimal('5.0')
        ),
        short_criteria=ShortCallCriteria(
            min_dte=21,   # 3+ weeks
            max_dte=49,   # 7 weeks max
            min_delta=Decimal('0.20'),  # More aggressive
            max_delta=Decimal('0.40'),
            max_bid_ask_spread_pct=Decimal('12.0')
        ),
        account_size=Decimal('100000'),  # $100k account
        max_risk_per_trade=Decimal('0.025'),  # 2.5% risk per trade
        max_opportunities=25,
        min_total_score=Decimal('60')  # Lower threshold
    )
    
    print("Aggressive Configuration:")
    print(f"  - Universe: {aggressive_config.universe}")
    print(f"  - Market Cap: ${aggressive_config.screening_criteria.min_market_cap}M - ${aggressive_config.screening_criteria.max_market_cap}M")
    print(f"  - IV Rank: {aggressive_config.screening_criteria.min_iv_rank} - {aggressive_config.screening_criteria.max_iv_rank}")
    print(f"  - Risk per Trade: {aggressive_config.max_risk_per_trade * 100}%")
    print(f"  - Min Score: {aggressive_config.min_total_score}\n")
    
    return conservative_config, aggressive_config


def demo_individual_symbol_analysis():
    """Demonstrate analyzing a specific symbol."""
    
    print("=== Individual Symbol Analysis ===\n")
    
    scanner = create_demo_scanner()
    
    # Configure for single symbol analysis
    config = ScanConfiguration(
        leaps_criteria=LEAPSCriteria(
            min_dte=365,
            min_delta=Decimal('0.75'),
            min_open_interest=50
        ),
        short_criteria=ShortCallCriteria(
            min_dte=21,
            max_dte=45,
            min_delta=Decimal('0.20'),
            max_delta=Decimal('0.35'),
            min_open_interest=25
        )
    )
    
    # Demo symbols to analyze
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    
    print("Analyzing individual symbols for PMCC opportunities:\n")
    
    for symbol in symbols:
        print(f"Symbol: {symbol}")
        print("  Status: [Would analyze with real API data]")
        print("  Expected: Screen options chain, identify LEAPS and short calls")
        print("  Output: List of ranked PMCC opportunities\n")
    
    # In a real implementation:
    # candidates = scanner.scan_symbol(symbol, config)
    # for candidate in candidates:
    #     print(f"  Opportunity: {candidate.analysis.long_call.option_symbol} / {candidate.analysis.short_call.option_symbol}")
    #     print(f"  Score: {candidate.total_score}")
    #     print(f"  Max Profit: ${candidate.analysis.risk_metrics.max_profit}")
    #     print(f"  Risk/Reward: {candidate.risk_reward_ratio:.3f}")


def demo_risk_analysis():
    """Demonstrate comprehensive risk analysis."""
    
    print("=== Risk Analysis Demo ===\n")
    
    print("Comprehensive Risk Analysis includes:")
    print("1. Basic Risk Metrics:")
    print("   - Maximum loss (net debit paid)")
    print("   - Maximum profit (at short strike)")
    print("   - Breakeven point")
    print("   - Risk/reward ratio")
    print("   - Probability of profit estimate\n")
    
    print("2. Greeks Analysis:")
    print("   - Net Delta (directional risk)")
    print("   - Net Gamma (delta change risk)")
    print("   - Net Theta (time decay benefit/cost)")
    print("   - Net Vega (volatility risk)\n")
    
    print("3. Early Assignment Risk:")
    print("   - ITM amount assessment")
    print("   - Dividend risk evaluation")
    print("   - Time to expiration factors")
    print("   - Assignment probability estimate\n")
    
    print("4. Position Sizing:")
    print("   - Kelly Criterion application")
    print("   - Account size considerations")
    print("   - Maximum position recommendations")
    print("   - Capital efficiency analysis\n")
    
    print("5. Scenario Analysis:")
    print("   - Multiple price scenarios")
    print("   - P&L at various stock prices")
    print("   - Value at Risk (VaR) calculation")
    print("   - Expected shortfall analysis\n")
    
    # Example risk metrics (mock data)
    print("Example PMCC Risk Analysis:")
    print("Symbol: AAPL")
    print("Long: AAPL Dec 2024 $140 Call")
    print("Short: AAPL Mar 2024 $165 Call")
    print("Current Price: $155.50")
    print("")
    print("Risk Metrics:")
    print("  Net Debit: $21.85")
    print("  Max Profit: $3.15 (14.4% ROI)")
    print("  Max Loss: $21.85 (net debit)")
    print("  Breakeven: $161.85")
    print("  Risk/Reward: 1:0.14")
    print("")
    print("Greeks:")
    print("  Net Delta: +0.60 (bullish bias)")
    print("  Net Theta: $0.00 (time neutral initially)")
    print("  Net Vega: +0.04 (slight vol risk)")
    print("")
    print("Early Assignment Risk: LOW")
    print("  - Short call is OTM")
    print("  - 35 days to expiration")
    print("  - No dividend before expiration")
    print("")


def demo_export_and_reporting():
    """Demonstrate result export and reporting."""
    
    print("=== Export and Reporting Demo ===\n")
    
    print("Available Export Formats:")
    print("1. JSON - Structured data with all details")
    print("2. CSV - Tabular format for spreadsheet analysis")
    print("3. Custom formats can be added\n")
    
    print("Report Contents:")
    print("- Scan summary and statistics")
    print("- Top-ranked opportunities")
    print("- Detailed risk analysis for each")
    print("- Position sizing recommendations")
    print("- Performance metrics and scores\n")
    
    print("Example JSON Export Structure:")
    example_export = {
        "scan_id": "pmcc_scan_20240115_143022",
        "started_at": "2024-01-15T14:30:22",
        "completed_at": "2024-01-15T14:32:45",
        "total_duration_seconds": 143.2,
        "stats": {
            "stocks_screened": 100,
            "stocks_passed_screening": 23,
            "opportunities_found": 12,
            "success_rate": "23.0%",
            "opportunity_rate": "52.2%"
        },
        "top_opportunities": [
            {
                "symbol": "AAPL",
                "underlying_price": 155.50,
                "long_call": {
                    "option_symbol": "AAPL241220C00140000",
                    "strike": 140.0,
                    "expiration": "2024-12-20T00:00:00",
                    "delta": 0.78,
                    "dte": 450
                },
                "short_call": {
                    "option_symbol": "AAPL240315C00165000", 
                    "strike": 165.0,
                    "expiration": "2024-03-15T00:00:00",
                    "delta": 0.18,
                    "dte": 35
                },
                "net_debit": 21.85,
                "max_profit": 3.15,
                "max_loss": 21.85,
                "breakeven": 161.85,
                "risk_reward_ratio": 0.144,
                "total_score": 87.5,
                "rank": 1
            }
        ]
    }
    
    import json
    print(json.dumps(example_export, indent=2)[:800] + "...")


def main():
    """Run the PMCC analysis demonstration."""
    
    print("PMCC (Poor Man's Covered Call) Analysis Engine Demo")
    print("=" * 55)
    print()
    
    # Configuration examples
    demo_scan_configuration()
    print()
    
    # Individual symbol analysis
    demo_individual_symbol_analysis()
    print()
    
    # Risk analysis demonstration
    demo_risk_analysis()
    print()
    
    # Export and reporting
    demo_export_and_reporting()
    print()
    
    print("=== Demo Complete ===\n")
    print("To use with real data:")
    print("1. Get API token from MarketData.app")
    print("2. Set up MarketDataClient with your token")
    print("3. Configure scan parameters for your strategy")
    print("4. Run scanner.scan() to find opportunities")
    print("5. Export results for further analysis")
    print("\nSee integration tests for working examples with mock data.")


if __name__ == "__main__":
    main()