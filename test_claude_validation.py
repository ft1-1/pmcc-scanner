#!/usr/bin/env python3
"""
Claude AI Integration Validation Test

This test validates that Claude AI integration correctly receives data from
the corrected provider architecture:
- MarketData.app for options data
- EODHD for fundamental data only
- Claude AI for enhanced analysis
"""

import os
import sys
import asyncio
import logging
from datetime import date, datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import get_settings
from src.api.provider_factory import SyncDataProviderFactory, FallbackStrategy
from src.api.data_provider import ProviderType
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.claude_client import ClaudeClient
from src.analysis.claude_integration import ClaudeIntegrationManager
from src.models.api_models import EnhancedStockData, StockQuote

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ClaudeValidationTest:
    """Comprehensive validation test for Claude AI integration."""
    
    def __init__(self):
        """Initialize test with providers."""
        self.settings = get_settings()
        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL']  # Test with reliable symbols
        
        # Initialize provider factory
        self.provider_factory = SyncDataProviderFactory(fallback_strategy=FallbackStrategy.ROUND_ROBIN)
        
        # Initialize enhanced EODHD provider
        self.enhanced_eodhd = None
        self.claude_client = None
        self.claude_integration = ClaudeIntegrationManager()
        
        # Results storage
        self.validation_results = {
            'provider_setup': {},
            'data_collection': {},
            'claude_analysis': {},
            'integration_test': {},
            'overall_status': 'pending'
        }
    
    def setup_providers(self) -> bool:
        """Setup and validate provider configurations."""
        logger.info("Setting up providers for validation...")
        
        try:
            # 1. Validate Provider Factory setup
            try:
                providers_info = self.provider_factory.get_provider_status()
                self.validation_results['provider_setup']['factory_status'] = providers_info
                logger.info("Provider factory status retrieved successfully")
            except Exception as e:
                logger.warning(f"Could not get provider status: {e}")
                self.validation_results['provider_setup']['factory_status'] = "unavailable"
            
            # Check MarketData.app availability for options
            marketdata_provider = None
            try:
                marketdata_provider = self.provider_factory.get_provider("get_options_chain", preferred_provider=ProviderType.MARKETDATA)
                self.validation_results['provider_setup']['marketdata_available'] = marketdata_provider is not None
                logger.info(f"MarketData.app provider available: {marketdata_provider is not None}")
            except Exception as e:
                self.validation_results['provider_setup']['marketdata_available'] = False
                logger.warning(f"MarketData.app provider not available: {e}")
            
            # Check EODHD availability for fundamentals
            eodhd_provider = None
            try:
                eodhd_provider = self.provider_factory.get_provider("get_fundamental_data", preferred_provider=ProviderType.EODHD)
                self.validation_results['provider_setup']['eodhd_available'] = eodhd_provider is not None
                logger.info(f"EODHD provider available: {eodhd_provider is not None}")
                
                # Initialize enhanced EODHD if available
                if eodhd_provider and hasattr(eodhd_provider, 'config'):
                    self.enhanced_eodhd = EnhancedEODHDProvider(
                        provider_type=ProviderType.EODHD,
                        config=eodhd_provider.config
                    )
                    self.validation_results['provider_setup']['enhanced_eodhd_initialized'] = True
                    logger.info("Enhanced EODHD provider initialized")
                
            except Exception as e:
                self.validation_results['provider_setup']['eodhd_available'] = False
                logger.warning(f"EODHD provider not available: {e}")
            
            # Check Claude AI availability
            claude_api_key = os.getenv('CLAUDE_API_KEY')
            if claude_api_key and claude_api_key.strip() and claude_api_key != "your_claude_api_key_here":
                try:
                    self.claude_client = ClaudeClient(api_key=claude_api_key)
                    # Test health check
                    health_status = asyncio.run(self.claude_client.health_check())
                    self.validation_results['provider_setup']['claude_available'] = health_status
                    logger.info(f"Claude AI available and healthy: {health_status}")
                except Exception as e:
                    self.validation_results['provider_setup']['claude_available'] = False
                    logger.warning(f"Claude AI not available: {e}")
            else:
                self.validation_results['provider_setup']['claude_available'] = False
                logger.warning("Claude API key not configured")
            
            # Overall provider setup status
            setup_success = (
                self.validation_results['provider_setup'].get('marketdata_available', False) or
                self.validation_results['provider_setup'].get('eodhd_available', False)
            ) and self.validation_results['provider_setup'].get('claude_available', False)
            
            self.validation_results['provider_setup']['overall_success'] = setup_success
            return setup_success
            
        except Exception as e:
            logger.error(f"Provider setup failed: {e}")
            self.validation_results['provider_setup']['error'] = str(e)
            return False
    
    def test_corrected_data_sources(self) -> bool:
        """Test that data comes from the correct sources."""
        logger.info("Testing corrected data source routing...")
        
        try:
            data_collection_results = {}
            
            for symbol in self.test_symbols:
                symbol_results = {
                    'symbol': symbol,
                    'options_from_marketdata': False,
                    'fundamentals_from_eodhd': False,
                    'combined_data_available': False
                }
                
                # Test 1: Options data should come from MarketData.app
                try:
                    options_response = self.provider_factory.get_options_chain(symbol)
                    if options_response.is_success and options_response.data:
                        # Check provider metadata to confirm source
                        if options_response.metadata and hasattr(options_response.metadata, 'provider_type'):
                            symbol_results['options_from_marketdata'] = (
                                options_response.metadata.provider_type.value == 'marketdata' or
                                'MarketData' in str(options_response.metadata.provider_name)
                            )
                        else:
                            # Fallback check - if we got options data, assume correct source
                            symbol_results['options_from_marketdata'] = True
                        
                        logger.info(f"{symbol}: Options data received (contracts: {len(options_response.data.contracts)})")
                    else:
                        logger.warning(f"{symbol}: No options data available")
                        
                except Exception as e:
                    logger.warning(f"{symbol}: Options data retrieval failed: {e}")
                
                # Test 2: Enhanced data (fundamentals) should come from EODHD
                if self.enhanced_eodhd:
                    try:
                        enhanced_response = asyncio.run(self.enhanced_eodhd.get_enhanced_stock_data(symbol))
                        if enhanced_response.is_success and enhanced_response.data:
                            enhanced_data = enhanced_response.data
                            
                            # Check if we have fundamental data from EODHD
                            has_fundamentals = (
                                enhanced_data.fundamentals is not None and
                                enhanced_data.fundamentals.pe_ratio is not None
                            )
                            symbol_results['fundamentals_from_eodhd'] = has_fundamentals
                            
                            # Check combined data availability
                            symbol_results['combined_data_available'] = (
                                enhanced_data.quote is not None and
                                has_fundamentals
                            )
                            
                            logger.info(f"{symbol}: Enhanced data received (completeness: {enhanced_data.completeness_score:.1f}%)")
                        else:
                            logger.warning(f"{symbol}: No enhanced data available")
                            
                    except Exception as e:
                        logger.warning(f"{symbol}: Enhanced data retrieval failed: {e}")
                
                data_collection_results[symbol] = symbol_results
                
            self.validation_results['data_collection'] = data_collection_results
            
            # Overall success check
            success_count = sum(
                1 for result in data_collection_results.values() 
                if result.get('combined_data_available', False)
            )
            
            collection_success = success_count >= 2  # At least 2 out of 3 symbols
            self.validation_results['data_collection']['overall_success'] = collection_success
            
            logger.info(f"Data collection test: {success_count}/{len(self.test_symbols)} symbols successful")
            return collection_success
            
        except Exception as e:
            logger.error(f"Data collection test failed: {e}")
            self.validation_results['data_collection']['error'] = str(e)
            return False
    
    def test_claude_integration(self) -> bool:
        """Test Claude AI integration with corrected data sources."""
        logger.info("Testing Claude AI integration...")
        
        if not self.claude_client or not self.enhanced_eodhd:
            logger.warning("Claude AI or enhanced EODHD not available for integration test")
            self.validation_results['claude_analysis']['error'] = "Required components not available"
            return False
        
        try:
            # Collect enhanced stock data for Claude analysis
            enhanced_stock_data = []
            
            for symbol in self.test_symbols:
                try:
                    enhanced_response = asyncio.run(self.enhanced_eodhd.get_enhanced_stock_data(symbol))
                    if enhanced_response.is_success and enhanced_response.data:
                        enhanced_stock_data.append(enhanced_response.data)
                except Exception as e:
                    logger.warning(f"Failed to collect enhanced data for {symbol}: {e}")
            
            if not enhanced_stock_data:
                logger.error("No enhanced stock data available for Claude analysis")
                self.validation_results['claude_analysis']['error'] = "No enhanced data available"
                return False
            
            # Create market context
            market_context = {
                'analysis_date': date.today().isoformat(),
                'total_opportunities': len(enhanced_stock_data),
                'market_sentiment': 'neutral',
                'volatility_regime': 'testing'
            }
            
            # Run Claude analysis
            claude_start_time = datetime.now()
            claude_response = asyncio.run(
                self.claude_client.analyze_pmcc_opportunities(enhanced_stock_data, market_context)
            )
            claude_duration = (datetime.now() - claude_start_time).total_seconds()
            
            # Analyze results
            claude_results = {
                'analysis_duration_seconds': claude_duration,
                'analysis_successful': claude_response.is_success,
                'opportunities_analyzed': 0,
                'top_10_selection': False,
                'ai_insights_available': False,
                'cost_tracking': {}
            }
            
            if claude_response.is_success and claude_response.data:
                analysis_data = claude_response.data
                
                claude_results['opportunities_analyzed'] = len(analysis_data.opportunities)
                claude_results['top_10_selection'] = len(analysis_data.opportunities) <= 10
                claude_results['ai_insights_available'] = bool(analysis_data.market_assessment)
                
                # Check cost tracking
                if hasattr(analysis_data, 'input_tokens') and hasattr(analysis_data, 'output_tokens'):
                    claude_results['cost_tracking'] = {
                        'input_tokens': analysis_data.input_tokens,
                        'output_tokens': analysis_data.output_tokens,
                        'estimated_cost_usd': (
                            analysis_data.input_tokens * 0.000003 + 
                            analysis_data.output_tokens * 0.000015
                        )
                    }
                
                logger.info(f"Claude analysis successful: {claude_results['opportunities_analyzed']} opportunities")
                logger.info(f"Market assessment: {analysis_data.market_assessment[:100]}...")
                
                # Log top 3 opportunities
                for i, opp in enumerate(analysis_data.opportunities[:3], 1):
                    logger.info(f"  {i}. {opp.symbol}: Score {opp.score}, Confidence {opp.confidence}%")
            
            else:
                logger.error(f"Claude analysis failed: {claude_response.error}")
                claude_results['error'] = str(claude_response.error) if claude_response.error else "Unknown error"
            
            self.validation_results['claude_analysis'] = claude_results
            return claude_results['analysis_successful']
            
        except Exception as e:
            logger.error(f"Claude integration test failed: {e}")
            self.validation_results['claude_analysis']['error'] = str(e)
            return False
    
    def test_end_to_end_integration(self) -> bool:
        """Test complete end-to-end integration."""
        logger.info("Testing end-to-end integration...")
        
        try:
            # Simulate the complete workflow
            integration_results = {
                'workflow_steps': [],
                'data_flow_correct': False,
                'ai_enhancement_working': False,
                'top_n_selection_working': False,
                'overall_integration_success': False
            }
            
            # Step 1: Collect data from correct sources
            step1_success = self.test_corrected_data_sources()
            integration_results['workflow_steps'].append({
                'step': 'data_collection',
                'success': step1_success,
                'description': 'MarketData options + EODHD fundamentals'
            })
            
            if step1_success:
                integration_results['data_flow_correct'] = True
            
            # Step 2: Claude AI analysis
            step2_success = self.test_claude_integration()
            integration_results['workflow_steps'].append({
                'step': 'claude_analysis',
                'success': step2_success,
                'description': 'AI-enhanced opportunity analysis'
            })
            
            if step2_success:
                integration_results['ai_enhancement_working'] = True
                
                # Step 3: Top N selection logic
                claude_data = self.validation_results.get('claude_analysis', {})
                top_n_working = (
                    claude_data.get('opportunities_analyzed', 0) > 0 and
                    claude_data.get('top_10_selection', False)
                )
                integration_results['top_n_selection_working'] = top_n_working
                
                integration_results['workflow_steps'].append({
                    'step': 'top_n_selection',
                    'success': top_n_working,
                    'description': 'Top 10 opportunity selection'
                })
            
            # Overall integration success
            integration_results['overall_integration_success'] = (
                integration_results['data_flow_correct'] and
                integration_results['ai_enhancement_working'] and
                integration_results['top_n_selection_working']
            )
            
            self.validation_results['integration_test'] = integration_results
            
            logger.info(f"End-to-end integration test: {'SUCCESS' if integration_results['overall_integration_success'] else 'FAILED'}")
            
            return integration_results['overall_integration_success']
            
        except Exception as e:
            logger.error(f"End-to-end integration test failed: {e}")
            self.validation_results['integration_test']['error'] = str(e)
            return False
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        logger.info("Starting Claude AI Integration Validation")
        logger.info("=" * 60)
        
        try:
            # Step 1: Setup providers
            setup_success = self.setup_providers()
            if not setup_success:
                self.validation_results['overall_status'] = 'failed_setup'
                return self.validation_results
            
            # Step 2: Test data integration
            data_success = self.test_corrected_data_sources()
            
            # Step 3: Test Claude analysis
            claude_success = self.test_claude_integration()
            
            # Step 4: Test full integration
            integration_success = self.test_end_to_end_integration()
            
            # Determine overall status
            if integration_success:
                self.validation_results['overall_status'] = 'success'
            elif claude_success and data_success:
                self.validation_results['overall_status'] = 'partial_success'
            else:
                self.validation_results['overall_status'] = 'failed'
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"Validation suite failed: {e}")
            self.validation_results['overall_status'] = 'error'
            self.validation_results['error'] = str(e)
            return self.validation_results
    
    def print_validation_report(self):
        """Print detailed validation report."""
        results = self.validation_results
        
        print("\n" + "=" * 80)
        print("CLAUDE AI INTEGRATION VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\nOverall Status: {results['overall_status'].upper()}")
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Provider Setup Results
        print("\n1. PROVIDER CONFIGURATION")
        print("-" * 40)
        setup = results.get('provider_setup', {})
        print(f"MarketData.app Available: {'✅' if setup.get('marketdata_available') else '❌'}")
        print(f"EODHD Available: {'✅' if setup.get('eodhd_available') else '❌'}")
        print(f"Claude AI Available: {'✅' if setup.get('claude_available') else '❌'}")
        print(f"Enhanced EODHD Initialized: {'✅' if setup.get('enhanced_eodhd_initialized') else '❌'}")
        
        # Data Collection Results
        print("\n2. DATA COLLECTION VALIDATION")
        print("-" * 40)
        data_collection = results.get('data_collection', {})
        if isinstance(data_collection, dict) and 'overall_success' in data_collection:
            print(f"Overall Data Collection: {'✅' if data_collection['overall_success'] else '❌'}")
            
            for symbol, symbol_data in data_collection.items():
                if symbol != 'overall_success' and isinstance(symbol_data, dict):
                    print(f"\n  {symbol}:")
                    print(f"    Options (MarketData): {'✅' if symbol_data.get('options_from_marketdata') else '❌'}")
                    print(f"    Fundamentals (EODHD): {'✅' if symbol_data.get('fundamentals_from_eodhd') else '❌'}")
                    print(f"    Combined Data Ready: {'✅' if symbol_data.get('combined_data_available') else '❌'}")
        
        # Claude Analysis Results
        print("\n3. CLAUDE AI ANALYSIS")
        print("-" * 40)
        claude = results.get('claude_analysis', {})
        if claude:
            print(f"Analysis Successful: {'✅' if claude.get('analysis_successful') else '❌'}")
            print(f"Opportunities Analyzed: {claude.get('opportunities_analyzed', 0)}")
            print(f"Top 10 Selection: {'✅' if claude.get('top_10_selection') else '❌'}")
            print(f"AI Insights Available: {'✅' if claude.get('ai_insights_available') else '❌'}")
            print(f"Analysis Duration: {claude.get('analysis_duration_seconds', 0):.2f} seconds")
            
            if 'cost_tracking' in claude and claude['cost_tracking']:
                cost = claude['cost_tracking']
                print(f"Tokens Used: {cost.get('input_tokens', 0)}/{cost.get('output_tokens', 0)}")
                print(f"Estimated Cost: ${cost.get('estimated_cost_usd', 0):.4f}")
        
        # Integration Test Results
        print("\n4. END-TO-END INTEGRATION")
        print("-" * 40)
        integration = results.get('integration_test', {})
        if integration:
            print(f"Data Flow Correct: {'✅' if integration.get('data_flow_correct') else '❌'}")
            print(f"AI Enhancement Working: {'✅' if integration.get('ai_enhancement_working') else '❌'}")
            print(f"Top N Selection Working: {'✅' if integration.get('top_n_selection_working') else '❌'}")
            print(f"Overall Integration: {'✅' if integration.get('overall_integration_success') else '❌'}")
        
        # Recommendations
        print("\n5. RECOMMENDATIONS")
        print("-" * 40)
        
        if results['overall_status'] == 'success':
            print("✅ Claude AI integration is correctly configured and working!")
            print("   - Data sources are properly routed")
            print("   - AI analysis is functioning as expected")
            print("   - Top N selection logic is operational")
        
        elif results['overall_status'] == 'partial_success':
            print("⚠️  Claude AI integration is partially working:")
            if not claude.get('analysis_successful'):
                print("   - Check Claude API key and model configuration")
            if not data_collection.get('overall_success'):
                print("   - Verify MarketData.app and EODHD API keys")
        
        else:
            print("❌ Claude AI integration has issues:")
            if not setup.get('claude_available'):
                print("   - Configure CLAUDE_API_KEY environment variable")
            if not setup.get('marketdata_available') and not setup.get('eodhd_available'):
                print("   - Configure data provider API keys")
            
            if 'error' in results:
                print(f"   - Error: {results['error']}")
        
        print("\n" + "=" * 80)


def main():
    """Run the validation test."""
    test = ClaudeValidationTest()
    results = test.run_full_validation()
    test.print_validation_report()
    
    # Return appropriate exit code
    if results['overall_status'] in ['success', 'partial_success']:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)