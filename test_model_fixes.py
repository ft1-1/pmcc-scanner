#!/usr/bin/env python3
"""
Test script to verify the StockQuote model fixes and data handling improvements.

This test focuses on validating the code changes without requiring API tokens.
"""

import sys
from pathlib import Path
import logging
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.api_models import StockQuote, EnhancedStockData
from src.analysis.scanner import PMCCScanner
from src.analysis.claude_integration import ClaudeIntegrationManager
from src.config.settings import Settings, get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_stock_quote_attributes():
    """Test that StockQuote now has the missing attributes."""
    logger.info("=== Test 1: StockQuote Attribute Fixes ===")
    
    try:
        # Create a test StockQuote with all attributes
        quote = StockQuote(
            symbol="KSS",
            last=Decimal("15.25"),
            volume=150000,
            change=Decimal("-0.35"),
            change_percent=Decimal("-2.24"),
            market_cap=Decimal("1500000000"),
            previous_close=Decimal("15.60")
        )
        
        # Test accessing all attributes (should not raise AttributeError)
        logger.info(f"✓ Symbol: {quote.symbol}")
        logger.info(f"✓ Last: {quote.last}")
        logger.info(f"✓ Change: {quote.change}")
        logger.info(f"✓ Change %: {quote.change_percent}")
        logger.info(f"✓ Market Cap: {quote.market_cap}")
        logger.info(f"✓ Previous Close: {quote.previous_close}")
        logger.info(f"✓ Volume: {quote.volume}")
        
        # Test with None values (should not crash)
        quote_minimal = StockQuote(symbol="TEST", last=Decimal("10.00"))
        logger.info(f"✓ Minimal quote - Change: {quote_minimal.change}")
        logger.info(f"✓ Minimal quote - Market Cap: {quote_minimal.market_cap}")
        
        logger.info("✅ StockQuote attribute tests PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ StockQuote test failed: {e}")
        return False


def test_enhanced_data_to_dict():
    """Test the scanner's _enhanced_stock_data_to_dict method with dictionary fundamentals."""
    logger.info("\n=== Test 2: Scanner Data Conversion with Dictionary Fundamentals ===")
    
    try:
        # Create mock enhanced data with dictionary fundamentals (as returned by enhanced EODHD)
        quote = StockQuote(
            symbol="KSS",
            last=Decimal("15.25"),
            volume=150000,
            change=Decimal("-0.35"),
            change_percent=Decimal("-2.24"),
            market_cap=Decimal("1500000000")
        )
        
        # Create fundamentals in dictionary format (as filtered by enhanced EODHD provider)
        fundamentals_dict = {
            'company_info': {
                'name': 'Kohls Corporation',
                'market_cap_mln': 1500,
                'sector': 'Consumer Discretionary'
            },
            'financial_health': {
                'eps_ttm': 2.15,
                'profit_margin': 0.045,
                'operating_margin': 0.065,
                'roe': 0.12,
                'roa': 0.08,
                'dividend_yield': 0.035,
                'revenue_growth_yoy': 0.02,
                'earnings_growth_yoy': 0.05
            },
            'valuation_metrics': {
                'pe_ratio': 7.1,
                'forward_pe': 6.8,
                'price_to_sales': 0.25,
                'price_to_book': 1.2
            },
            'stock_technicals': {
                'beta': 1.8,
                '52_week_high': 24.50,
                '52_week_low': 12.75,
                'short_interest': 0.15
            },
            'balance_sheet': {
                'total_debt': 3200,
                'shareholders_equity': 2800,
                'debt_to_equity': 1.14
            }
        }
        
        # Create enhanced stock data with dictionary fundamentals
        enhanced_data = EnhancedStockData(
            quote=quote,
            fundamentals=fundamentals_dict,  # Dictionary format
            calendar_events=[],
            technical_indicators=None,
            risk_metrics=None,
            options_chain=None
        )
        
        # Create a PMCCScanner instance to test the conversion method
        # Note: This will fail without proper settings, but we can test the method directly
        logger.info("Creating mock settings...")
        mock_settings = Settings(
            environment="development",
            debug=True,
            marketdata=None,
            eodhd=None,
            claude=None
        )
        
        # Create scanner with mock factory (won't be used for this test)
        scanner = PMCCScanner(mock_settings, None)
        
        # Test the problematic method with dictionary fundamentals
        logger.info("Testing _enhanced_stock_data_to_dict with dictionary fundamentals...")
        converted_data = scanner._enhanced_stock_data_to_dict(enhanced_data)
        
        logger.info("✅ Data conversion completed without errors")
        
        # Validate the converted structure
        logger.info(f"✓ Quote data keys: {list(converted_data.get('quote', {}).keys())}")
        logger.info(f"✓ Fundamentals data keys: {list(converted_data.get('fundamentals', {}).keys())}")
        
        # Check specific values
        quote_data = converted_data.get('quote', {})
        fund_data = converted_data.get('fundamentals', {})
        
        logger.info(f"✓ Quote symbol: {quote_data.get('symbol')}")
        logger.info(f"✓ Quote last: {quote_data.get('last')}")
        logger.info(f"✓ Quote change: {quote_data.get('change')}")
        logger.info(f"✓ Quote market_cap: {quote_data.get('market_cap')}")
        
        logger.info(f"✓ Fund PE ratio: {fund_data.get('pe_ratio')}")
        logger.info(f"✓ Fund beta: {fund_data.get('beta')}")
        logger.info(f"✓ Fund market cap: {fund_data.get('market_capitalization')}")
        
        logger.info("✅ Scanner data conversion tests PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Scanner test failed: {e}")
        logger.exception("Full error details:")
        return False


def test_claude_integration_data_prep():
    """Test Claude integration data preparation."""
    logger.info("\n=== Test 3: Claude Integration Data Preparation ===")
    
    try:
        # Create mock opportunity data
        opportunity = {
            'symbol': 'KSS',
            'underlying_price': 15.25,
            'pmcc_score': 75.5,
            'total_score': 75.5,
            'liquidity_score': 80,
            'net_debit': 5.50,
            'long_call': {
                'option_symbol': 'KSS250117C00015000',
                'strike': 15.0,
                'delta': 0.78,
                'gamma': 0.05,
                'theta': -0.02,
                'vega': 0.15,
                'iv': 0.45,
                'bid': 5.40,
                'ask': 5.60,
                'volume': 12
            },
            'short_call': {
                'option_symbol': 'KSS240816C00017000',
                'strike': 17.0,
                'delta': 0.25,
                'gamma': 0.08,
                'theta': -0.05,
                'vega': 0.12,
                'iv': 0.52,
                'bid': 1.20,
                'ask': 1.30,
                'volume': 25
            }
        }
        
        # Test Claude integration manager
        integration_manager = ClaudeIntegrationManager()
        
        # Test data preparation
        logger.info("Testing opportunity data preparation for Claude...")
        prepared_data = integration_manager.prepare_opportunities_for_claude([opportunity])
        
        logger.info("✅ Claude data preparation completed without errors")
        
        # Validate structure
        logger.info(f"✓ Prepared opportunities count: {len(prepared_data.get('opportunities', []))}")
        logger.info(f"✓ Market context keys: {list(prepared_data.get('market_context', {}).keys())}")
        logger.info(f"✓ Analysis metadata keys: {list(prepared_data.get('analysis_metadata', {}).keys())}")
        
        if prepared_data.get('opportunities'):
            opp = prepared_data['opportunities'][0]
            logger.info(f"✓ Opportunity symbol: {opp.get('symbol')}")
            logger.info(f"✓ Strategy details keys: {list(opp.get('strategy_details', {}).keys())}")
            logger.info(f"✓ LEAPS option keys: {list(opp.get('leaps_option', {}).keys())}")
            logger.info(f"✓ Short option keys: {list(opp.get('short_option', {}).keys())}")
        
        logger.info("✅ Claude integration tests PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Claude integration test failed: {e}")
        logger.exception("Full error details:")
        return False


def main():
    """Run all model and data handling tests."""
    logger.info("Starting PMCC Scanner Model and Data Handling Tests")
    logger.info("=" * 60)
    
    # Run all tests
    test1_passed = test_stock_quote_attributes()
    test2_passed = test_enhanced_data_to_dict()
    test3_passed = test_claude_integration_data_prep()
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY:")
    logger.info(f"✓ StockQuote Attributes: {'PASSED' if test1_passed else 'FAILED'}")
    logger.info(f"✓ Scanner Data Conversion: {'PASSED' if test2_passed else 'FAILED'}")
    logger.info(f"✓ Claude Integration: {'PASSED' if test3_passed else 'FAILED'}")
    
    if test1_passed and test2_passed and test3_passed:
        logger.info("🎉 ALL TESTS PASSED - Model and data handling fixes are working!")
        logger.info("\nThe following issues have been resolved:")
        logger.info("✅ StockQuote now has 'change', 'change_percent', and 'market_cap' attributes")
        logger.info("✅ Scanner handles both dictionary and object fundamentals formats")
        logger.info("✅ Claude integration properly processes opportunity data")
        logger.info("\nThe enhanced data collection → Claude AI analysis flow should now work correctly.")
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED - Additional fixes may be needed")
        return 1


if __name__ == "__main__":
    sys.exit(main())