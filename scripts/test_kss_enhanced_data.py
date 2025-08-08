#!/usr/bin/env python3
"""
Test script to show detailed EODHD enhanced data for KSS that's provided to Claude AI.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_kss_enhanced_data():
    """Test and display all enhanced data for KSS."""
    print("\n" + "="*100)
    print("KSS ENHANCED DATA TEST - What Claude AI Receives")
    print("="*100 + "\n")
    
    # Get settings
    settings = get_settings()
    
    # Initialize enhanced EODHD provider
    eodhd_config = {
        'api_token': settings.eodhd.api_token if settings.eodhd else None
    }
    
    if not eodhd_config['api_token']:
        print("❌ EODHD API token not configured")
        return
    
    provider = EnhancedEODHDProvider(ProviderType.EODHD, eodhd_config)
    
    symbol = "KSS"
    print(f"Testing enhanced data collection for: {symbol}\n")
    
    try:
        # 1. Get enhanced stock data (all-in-one)
        print("1. FETCHING ENHANCED STOCK DATA")
        print("-" * 50)
        
        enhanced_response = await provider.get_enhanced_stock_data(symbol)
        
        if not enhanced_response.is_success:
            print(f"❌ Failed to get enhanced data: {enhanced_response.error}")
            return
        
        enhanced_data = enhanced_response.data
        print(f"✅ Data completeness score: {enhanced_data.data_completeness_score}%")
        
        # 2. Display Stock Quote
        print("\n2. STOCK QUOTE DATA")
        print("-" * 50)
        if enhanced_data.quote:
            quote = enhanced_data.quote
            print(f"Symbol: {quote.symbol}")
            print(f"Price: ${quote.last}")
            print(f"Volume: {quote.volume:,}" if quote.volume else "Volume: N/A")
            print(f"Updated: {quote.updated}" if hasattr(quote, 'updated') and quote.updated else "Updated: N/A")
        else:
            print("❌ No quote data available")
        
        # 3. Display Fundamental Data
        print("\n3. FUNDAMENTAL DATA")
        print("-" * 50)
        if enhanced_data.fundamentals:
            fund = enhanced_data.fundamentals
            print(f"Symbol: {fund.symbol}")
            print(f"\nValuation Metrics:")
            print(f"  P/E Ratio: {fund.pe_ratio}")
            print(f"  PEG Ratio: {fund.peg_ratio}")
            print(f"  Price/Book: {fund.pb_ratio}")
            print(f"  Price/Sales: {fund.ps_ratio}")
            print(f"  EV/EBITDA: {fund.ev_to_ebitda}")
            print(f"  Enterprise Value: ${fund.enterprise_value:,.0f}" if fund.enterprise_value else "  Enterprise Value: N/A")
            print(f"\nProfitability:")
            print(f"  ROE: {fund.roe}%")
            print(f"  ROA: {fund.roa}%")
            print(f"  ROIC: {fund.roic}%")
            print(f"  Gross Margin: {fund.gross_margin}%")
            print(f"  Operating Margin: {fund.operating_margin}%")
            print(f"  Net Margin: {fund.profit_margin}%")
            print(f"\nFinancial Health:")
            print(f"  Current Ratio: {fund.current_ratio}")
            print(f"  Quick Ratio: {fund.quick_ratio}")
            print(f"  Debt/Equity: {fund.debt_to_equity}")
            print(f"  Cash Ratio: {fund.cash_ratio}")
            print(f"\nGrowth Rates:")
            print(f"  Revenue Growth: {fund.revenue_growth_rate}%")
            print(f"  Earnings Growth: {fund.earnings_growth_rate}%")
            print(f"  Book Value Growth: {fund.book_value_growth_rate}%")
            print(f"\nPer Share Data:")
            print(f"  EPS: ${fund.earnings_per_share}")
            print(f"  Book Value/Share: ${fund.book_value_per_share}")
            print(f"  Revenue/Share: ${fund.revenue_per_share}")
            print(f"  Cash/Share: ${fund.cash_per_share}")
            # Note: dividend info comes from other fields or calendar events
        else:
            print("❌ No fundamental data available")
        
        # 4. Display Calendar Events
        print("\n4. CALENDAR EVENTS")
        print("-" * 50)
        if enhanced_data.calendar_events:
            for event in enhanced_data.calendar_events[:5]:  # Show first 5
                print(f"  {event.event_type}: {event.date}")
                if event.event_type == 'earnings':
                    print(f"    Estimate: ${event.estimate}, Actual: ${event.actual}")
                elif event.event_type == 'dividend':
                    print(f"    Amount: ${event.amount}, Ex-Date: {event.ex_dividend_date}")
        else:
            print("  No upcoming calendar events")
        
        # 5. Display Technical Indicators
        print("\n5. TECHNICAL INDICATORS")
        print("-" * 50)
        if enhanced_data.technical_indicators:
            tech = enhanced_data.technical_indicators
            print(f"Symbol: {tech.symbol}")
            print(f"Beta: {tech.beta}")
            print(f"30-day Volatility: {tech.volatility_30d}%")
            print(f"RSI (14d): {tech.rsi_14d}")
            print(f"50-Day SMA: ${tech.sma_50d}")
            print(f"200-Day SMA: ${tech.sma_200d}")
            print(f"Avg Volume (30d): {tech.avg_volume_30d:,}" if tech.avg_volume_30d else "Avg Volume (30d): N/A")
            print(f"Sector: {tech.sector}")
            print(f"Industry: {tech.industry}")
            print(f"Market Cap Category: {tech.market_cap_category}")
        else:
            print("❌ No technical indicators available")
        
        # 6. Display Risk Metrics
        print("\n6. RISK METRICS")
        print("-" * 50)
        if enhanced_data.risk_metrics:
            risk = enhanced_data.risk_metrics
            print(f"Symbol: {risk.symbol}")
            print(f"Institutional Ownership: {risk.institutional_ownership}%")
            print(f"Insider Ownership: {risk.insider_ownership}%")
            print(f"Short Interest: {risk.short_interest}%")
            print(f"Analyst Rating Avg: {risk.analyst_rating_avg}")
            print(f"Analyst Target Avg: ${risk.price_target_avg}")
            print(f"Number of Analysts: {risk.analyst_count}")
            print(f"Price Target Upside: {risk.price_target_upside}%")
            print(f"Credit Rating: {risk.credit_rating}")
            print(f"Financial Strength Score: {risk.financial_strength_score}")
            print(f"Bankruptcy Risk Score: {risk.bankruptcy_risk_score}%")
        else:
            print("❌ No risk metrics available")
        
        # 7. Show what's missing (options data)
        print("\n7. OPTIONS DATA (from MarketData.app, not EODHD)")
        print("-" * 50)
        print("Note: Options chain data must come from MarketData.app provider")
        print("Enhanced EODHD provides fundamentals only, not options")
        
        # 8. Export to JSON for inspection
        print("\n8. EXPORTING COMPLETE DATA")
        print("-" * 50)
        
        # Convert to dict for export (using to_dict method for EnhancedStockData)
        export_data = enhanced_data.to_dict() if hasattr(enhanced_data, 'to_dict') else {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'data_completeness_score': enhanced_data.data_completeness_score,
            'note': 'Complete data structure available but to_dict() method not found'
        }
        
        output_file = f"data/kss_enhanced_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Complete enhanced data exported to: {output_file}")
        
        # 9. Summary of what Claude AI receives
        print("\n9. SUMMARY - DATA PROVIDED TO CLAUDE AI")
        print("-" * 50)
        print(f"✅ Stock Quote: {'Yes' if enhanced_data.quote else 'No'}")
        print(f"✅ Fundamentals: {'Yes' if enhanced_data.fundamentals else 'No'}")
        print(f"✅ Calendar Events: {len(enhanced_data.calendar_events)} events")
        print(f"✅ Technical Indicators: {'Yes' if enhanced_data.technical_indicators else 'No'}")
        print(f"✅ Risk Metrics: {'Yes' if enhanced_data.risk_metrics else 'No'}")
        print(f"❌ Options Chain: No (must come from MarketData.app)")
        print(f"\nOverall Data Completeness: {enhanced_data.data_completeness_score}%")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
    
    finally:
        await provider.close()


if __name__ == "__main__":
    print("Starting KSS enhanced data test...")
    asyncio.run(test_kss_enhanced_data())