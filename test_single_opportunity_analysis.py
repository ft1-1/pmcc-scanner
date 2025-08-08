#!/usr/bin/env python3
"""
Test script for the new single opportunity Claude AI analysis feature.

This script demonstrates how the Claude AI integration now analyzes PMCC opportunities
one at a time instead of in batches, providing more focused analysis with 0-100 scoring.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.analysis.claude_integration import ClaudeIntegrationManager
from src.api.provider_factory import SyncDataProviderFactory
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_opportunity_data() -> Dict[str, Any]:
    """Create sample PMCC opportunity data for testing."""
    return {
        'symbol': 'AAPL',
        'underlying_price': 150.25,
        'pmcc_score': 78.5,
        'total_score': 78.5,
        'liquidity_score': 85.0,
        
        'strategy_details': {
            'net_debit': 1250.00,
            'credit_received': 325.00,
            'max_profit': 1575.00,
            'max_loss': 925.00,
            'breakeven_price': 162.50,
            'risk_reward_ratio': 1.70,
            'strategy_type': 'Poor_Mans_Covered_Call'
        },
        
        'leaps_option': {
            'option_symbol': 'AAPL250117C00130000',
            'strike': 130.00,
            'expiration': '2025-01-17',
            'dte': 365,
            'delta': 0.85,
            'gamma': 0.015,
            'theta': -0.25,
            'vega': 0.45,
            'iv': 22.5,
            'bid': 24.50,
            'ask': 25.10,
            'mid': 24.80,
            'last': 24.85,
            'volume': 125,
            'open_interest': 1850,
            'bid_size': 15,
            'ask_size': 12
        },
        
        'short_option': {
            'option_symbol': 'AAPL241215C00155000',
            'strike': 155.00,
            'expiration': '2024-12-15',
            'dte': 45,
            'delta': 0.25,
            'gamma': 0.035,
            'theta': -0.08,
            'vega': 0.15,
            'iv': 28.2,
            'bid': 3.20,
            'ask': 3.35,
            'mid': 3.28,
            'last': 3.25,
            'volume': 85,
            'open_interest': 420,
            'bid_size': 8,
            'ask_size': 10
        }
    }


def create_sample_enhanced_stock_data() -> Dict[str, Any]:
    """Create sample enhanced EODHD stock data for testing."""
    return {
        'fundamentals': {
            'market_cap': 2350000000000,  # $2.35T
            'pe_ratio': 28.5,
            'roe': 15.2,
            'profit_margin': 23.8,
            'debt_to_equity': 0.45,
            'revenue_growth': 8.5,
            'eps_growth': 12.3
        },
        
        'calendar_events': {
            'next_earnings_date': '2024-02-01',
            'next_ex_dividend_date': '2024-02-15',
            'dividend_yield': 0.52,
            'upcoming_events': [
                {'date': '2024-02-01', 'event': 'Earnings Release'},
                {'date': '2024-02-15', 'event': 'Ex-Dividend Date'}
            ]
        },
        
        'technical_indicators': {
            'rsi': 62.5,
            'macd': 1.25,
            'sma_20': 148.75,
            'sma_50': 145.20,
            'beta': 1.15,
            'support_level': 142.50,
            'resistance_level': 158.00
        },
        
        'news_sentiment': {
            'sentiment_score': 0.35,  # Positive sentiment
            'news_count': 15,
            'analyst_rating': 'Buy'
        },
        
        'live_price_data': {
            'current_price': 150.25,
            'day_change_percent': 1.2,
            'high_52_week': 198.23,
            'low_52_week': 124.17,
            'avg_volume': 58500000
        },
        
        'earnings_data': {
            'next_earnings_date': '2024-02-01',
            'eps_estimate': 2.45,
            'revenue_estimate': 123500000000
        },
        
        'historical_data': {
            'price_history': [145.20, 147.80, 149.50, 150.25],
            'volatility_30d': 0.285
        },
        
        'economic_events': {
            'upcoming_events': [
                {'date': '2024-01-31', 'event': 'FOMC Meeting'},
                {'date': '2024-02-02', 'event': 'Jobs Report'}
            ]
        }
    }


async def test_single_opportunity_analysis():
    """Test the new single opportunity Claude analysis feature."""
    logger.info("Testing single opportunity Claude AI analysis")
    
    try:
        # Load settings
        settings = get_settings()
        
        # Check if Claude is configured
        if not settings.claude_api_key:
            logger.error("Claude API key not configured. Please set CLAUDE_API_KEY environment variable.")
            return
        
        # Create provider factory and get Claude provider
        provider_factory = SyncDataProviderFactory()
        claude_provider = provider_factory.get_claude_provider()
        
        if not claude_provider:
            logger.error("Claude provider not available")
            return
        
        # Check Claude provider health
        health = await claude_provider.health_check()
        logger.info(f"Claude provider health: {health.status}")
        
        if health.status.name != 'HEALTHY':
            logger.error(f"Claude provider not healthy: {health.error_message}")
            return
        
        # Create sample data
        opportunity_data = create_sample_opportunity_data()
        enhanced_stock_data = create_sample_enhanced_stock_data()
        market_context = {
            'volatility_regime': 'Medium',
            'interest_rate_trend': 'Rising',
            'market_sentiment': 'Bullish',
            'vix_level': 18.5
        }
        
        logger.info(f"Analyzing opportunity: {opportunity_data['symbol']}")
        logger.info(f"Original PMCC score: {opportunity_data['pmcc_score']}")
        
        # Initialize integration manager
        integration_manager = ClaudeIntegrationManager()
        
        # Test single opportunity analysis
        analyzed_opportunity = await integration_manager.analyze_single_opportunity_with_claude(
            opportunity_data=opportunity_data,
            enhanced_stock_data=enhanced_stock_data,
            claude_provider=claude_provider,
            market_context=market_context
        )
        
        # Display results
        logger.info("=== ANALYSIS RESULTS ===")
        logger.info(f"Symbol: {analyzed_opportunity['symbol']}")
        logger.info(f"Original PMCC Score: {analyzed_opportunity.get('pmcc_score', 'N/A')}")
        logger.info(f"Claude Score: {analyzed_opportunity.get('claude_score', 'N/A')}")
        logger.info(f"Combined Score: {analyzed_opportunity.get('combined_score', 'N/A')}")
        logger.info(f"Claude Analyzed: {analyzed_opportunity.get('claude_analyzed', False)}")
        logger.info(f"Recommendation: {analyzed_opportunity.get('claude_recommendation', 'N/A')}")
        logger.info(f"Confidence: {analyzed_opportunity.get('claude_confidence', 0)}%")
        
        if analyzed_opportunity.get('claude_analyzed'):
            logger.info("\n=== CLAUDE ANALYSIS SUMMARY ===")
            logger.info(analyzed_opportunity.get('claude_analysis_summary', 'No summary available'))
            
            logger.info("\n=== SCORE BREAKDOWN ===")
            breakdown = analyzed_opportunity.get('claude_scores_breakdown', {})
            logger.info(f"Risk Score: {breakdown.get('risk_score', 0)}/25")
            logger.info(f"Fundamental Score: {breakdown.get('fundamental_score', 0)}/25")
            logger.info(f"Technical Score: {breakdown.get('technical_score', 0)}/20")
            logger.info(f"Calendar Score: {breakdown.get('calendar_score', 0)}/15")
            logger.info(f"Strategy Score: {breakdown.get('strategy_score', 0)}/15")
            
            logger.info("\n=== KEY INSIGHTS ===")
            insights = analyzed_opportunity.get('ai_insights', {})
            strengths = insights.get('key_strengths', [])
            risks = insights.get('key_risks', [])
            
            if strengths:
                logger.info("Strengths:")
                for strength in strengths:
                    logger.info(f"  • {strength}")
            
            if risks:
                logger.info("Risks:")
                for risk in risks:
                    logger.info(f"  • {risk}")
            
            logger.info(f"\nProfit Probability: {insights.get('profit_probability', 0)}%")
            logger.info(f"Early Assignment Risk: {insights.get('early_assignment_risk', 'Unknown')}")
            logger.info(f"Optimal Management: {insights.get('optimal_management', 'N/A')}")
        
        # Display integration stats
        stats = integration_manager.get_integration_stats()
        logger.info("\n=== INTEGRATION STATISTICS ===")
        logger.info(f"Total Analyses: {stats['total_analyses']}")
        logger.info(f"Successful Analyses: {stats['successful_analyses']}")
        logger.info(f"Success Rate: {stats['success_rate']:.1%}")
        
        logger.info("\nSingle opportunity Claude analysis test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in single opportunity analysis test: {e}")
        raise


async def test_batch_individual_analysis():
    """Test analyzing multiple opportunities individually."""
    logger.info("Testing batch individual Claude analysis")
    
    try:
        # Load settings
        settings = get_settings()
        
        if not settings.claude_api_key:
            logger.error("Claude API key not configured")
            return
        
        # Create provider factory and get Claude provider
        provider_factory = SyncDataProviderFactory()
        claude_provider = provider_factory.get_claude_provider()
        
        if not claude_provider:
            logger.error("Claude provider not available")
            return
        
        # Create multiple sample opportunities
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        opportunities = []
        enhanced_data_lookup = {}
        
        for symbol in symbols:
            opp_data = create_sample_opportunity_data()
            opp_data['symbol'] = symbol
            opp_data['pmcc_score'] = 75.0 + (hash(symbol) % 20)  # Vary scores
            opportunities.append(opp_data)
            
            enhanced_data_lookup[symbol] = create_sample_enhanced_stock_data()
        
        logger.info(f"Analyzing {len(opportunities)} opportunities individually")
        
        # Initialize integration manager
        integration_manager = ClaudeIntegrationManager()
        
        # Test batch individual analysis
        analyzed_opportunities = await integration_manager.analyze_opportunities_individually(
            opportunities=opportunities,
            enhanced_stock_data_lookup=enhanced_data_lookup,
            claude_provider=claude_provider,
            max_concurrent=2  # Limit concurrent calls for testing
        )
        
        # Display results
        logger.info(f"\n=== BATCH ANALYSIS RESULTS ({len(analyzed_opportunities)} opportunities) ===")
        
        for i, opp in enumerate(analyzed_opportunities, 1):
            logger.info(f"\n{i}. {opp['symbol']}:")
            logger.info(f"   Original Score: {opp.get('pmcc_score', 'N/A')}")
            logger.info(f"   Claude Score: {opp.get('claude_score', 'N/A')}")
            logger.info(f"   Combined Score: {opp.get('combined_score', 'N/A')}")
            logger.info(f"   Recommendation: {opp.get('claude_recommendation', 'N/A')}")
            logger.info(f"   Analyzed: {opp.get('claude_analyzed', False)}")
        
        # Display final stats
        stats = integration_manager.get_integration_stats()
        logger.info(f"\n=== FINAL STATISTICS ===")
        logger.info(f"Total Analyses: {stats['total_analyses']}")
        logger.info(f"Successful Analyses: {stats['successful_analyses']}")
        logger.info(f"Success Rate: {stats['success_rate']:.1%}")
        
        logger.info("Batch individual analysis test completed!")
        
    except Exception as e:
        logger.error(f"Error in batch individual analysis test: {e}")
        raise


async def main():
    """Main test function."""
    logger.info("Starting Claude AI single opportunity analysis tests")
    
    try:
        # Test single opportunity analysis
        await test_single_opportunity_analysis()
        
        # Test batch individual analysis
        await test_batch_individual_analysis()
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())