#!/usr/bin/env python3
"""
Simple test script to validate Claude AI integration.

This script tests the Claude API integration without requiring a full PMCC scan.
It validates configuration, API connectivity, and basic functionality.
"""

import sys
import os
import logging
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import get_settings
from src.api.providers.claude_provider import ClaudeProvider
from src.api.data_provider import ProviderType
from src.models.api_models import EnhancedStockData, StockQuote, FundamentalMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_claude_configuration():
    """Test Claude configuration and setup."""
    logger.info("Testing Claude configuration...")
    
    try:
        settings = get_settings()
        if not settings.claude or not settings.claude.is_configured:
            logger.error("Claude is not configured. Please set CLAUDE_API_KEY environment variable.")
            return False
        
        logger.info(f"Claude configured with model: {settings.claude.model}")
        logger.info(f"Max tokens: {settings.claude.max_tokens}")
        logger.info(f"Daily cost limit: ${settings.claude.daily_cost_limit}")
        return True
        
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


def test_claude_provider_creation():
    """Test Claude provider creation."""
    logger.info("Testing Claude provider creation...")
    
    try:
        settings = get_settings()
        if not settings.claude:
            logger.error("Claude not configured")
            return False
        
        config = {
            'api_key': settings.claude.api_key,
            'model': settings.claude.model,
            'max_tokens': settings.claude.max_tokens,
            'temperature': settings.claude.temperature,
            'timeout': settings.claude.timeout_seconds,
            'max_retries': settings.claude.max_retries,
            'daily_cost_limit': settings.claude.daily_cost_limit
        }
        
        provider = ClaudeProvider(ProviderType.CLAUDE, config)
        logger.info("Claude provider created successfully")
        
        # Test provider info
        info = provider.get_provider_info()
        logger.info(f"Provider info: {info}")
        
        return provider
        
    except Exception as e:
        logger.error(f"Provider creation test failed: {e}")
        return False


def create_mock_enhanced_stock_data():
    """Create mock enhanced stock data for testing."""
    
    # Create mock stock quote
    quote = StockQuote(
        symbol="AAPL",
        last=150.00,
        volume=50000000
    )
    
    # Create mock fundamentals
    fundamentals = FundamentalMetrics(
        symbol="AAPL",
        pe_ratio=25.5,
        roe=30.2,
        profit_margin=25.1,
        debt_to_equity=1.5,
        earnings_per_share=6.15
    )
    
    # Create enhanced stock data
    enhanced_data = EnhancedStockData(
        quote=quote,
        fundamentals=fundamentals
    )
    
    # Calculate completeness score
    enhanced_data.calculate_completeness_score()
    
    return [enhanced_data]


async def test_claude_health_check(provider):
    """Test Claude provider health check."""
    logger.info("Testing Claude health check...")
    
    try:
        health = await provider.health_check()
        logger.info(f"Health check result: {health.status.value}")
        logger.info(f"Latency: {health.latency_ms}ms")
        
        if health.error_message:
            logger.warning(f"Health check warning: {health.error_message}")
        
        return health.status.value == "healthy"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def test_claude_analysis(provider):
    """Test Claude AI analysis with mock data."""
    logger.info("Testing Claude AI analysis...")
    
    try:
        # Create mock data
        enhanced_stock_data = create_mock_enhanced_stock_data()
        
        # Test analysis
        response = await provider.analyze_pmcc_opportunities(
            enhanced_stock_data=enhanced_stock_data,
            market_context={
                'volatility_regime': 'Normal',
                'market_sentiment': 'Neutral',
                'interest_rate_trend': 'Rising'
            }
        )
        
        if not response.is_success:
            logger.error(f"Analysis failed: {response.error}")
            return False
        
        analysis = response.data
        logger.info(f"Analysis completed successfully")
        logger.info(f"Number of opportunities analyzed: {len(analysis.opportunities)}")
        logger.info(f"Processing time: {analysis.processing_time_ms}ms")
        logger.info(f"Market assessment: {analysis.market_assessment}")
        
        if analysis.opportunities:
            top_opp = analysis.opportunities[0]
            logger.info(f"Top opportunity: {top_opp.symbol} - Score: {top_opp.score}")
            logger.info(f"Reasoning: {top_opp.reasoning}")
        
        return True
        
    except Exception as e:
        logger.error(f"Analysis test failed: {e}")
        return False


def test_rate_limit_estimation(provider):
    """Test rate limit and cost estimation."""
    logger.info("Testing rate limit and cost estimation...")
    
    try:
        # Test rate limit info
        rate_limit = provider.get_rate_limit_info()
        if rate_limit:
            logger.info(f"Rate limit - Limit: {rate_limit.limit}, Remaining: {rate_limit.remaining}")
        
        # Test cost estimation
        cost = provider.estimate_credits_required(
            "analyze_pmcc_opportunities", 
            enhanced_stock_data=[None] * 10  # Mock 10 stocks
        )
        logger.info(f"Estimated cost for 10 stocks: {cost} cents")
        
        return True
        
    except Exception as e:
        logger.error(f"Rate limit test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting Claude AI integration tests...")
    
    # Test configuration
    if not test_claude_configuration():
        logger.error("Configuration test failed. Exiting.")
        sys.exit(1)
    
    # Test provider creation
    provider = test_claude_provider_creation()
    if not provider:
        logger.error("Provider creation test failed. Exiting.")
        sys.exit(1)
    
    # Test rate limiting
    if not test_rate_limit_estimation(provider):
        logger.warning("Rate limit test failed, but continuing...")
    
    # Test health check
    if not await test_claude_health_check(provider):
        logger.error("Health check failed. Exiting.")
        sys.exit(1)
    
    # Test analysis (this uses API credits, so run carefully)
    logger.info("About to test Claude analysis - this will use API credits.")
    user_input = input("Continue with analysis test? (y/N): ")
    
    if user_input.lower() == 'y':
        if not await test_claude_analysis(provider):
            logger.error("Analysis test failed.")
            sys.exit(1)
    else:
        logger.info("Skipping analysis test.")
    
    logger.info("All tests completed successfully!")


if __name__ == "__main__":
    import asyncio
    
    # Check if Claude API key is set
    if not os.getenv('CLAUDE_API_KEY'):
        print("ERROR: CLAUDE_API_KEY environment variable is not set.")
        print("Please set your Claude API key:")
        print("export CLAUDE_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    asyncio.run(main())