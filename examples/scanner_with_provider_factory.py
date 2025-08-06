#!/usr/bin/env python3
"""
Example script demonstrating PMCC Scanner with Provider Factory integration.

This script shows how to use the new provider abstraction system with automatic failover
between EODHD and MarketData.app providers based on operation type and availability.
"""

import os
import sys
import logging
from decimal import Decimal

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from analysis.scanner import PMCCScanner, ScanConfiguration, LEAPSCriteria, ShortCallCriteria
from analysis.stock_screener import ScreeningCriteria
from config.provider_config import DataProviderSettings, ProviderConfigurationManager
from api.provider_factory import FallbackStrategy
from api.data_provider import ProviderType

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scanner_provider_example.log')
        ]
    )

def main():
    """Main example function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check environment variables
    if not os.getenv('EODHD_API_TOKEN'):
        logger.error("EODHD_API_TOKEN environment variable not set")
        return
    
    if not os.getenv('MARKETDATA_API_TOKEN'):
        logger.warning("MARKETDATA_API_TOKEN not set - will use EODHD only")
    
    try:
        # Configure provider settings for optimal routing
        provider_settings = DataProviderSettings(
            primary_provider=ProviderType.EODHD,  # Primary for screening
            fallback_strategy=FallbackStrategy.OPERATION_SPECIFIC,  # Route operations optimally
            preferred_stock_screener=ProviderType.EODHD,  # EODHD has native screener
            preferred_options_provider=ProviderType.MARKETDATA,  # MarketData.app has better options API
            preferred_quotes_provider=ProviderType.MARKETDATA,  # MarketData.app has real-time data
            preferred_greeks_provider=ProviderType.MARKETDATA,
            health_check_interval_seconds=300,
            max_concurrent_requests_per_provider=5,
            prioritize_cost_efficiency=True,
            max_daily_api_credits=5000
        )
        
        # Create scanner with provider factory
        logger.info("Creating PMCC Scanner with provider factory...")
        scanner = PMCCScanner.create_with_provider_factory(provider_settings)
        
        # Display provider status
        provider_status = scanner.get_provider_status()
        logger.info("Provider Status:")
        for provider, status in provider_status.get('config_summary', {}).get('providers', {}).items():
            logger.info(f"  {provider}: {'Available' if status.get('available') else 'Not Available'}")
        
        # Configure scan parameters
        scan_config = ScanConfiguration(
            universe="DEMO",  # Use demo universe for testing
            custom_symbols=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],  # Test with specific symbols
            max_stocks_to_screen=10,
            
            # Screening criteria
            screening_criteria=ScreeningCriteria(
                min_price=Decimal('20'),
                max_price=Decimal('500'),
                min_volume=100000,
                min_market_cap=Decimal('1000000000'),  # 1B minimum
                has_options=True
            ),
            
            # LEAPS criteria  
            leaps_criteria=LEAPSCriteria(
                min_dte=180,  # 6 months minimum
                max_dte=720,  # 24 months maximum
                min_delta=Decimal('0.70'),
                max_delta=Decimal('0.90'),
                min_open_interest=10
            ),
            
            # Short call criteria
            short_criteria=ShortCallCriteria(
                min_dte=21,   # 3 weeks minimum
                max_dte=45,   # 6 weeks maximum
                min_delta=Decimal('0.15'),
                max_delta=Decimal('0.35'),
                min_open_interest=5
            ),
            
            # Output settings
            max_opportunities=10,
            min_total_score=Decimal('60')
        )
        
        # Execute scan
        logger.info("Starting PMCC scan with provider factory...")
        results = scanner.scan(scan_config)
        
        # Display results summary
        logger.info("Scan Results Summary:")
        logger.info(f"  Scan ID: {results.scan_id}")
        logger.info(f"  Duration: {results.total_duration_seconds:.1f} seconds")
        logger.info(f"  Stocks Screened: {results.stocks_screened}")
        logger.info(f"  Stocks Passed: {results.stocks_passed_screening}")
        logger.info(f"  Options Analyzed: {results.options_analyzed}")
        logger.info(f"  Opportunities Found: {results.opportunities_found}")
        logger.info(f"  Top Opportunities: {len(results.top_opportunities)}")
        
        # Display provider usage statistics
        if results.provider_usage:
            logger.info("Provider Usage Statistics:")
            for provider_type, stats in results.provider_usage.items():
                logger.info(f"  {provider_type.value}:")
                logger.info(f"    Operations: {stats.operations_count}")
                logger.info(f"    Success Rate: {stats.success_rate:.1%}")
                logger.info(f"    Avg Latency: {stats.average_latency_ms:.1f}ms")
                logger.info(f"    Credits Used: {stats.credits_used}")
        
        # Display operation routing
        if results.operation_routing:
            logger.info("Operation Routing:")
            for operation, ops in results.operation_routing.items():
                if ops:
                    providers_used = set(provider.value if hasattr(provider, 'value') else str(provider) 
                                       for _, provider, _ in ops)
                    success_rate = sum(1 for _, _, success in ops if success) / len(ops)
                    logger.info(f"  {operation}: {len(ops)} ops, {success_rate:.1%} success, providers: {', '.join(providers_used)}")
        
        # Display top opportunities
        if results.top_opportunities:
            logger.info(f"Top {min(3, len(results.top_opportunities))} Opportunities:")
            for i, opportunity in enumerate(results.top_opportunities[:3], 1):
                logger.info(f"  {i}. {opportunity.symbol}")
                logger.info(f"     Score: {opportunity.total_score}")
                logger.info(f"     Underlying: ${opportunity.underlying_price}")
                if opportunity.analysis.risk_metrics:
                    logger.info(f"     Max Profit: ${opportunity.analysis.risk_metrics.max_profit}")
                    logger.info(f"     Risk/Reward: {opportunity.analysis.risk_metrics.risk_reward_ratio}")
        
        # Test single symbol scan
        logger.info("Testing single symbol scan...")
        symbol_candidates = scanner.scan_symbol("AAPL", scan_config)
        logger.info(f"Found {len(symbol_candidates)} PMCC candidates for AAPL")
        
        # Export results (files will include provider information)
        logger.info("Exporting results...")
        json_file = scanner.export_results(results, format="json")
        csv_file = scanner.export_results(results, format="csv")
        logger.info(f"Results exported to {json_file} and {csv_file}")
        
        logger.info("Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())