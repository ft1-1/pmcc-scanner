#!/usr/bin/env python3
"""
Enhanced EODHD Provider Demo

This script demonstrates how to use the Enhanced EODHD Provider for AI-enhanced 
PMCC analysis with comprehensive fundamental data, calendar events, technical 
indicators, and risk metrics.

Usage:
    python examples/enhanced_eodhd_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.data_provider import ProviderType
from api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from api.provider_factory import DataProviderFactory, ProviderConfig
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demo_enhanced_eodhd():
    """
    Demonstrate the Enhanced EODHD Provider capabilities.
    """
    print("🚀 Enhanced EODHD Provider Demo")
    print("=" * 50)
    
    # Initialize the enhanced provider
    config = {
        'api_token': os.getenv('EODHD_API_TOKEN', 'demo'),  # Use demo token if not set
        'enable_caching': True,
        'cache_ttl_hours': 24
    }
    
    try:
        provider = EnhancedEODHDProvider(ProviderType.EODHD, config)
        
        # Test symbol - using AAPL as it has comprehensive data
        test_symbol = "AAPL"
        
        print(f"\n📊 Testing Enhanced EODHD Provider with {test_symbol}")
        print("-" * 40)
        
        # 1. Health Check
        print("\n🔍 1. Health Check")
        health = await provider.health_check()
        print(f"   Status: {health.status.value}")
        print(f"   Latency: {health.latency_ms:.1f}ms")
        if health.error_message:
            print(f"   Error: {health.error_message}")
        
        if health.status.value != 'healthy':
            print("   ⚠️  Provider not healthy, some operations may fail")
        
        # 2. Basic Stock Quote
        print(f"\n💹 2. Stock Quote for {test_symbol}")
        quote_response = await provider.get_stock_quote(test_symbol)
        if quote_response.is_success:
            quote = quote_response.data
            print(f"   Symbol: {quote.symbol}")
            print(f"   Last Price: ${quote.last}")
            print(f"   Volume: {quote.volume:,}" if quote.volume else "   Volume: N/A")
            print(f"   Updated: {quote.updated}")
        else:
            print(f"   ❌ Failed: {quote_response.error}")
        
        # 3. Fundamental Data
        print(f"\n📈 3. Fundamental Data for {test_symbol}")
        fundamental_response = await provider.get_fundamental_data(test_symbol)
        if fundamental_response.is_success:
            fundamentals = fundamental_response.data
            print(f"   Symbol: {fundamentals.symbol}")
            print(f"   P/E Ratio: {fundamentals.pe_ratio}")
            print(f"   Profit Margin: {fundamentals.profit_margin}%")
            print(f"   ROE: {fundamentals.roe}%")
            print(f"   Debt-to-Equity: {fundamentals.debt_to_equity}")
            print(f"   Sector: {getattr(fundamentals, 'sector', 'N/A')}")
        else:
            print(f"   ❌ Failed: {fundamental_response.error}")
        
        # 4. Calendar Events
        print(f"\n📅 4. Calendar Events for {test_symbol}")
        calendar_response = await provider.get_calendar_events(test_symbol)
        if calendar_response.is_success:
            events = calendar_response.data
            print(f"   Found {len(events)} upcoming events:")
            for event in events[:3]:  # Show first 3 events
                print(f"   - {event.event_type.title()}: {event.date}")
                if event.event_type == 'earnings' and event.estimated_eps:
                    print(f"     Estimated EPS: ${event.estimated_eps}")
                elif event.event_type == 'ex_dividend' and event.dividend_amount:
                    print(f"     Dividend: ${event.dividend_amount}")
        else:
            print(f"   ❌ Failed: {calendar_response.error}")
        
        # 5. Technical Indicators
        print(f"\n📊 5. Technical Indicators for {test_symbol}")
        technical_response = await provider.get_technical_indicators(test_symbol)
        if technical_response.is_success:
            technical = technical_response.data
            print(f"   Symbol: {technical.symbol}")
            print(f"   Beta: {technical.beta}")
            print(f"   Sector: {technical.sector}")
            print(f"   Industry: {technical.industry}")
            print(f"   Market Cap Category: {technical.market_cap_category}")
        else:
            print(f"   ❌ Failed: {technical_response.error}")
        
        # 6. Risk Metrics
        print(f"\n⚠️  6. Risk Metrics for {test_symbol}")
        risk_response = await provider.get_risk_metrics(test_symbol)
        if risk_response.is_success:
            risk = risk_response.data
            print(f"   Symbol: {risk.symbol}")
            print(f"   Institutional Ownership: {risk.institutional_ownership}%")
            print(f"   Insider Ownership: {risk.insider_ownership}%")
            print(f"   Short Interest: {risk.short_interest}%")
            print(f"   Analyst Rating: {risk.analyst_rating_avg}")
            print(f"   Price Target: ${risk.price_target_avg}")
        else:
            print(f"   ❌ Failed: {risk_response.error}")
        
        # 7. Enhanced Stock Data (All-in-One)
        print(f"\n🎯 7. Enhanced Stock Data for {test_symbol}")
        enhanced_response = await provider.get_enhanced_stock_data(test_symbol)
        if enhanced_response.is_success:
            enhanced = enhanced_response.data
            print(f"   Symbol: {enhanced.symbol}")
            print(f"   Data Completeness: {enhanced.data_completeness_score}%")
            print(f"   Has Fundamental Data: {enhanced.has_complete_fundamental_data}")
            print(f"   Has Options Data: {enhanced.has_options_data}")
            print(f"   Upcoming Earnings: {enhanced.upcoming_earnings_date}")
            print(f"   Next Ex-Dividend: {enhanced.next_ex_dividend_date}")
        else:
            print(f"   ❌ Failed: {enhanced_response.error}")
        
        # 8. Options Chain (if available)
        print(f"\n⚙️  8. Options Chain for {test_symbol}")
        options_response = await provider.get_options_chain(test_symbol)
        if options_response.is_success:
            chain = options_response.data
            print(f"   Underlying: {chain.underlying}")
            print(f"   Underlying Price: ${chain.underlying_price}")
            print(f"   Total Contracts: {len(chain.contracts)}")
            
            # Show some LEAPS calls suitable for PMCC
            leaps_calls = chain.get_leaps_calls()
            if leaps_calls:
                print(f"   LEAPS Calls (delta >= 0.70): {len(leaps_calls)}")
                for contract in leaps_calls[:3]:  # Show first 3
                    print(f"     {contract.option_symbol}: Strike ${contract.strike}, "
                          f"Delta {contract.delta}, DTE {contract.dte}")
        else:
            print(f"   ❌ Failed: {options_response.error}")
        
        # 9. Provider Information
        print(f"\n📋 9. Provider Information")
        provider_info = provider.get_provider_info()
        print(f"   Type: {provider_info['type']}")
        print(f"   Name: {provider_info['name']}")
        print(f"   Supports Screening: {provider_info['supports_screening']}")
        print(f"   Supports Greeks: {provider_info['supports_greeks']}")
        print(f"   Supports Enhanced Operations: {provider.supports_operation('get_enhanced_stock_data')}")
        
        # Close the provider
        await provider.close()
        
        print("\n✅ Enhanced EODHD Provider Demo Complete!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")


async def demo_provider_factory_integration():
    """
    Demonstrate integration with the Provider Factory system.
    """
    print("\n🏭 Provider Factory Integration Demo")
    print("=" * 50)
    
    # Create provider factory
    factory = DataProviderFactory()
    
    # Configure Enhanced EODHD Provider
    provider_config = ProviderConfig(
        provider_type=ProviderType.EODHD,
        provider_class=EnhancedEODHDProvider,
        config={
            'api_token': os.getenv('EODHD_API_TOKEN', 'demo'),
            'enable_caching': True,
            'cache_ttl_hours': 24
        },
        priority=10,  # High priority
        preferred_operations=[
            'get_fundamental_data', 'get_calendar_events', 
            'get_technical_indicators', 'get_risk_metrics',
            'get_enhanced_stock_data'
        ]
    )
    
    # Register the provider
    factory.register_provider(provider_config)
    
    test_symbol = "MSFT"
    
    print(f"\n🎯 Testing Factory Integration with {test_symbol}")
    print("-" * 40)
    
    try:
        # Test enhanced operations through factory
        print("\n📈 Getting enhanced stock data through factory...")
        enhanced_response = await factory.get_enhanced_stock_data(
            test_symbol, 
            preferred_provider=ProviderType.EODHD
        )
        
        if enhanced_response.is_success:
            enhanced = enhanced_response.data
            print(f"   ✅ Success! Data completeness: {enhanced.data_completeness_score}%")
            print(f"   Provider: {enhanced_response.provider_name}")
            print(f"   Latency: {enhanced_response.response_latency_ms:.1f}ms")
        else:
            print(f"   ❌ Failed: {enhanced_response.error}")
        
        # Test factory status
        print("\n📊 Factory Status")
        status = factory.get_provider_status()
        print(f"   Fallback Strategy: {status['fallback_strategy']}")
        print(f"   Registered Providers: {len(status['providers'])}")
        
        for provider_type, info in status['providers'].items():
            print(f"   {provider_type}: Priority {info['priority']}, "
                  f"Circuit Breaker {'OPEN' if info['circuit_breaker']['is_open'] else 'CLOSED'}")
        
    except Exception as e:
        logger.error(f"Factory integration demo failed: {e}")
        print(f"   ❌ Failed: {e}")


async def main():
    """Main demo function."""
    print("🌟 Enhanced EODHD Provider Comprehensive Demo")
    print("=" * 60)
    
    # Check if API token is available
    api_token = os.getenv('EODHD_API_TOKEN', 'demo')
    if api_token == 'demo':
        print("⚠️  Using demo API token - limited symbols available")
        print("   Set EODHD_API_TOKEN environment variable for full access")
    
    print(f"   API Token: {'***' + api_token[-4:] if len(api_token) > 4 else 'demo'}")
    
    # Run the demos
    await demo_enhanced_eodhd()
    await demo_provider_factory_integration()
    
    print("\n🎉 All demos completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n💥 Demo failed: {e}")
        sys.exit(1)