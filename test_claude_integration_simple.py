#!/usr/bin/env python3
"""
Simple Claude AI Integration Test

This test validates that Claude AI integration works correctly by:
1. Testing Claude API connectivity
2. Creating sample enhanced data
3. Running Claude analysis
4. Validating the response format and top 10 selection
"""

import os
import sys
import asyncio
import logging
from datetime import date, datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.claude_client import ClaudeClient
from src.models.api_models import (
    EnhancedStockData, StockQuote, FundamentalMetrics, 
    TechnicalIndicators, RiskMetrics, CalendarEvent
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_enhanced_data() -> List[EnhancedStockData]:
    """Create sample enhanced stock data for testing."""
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    enhanced_data = []
    
    for symbol in symbols:
        # Create sample quote
        quote = StockQuote(
            symbol=symbol,
            last=175.50 if symbol == 'AAPL' else (410.25 if symbol == 'MSFT' else 141.80),
            volume=50000000,
            change=2.50,
            change_percent=1.45,
            high=178.00 if symbol == 'AAPL' else (415.00 if symbol == 'MSFT' else 145.20),
            low=173.25 if symbol == 'AAPL' else (407.50 if symbol == 'MSFT' else 139.60),
            open=174.00 if symbol == 'AAPL' else (409.00 if symbol == 'MSFT' else 140.50),
            previous_close=173.00 if symbol == 'AAPL' else (407.75 if symbol == 'MSFT' else 139.30),
            market_cap=2700000000000 if symbol == 'AAPL' else (3100000000000 if symbol == 'MSFT' else 1750000000000),
            timestamp=datetime.now()
        )
        
        # Create sample fundamentals
        from decimal import Decimal
        fundamentals = FundamentalMetrics(
            symbol=symbol,
            pe_ratio=Decimal('28.5') if symbol == 'AAPL' else (Decimal('32.1') if symbol == 'MSFT' else Decimal('25.8')),
            roe=Decimal('160.0') if symbol == 'AAPL' else (Decimal('38.2') if symbol == 'MSFT' else Decimal('18.1')),
            debt_to_equity=Decimal('1.73') if symbol == 'AAPL' else (Decimal('0.35') if symbol == 'MSFT' else Decimal('0.12')),
            profit_margin=Decimal('25.31') if symbol == 'AAPL' else (Decimal('36.69') if symbol == 'MSFT' else Decimal('22.47')),
            earnings_per_share=Decimal('6.16') if symbol == 'AAPL' else (Decimal('12.77') if symbol == 'MSFT' else Decimal('5.61')),
            book_value_per_share=Decimal('4.43') if symbol == 'AAPL' else (Decimal('13.79') if symbol == 'MSFT' else Decimal('27.25')),
            revenue_growth_rate=Decimal('0.02') if symbol == 'AAPL' else (Decimal('0.17') if symbol == 'MSFT' else Decimal('0.15')),
            earnings_growth_rate=Decimal('0.11') if symbol == 'AAPL' else (Decimal('0.27') if symbol == 'MSFT' else Decimal('0.42'))
        )
        
        # Create sample technical indicators
        technical = TechnicalIndicators(
            symbol=symbol,
            beta=Decimal('1.32') if symbol == 'AAPL' else (Decimal('0.89') if symbol == 'MSFT' else Decimal('1.05')),
            rsi_14d=Decimal('58.2') if symbol == 'AAPL' else (Decimal('61.8') if symbol == 'MSFT' else Decimal('65.3')),
            sma_50d=Decimal('180.25') if symbol == 'AAPL' else (Decimal('420.15') if symbol == 'MSFT' else Decimal('145.60')),
            sma_200d=Decimal('178.90') if symbol == 'AAPL' else (Decimal('405.25') if symbol == 'MSFT' else Decimal('135.20')),
            sector='Technology',
            industry=f'{symbol} Industry',
            avg_volume_30d=50000000
        )
        
        # Create sample risk metrics
        risk = RiskMetrics(
            symbol=symbol,
            institutional_ownership=Decimal('59.0') if symbol == 'AAPL' else (Decimal('72.8') if symbol == 'MSFT' else Decimal('81.2')),
            analyst_rating_avg=Decimal('2.1') if symbol == 'AAPL' else (Decimal('1.9') if symbol == 'MSFT' else Decimal('1.8')),
            analyst_count=25 if symbol == 'AAPL' else (30 if symbol == 'MSFT' else 22)
        )
        
        # Create sample calendar events
        calendar_events = [
            CalendarEvent(
                symbol=symbol,
                event_type='earnings',
                date=date(2024, 11, 15),
                announcement_time='after_market'
            )
        ]
        
        # Create enhanced stock data
        enhanced = EnhancedStockData(
            quote=quote,
            fundamentals=fundamentals,
            calendar_events=calendar_events,
            technical_indicators=technical,
            risk_metrics=risk,
            options_chain=None  # Not needed for this test
        )
        
        # Calculate completeness score
        enhanced.calculate_completeness_score()
        enhanced_data.append(enhanced)
    
    return enhanced_data


async def test_claude_connectivity():
    """Test Claude API connectivity."""
    logger.info("Testing Claude API connectivity...")
    
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key or claude_api_key.strip() == '' or claude_api_key == 'your_claude_api_key_here':
        logger.error("CLAUDE_API_KEY not configured")
        return False
    
    try:
        client = ClaudeClient(api_key=claude_api_key)
        health_check = await client.health_check()
        logger.info(f"Claude API health check: {'✅ PASSED' if health_check else '❌ FAILED'}")
        return health_check
    except Exception as e:
        logger.error(f"Claude API connectivity test failed: {e}")
        return False


async def test_claude_analysis():
    """Test Claude analysis with sample data."""
    logger.info("Testing Claude analysis...")
    
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        logger.error("CLAUDE_API_KEY not configured")
        return False
    
    try:
        # Initialize client
        client = ClaudeClient(api_key=claude_api_key)
        
        # Create sample enhanced data
        enhanced_data = create_sample_enhanced_data()
        logger.info(f"Created {len(enhanced_data)} enhanced stock records for analysis")
        
        # Create market context
        market_context = {
            'analysis_date': date.today().isoformat(),
            'total_opportunities': len(enhanced_data),
            'market_sentiment': 'neutral',
            'volatility_regime': 'testing'
        }
        
        # Run analysis
        start_time = datetime.now()
        try:
            response = await client.analyze_pmcc_opportunities(enhanced_data, market_context)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Claude analysis completed in {duration:.2f} seconds")
            
            if not response.is_success:
                logger.error(f"Claude analysis failed: {response.error}")
                if response.error:
                    logger.error(f"Error details: {response.error}")
                return False
        except Exception as e:
            logger.error(f"Exception during Claude analysis: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
        if not response.data:
            logger.error("No analysis data returned")
            return False
        
        analysis = response.data
        logger.info(f"Analysis successful:")
        logger.info(f"  - Opportunities analyzed: {len(analysis.opportunities)}")
        logger.info(f"  - Model used: {analysis.model_used}")
        logger.info(f"  - Input tokens: {analysis.input_tokens}")
        logger.info(f"  - Output tokens: {analysis.output_tokens}")
        logger.info(f"  - Market assessment: {analysis.market_assessment[:100] if analysis.market_assessment else 'None'}...")
        
        # Debug the first opportunity in detail
        if analysis.opportunities:
            first_opp = analysis.opportunities[0]
            logger.info(f"First opportunity details:")
            logger.info(f"  Type: {type(first_opp)}")
            logger.info(f"  Attributes: {dir(first_opp)}")
            logger.info(f"  Symbol: {getattr(first_opp, 'symbol', 'MISSING')}")
            logger.info(f"  Score: {getattr(first_opp, 'score', 'MISSING')} (type: {type(getattr(first_opp, 'score', None))})")
            logger.info(f"  Confidence: {getattr(first_opp, 'confidence', 'MISSING')} (type: {type(getattr(first_opp, 'confidence', None))})")
        
        # Validate top 10 selection
        if len(analysis.opportunities) > 10:
            logger.warning(f"Too many opportunities returned: {len(analysis.opportunities)}")
            return False
        
        # Check that opportunities are properly scored
        for i, opp in enumerate(analysis.opportunities[:5], 1):
            logger.info(f"  {i}. {opp.symbol}: Score {opp.score}, Confidence {opp.confidence}%")
        
        # Debug: Check scores and confidence values
        logger.info("Debugging scores and confidence values:")
        for i, opp in enumerate(analysis.opportunities):
            logger.info(f"  Opp {i}: {opp.symbol}, Score: {opp.score} (type: {type(opp.score)}), Confidence: {opp.confidence} (type: {type(opp.confidence)})")
        
        # Validate required fields
        required_checks = [
            (len(analysis.opportunities) > 0, "No opportunities returned"),
            (analysis.market_assessment, "No market assessment"),
            (analysis.model_used, "No model information"),
            (all(opp.symbol for opp in analysis.opportunities), "Missing symbols"),
            (all(getattr(opp, 'score', 0) > 0 for opp in analysis.opportunities), "Invalid scores"),
            (all(0 <= getattr(opp, 'confidence', -1) <= 100 for opp in analysis.opportunities), "Invalid confidence values")
        ]
        
        for check, message in required_checks:
            if not check:
                logger.error(f"Validation failed: {message}")
                return False
        
        logger.info("✅ All validations passed!")
        return True
        
    except Exception as e:
        logger.error(f"Claude analysis test failed: {e}")
        return False


async def main():
    """Run the simple Claude integration test."""
    print("=" * 60)
    print("SIMPLE CLAUDE AI INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Claude connectivity
    print("\n1. Testing Claude API Connectivity...")
    connectivity_success = await test_claude_connectivity()
    
    if not connectivity_success:
        print("❌ FAILED: Claude API not accessible")
        print("\nRecommendations:")
        print("- Check CLAUDE_API_KEY environment variable")
        print("- Verify API key is valid and has sufficient credits")
        return 1
    
    # Test 2: Claude analysis
    print("\n2. Testing Claude Analysis...")
    analysis_success = await test_claude_analysis()
    
    if not analysis_success:
        print("❌ FAILED: Claude analysis not working")
        print("\nRecommendations:")
        print("- Check Claude model configuration")
        print("- Review API limits and usage")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: Claude AI integration is working correctly!")
    print("✅ API connectivity: PASSED")
    print("✅ Analysis functionality: PASSED") 
    print("✅ Top 10 selection: PASSED")
    print("✅ Response validation: PASSED")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)