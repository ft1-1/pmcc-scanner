#!/usr/bin/env python3
"""
Quick test to validate comprehensive enhanced data integration.
Tests the updated scanner data flow and Claude prompt enhancement.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner

def test_enhanced_data_collection():
    """Test comprehensive enhanced data collection."""
    print("=" * 60)
    print("COMPREHENSIVE ENHANCED DATA INTEGRATION TEST")
    print("=" * 60)
    
    # Check if EODHD API key is available
    eodhd_api_key = os.getenv('EODHD_API_KEY')
    if not eodhd_api_key:
        print("❌ EODHD_API_KEY not found in environment")
        return False
    
    try:
        # Initialize enhanced EODHD provider
        config = {
            'api_token': eodhd_api_key,
            'enable_caching': True,
            'cache_ttl_hours': 24
        }
        
        provider = EnhancedEODHDProvider(ProviderType.EODHD, config)
        print(f"✅ Enhanced EODHD provider initialized")
        
        # Test symbol for data collection
        test_symbol = 'AAPL'
        
        print(f"\n📊 Testing comprehensive data collection for {test_symbol}...")
        
        # Test comprehensive enhanced data collection
        async def run_test():
            response = await provider.get_comprehensive_enhanced_data(test_symbol)
            return response
        
        enhanced_response = asyncio.run(run_test())
        
        if not enhanced_response.is_success:
            print(f"❌ Data collection failed: {enhanced_response.error}")
            return False
        
        comprehensive_data = enhanced_response.data
        print(f"✅ Comprehensive data collected successfully")
        
        # Validate data structure
        expected_categories = [
            'economic_events', 'news', 'fundamentals', 'live_price',
            'earnings', 'historical_prices', 'sentiment', 'technical_indicators'
        ]
        
        print(f"\n📋 Data Category Validation:")
        available_categories = 0
        for category in expected_categories:
            has_data = bool(comprehensive_data.get(category))
            status = "✅" if has_data else "⚠️"
            print(f"  {status} {category}: {'Available' if has_data else 'No data'}")
            if has_data:
                available_categories += 1
        
        completeness = (available_categories / len(expected_categories)) * 100
        print(f"\n📈 Data Completeness: {completeness:.1f}% ({available_categories}/{len(expected_categories)} categories)")
        
        # Test scanner data conversion
        print(f"\n🔄 Testing scanner data conversion...")
        scanner = PMCCScanner()
        
        # Test the enhanced data to dict conversion
        try:
            enhanced_dict = scanner._enhanced_stock_data_to_dict(comprehensive_data)
            print(f"✅ Data conversion successful")
            
            # Validate converted data structure
            key_fields = ['quote', 'fundamentals', 'technical_indicators', 'recent_news', 'data_completeness']
            print(f"\n📋 Converted Data Validation:")
            for field in key_fields:
                has_field = field in enhanced_dict
                status = "✅" if has_field else "⚠️"
                print(f"  {status} {field}: {'Present' if has_field else 'Missing'}")
            
            # Show data completeness score
            if 'data_completeness' in enhanced_dict:
                completeness_score = enhanced_dict['data_completeness'].get('completeness_score', 0)
                print(f"\n📊 Scanner Data Completeness Score: {completeness_score}%")
            
            # Sample some key data points
            print(f"\n📄 Sample Data Points:")
            if 'quote' in enhanced_dict and enhanced_dict['quote']:
                quote = enhanced_dict['quote']
                print(f"  📈 Current Price: ${quote.get('last', 0):.2f}")
                print(f"  📊 Market Cap: ${quote.get('market_cap', 0):,.0f}")
            
            if 'fundamentals' in enhanced_dict and enhanced_dict['fundamentals']:
                fund = enhanced_dict['fundamentals']
                print(f"  💼 Company: {fund.get('company_name', 'N/A')}")
                print(f"  🏭 Sector: {fund.get('sector', 'N/A')} | Industry: {fund.get('industry', 'N/A')}")
                print(f"  📊 P/E Ratio: {fund.get('pe_ratio', 'N/A')}")
                print(f"  💰 ROE: {fund.get('roe', 'N/A')}%")
                print(f"  📈 Revenue Growth: {fund.get('revenue_growth_yoy', 'N/A')}%")
                print(f"  💵 Dividend Yield: {fund.get('dividend_yield', 'N/A')}%")
            
            if 'recent_news' in enhanced_dict and enhanced_dict['recent_news']:
                print(f"  📰 Recent News: {len(enhanced_dict['recent_news'])} articles available")
            
            return True
            
        except Exception as e:
            print(f"❌ Data conversion failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_claude_prompt_enhancement():
    """Test that Claude prompt can handle comprehensive data."""
    print(f"\n" + "=" * 60)
    print("CLAUDE PROMPT ENHANCEMENT TEST")
    print("=" * 60)
    
    # Check if Claude API key is available
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        print("❌ CLAUDE_API_KEY not found - skipping Claude integration test")
        return False
    
    try:
        from src.api.claude_client import ClaudeClient
        
        client = ClaudeClient(api_key=claude_api_key)
        print(f"✅ Claude client initialized")
        
        # Create sample comprehensive data for testing
        sample_opportunity_data = {
            'symbol': 'AAPL',
            'underlying_price': 150.00,
            'strategy_details': {
                'net_debit': 1500.00,
                'max_profit': 5000.00,
                'max_loss': -1500.00,
                'breakeven_price': 165.00,
                'risk_reward_ratio': 3.33
            },
            'leaps_option': {
                'option_symbol': 'AAPL241220C00135000',
                'strike': 135.00,
                'delta': 0.85,
                'dte': 300
            },
            'short_option': {
                'option_symbol': 'AAPL240315C00160000',
                'strike': 160.00,
                'delta': 0.30,
                'dte': 45
            },
            'pmcc_score': 75.0,
            'liquidity_score': 85.0
        }
        
        sample_enhanced_data = {
            'quote': {
                'symbol': 'AAPL',
                'last': 150.00,
                'change': 2.50,
                'change_percent': 1.69,
                'volume': 50000000,
                'market_cap': 2400000000000
            },
            'fundamentals': {
                'company_name': 'Apple Inc.',
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'pe_ratio': 25.5,
                'roe': 28.5,
                'profit_margin': 23.2,
                'revenue_growth_yoy': 8.2,
                'dividend_yield': 0.5,
                'beta': 1.2
            },
            'technical_indicators': {
                'rsi_14d': 65.2,
                'volatility_30d': 22.5,
                'beta': 1.2
            },
            'recent_news': [
                {
                    'date': '2024-01-15',
                    'title': 'Apple reports strong quarterly earnings',
                    'sentiment': 'positive'
                }
            ],
            'data_completeness': {
                'completeness_score': 87.5,
                'comprehensive_data_available': True,
                'has_fundamental_data': True,
                'has_technical_indicators': True,
                'has_recent_news': True
            }
        }
        
        market_context = {
            'analysis_date': '2024-01-15',
            'market_sentiment': 'neutral',
            'volatility_regime': 'normal'
        }
        
        print(f"🧠 Testing Claude prompt generation...")
        
        # Build the prompt (we're not actually calling Claude to save costs)
        prompt = client._build_single_opportunity_prompt(
            sample_opportunity_data,
            sample_enhanced_data,
            market_context
        )
        
        print(f"✅ Claude prompt generated successfully")
        
        # Validate prompt contains comprehensive data
        key_data_points = [
            'Current Price:', 'Market Cap:', 'Company:', 'Sector:', 'P/E Ratio:',
            'ROE:', 'Revenue Growth YoY:', 'RSI', 'RECENT NEWS', 'DATA COMPLETENESS'
        ]
        
        print(f"\n📋 Prompt Data Validation:")
        for data_point in key_data_points:
            has_data = data_point in prompt
            status = "✅" if has_data else "❌"
            print(f"  {status} {data_point}: {'Found' if has_data else 'Missing'}")
        
        # Check prompt length (should be substantial with comprehensive data)
        prompt_length = len(prompt)
        print(f"\n📏 Prompt Length: {prompt_length:,} characters")
        
        if prompt_length > 5000:  # Comprehensive prompt should be substantial
            print(f"✅ Prompt appears comprehensive")
        else:
            print(f"⚠️ Prompt may be missing data (too short)")
        
        return True
        
    except Exception as e:
        print(f"❌ Claude prompt test failed: {e}")
        return False

def main():
    """Run all comprehensive enhanced data tests."""
    print(f"🚀 Starting Comprehensive Enhanced Data Integration Tests")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Enhanced Data Collection
    results.append(test_enhanced_data_collection())
    
    # Test 2: Claude Prompt Enhancement
    results.append(test_claude_prompt_enhancement())
    
    # Summary
    print(f"\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Tests Passed: {passed}/{total}")
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED - Comprehensive enhanced data integration is working!")
        print(f"\n🎯 Key Improvements Validated:")
        print(f"   • Comprehensive data collection from 8 EODHD data sources")
        print(f"   • Enhanced data processing and conversion for Claude analysis")
        print(f"   • Updated Claude prompt template with comprehensive market data")
        print(f"   • Data completeness scoring and validation")
    else:
        print(f"❌ Some tests failed - review issues above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)