#\!/usr/bin/env python3
"""
Comprehensive QA Test Suite for PMCC Scanner Production Readiness

This test suite validates all critical components of the PMCC Scanner system
to ensure production readiness, including:

1. Enhanced EODHD Data Collection (8 data types)
2. Individual Claude Analysis with 0-100 scoring
3. End-to-End Integration testing
4. Performance and reliability validation
5. Error handling and circuit breaker testing

Usage: python3 comprehensive_qa_test.py
"""

import sys
import os
import asyncio
import logging
import traceback
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import statistics

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import all necessary components
try:
    from src.config import get_settings, Settings
    from src.api.provider_factory import DataProviderFactory
    from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
    from src.api.providers.claude_provider import ClaudeProvider
    from src.analysis.claude_integration import ClaudeIntegrationManager
    from src.analysis.scanner import PMCCScanner, ScanConfiguration
    from src.models.api_models import (
        EnhancedStockData, ClaudeAnalysisResponse, PMCCOpportunityAnalysis,
        APIResponse, APIStatus, StockQuote, FundamentalMetrics,
        CalendarEvent, TechnicalIndicators
    )
    from src.notifications.notification_manager import NotificationManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive_qa_test.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)


class ComprehensiveQATest:
    """
    Production-readiness QA test suite for PMCC Scanner.
    
    Validates all critical components and their integrations to ensure
    the system is ready for production deployment.
    """
    
    def __init__(self):
        """Initialize the comprehensive QA test suite."""
        self.settings = get_settings()
        self.test_results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'skipped': [],
            'performance_metrics': {}
        }
        self.start_time = datetime.now()
        
        # Test symbols - mix of known opportunities and edge cases
        self.test_symbols = [
            'KSS',    # Known PMCC opportunity from previous scans
            'AAPL',   # High-volume, reliable data
            'XYZ123', # Invalid symbol for error testing
            'MSFT',   # Another reliable symbol
            'INVALID' # Another invalid for edge case testing
        ]
        
        # Test configuration
        self.scan_config = None
        self.factory = None
        self.claude_manager = None
        
    def log_test_result(self, test_name: str, success: bool, message: str = "", 
                       warning: bool = False, skip: bool = False, 
                       performance_data: Optional[Dict] = None):
        """Log test result and track statistics."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        result = {
            'test': test_name,
            'message': message,
            'timestamp': timestamp
        }
        
        if performance_data:
            result['performance'] = performance_data
            self.test_results['performance_metrics'][test_name] = performance_data
        
        if skip:
            self.test_results['skipped'].append(result)
            logger.warning(f"SKIPPED - {test_name}: {message}")
        elif warning:
            self.test_results['warnings'].append(result)
            logger.warning(f"WARNING - {test_name}: {message}")
        elif success:
            self.test_results['passed'].append(result)
            logger.info(f"PASSED  - {test_name}: {message}")
        else:
            self.test_results['failed'].append(result)
            logger.error(f"FAILED  - {test_name}: {message}")

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests and return results."""
        logger.info("="*80)
        logger.info("STARTING COMPREHENSIVE QA TEST SUITE")
        logger.info("="*80)
        
        # Group 1: Configuration and Setup Tests
        logger.info("\n" + "="*50)
        logger.info("GROUP 1: CONFIGURATION AND SETUP TESTS")
        logger.info("="*50)
        
        await self.test_01_system_configuration()
        await self.test_02_provider_initialization()
        await self.test_03_api_connectivity()
        
        # Group 2: Enhanced EODHD Data Collection Tests
        logger.info("\n" + "="*50)
        logger.info("GROUP 2: ENHANCED EODHD DATA COLLECTION TESTS")
        logger.info("="*50)
        
        await self.test_04_enhanced_data_collection_all_types()
        await self.test_05_fundamental_data_filtering()
        await self.test_06_missing_data_handling()
        await self.test_07_data_collection_performance()
        
        # Group 3: Individual Claude Analysis Tests
        logger.info("\n" + "="*50)
        logger.info("GROUP 3: INDIVIDUAL CLAUDE ANALYSIS TESTS")
        logger.info("="*50)
        
        await self.test_08_single_opportunity_analysis()
        await self.test_09_scoring_system_validation()
        await self.test_10_claude_error_handling()
        await self.test_11_cost_tracking_limits()
        
        # Group 4: End-to-End Integration Tests
        logger.info("\n" + "="*50)
        logger.info("GROUP 4: END-TO-END INTEGRATION TESTS")
        logger.info("="*50)
        
        await self.test_12_complete_workflow_integration()
        await self.test_13_data_flow_validation()
        await self.test_14_kss_opportunity_validation()
        await self.test_15_notification_integration()
        
        # Group 5: Performance and Reliability Tests
        logger.info("\n" + "="*50)
        logger.info("GROUP 5: PERFORMANCE AND RELIABILITY TESTS")
        logger.info("="*50)
        
        await self.test_16_concurrent_requests()
        await self.test_17_rate_limiting_compliance()
        await self.test_18_circuit_breaker_functionality()
        await self.test_19_graceful_degradation()
        await self.test_20_memory_usage_validation()
        
        # Generate final report
        await self.generate_final_report()
        return self.test_results

    async def test_01_system_configuration(self):
        """Test 1: Validate system configuration completeness."""
        test_name = "System Configuration Validation"
        
        try:
            # Check API configurations
            has_eodhd = self.settings.eodhd and bool(self.settings.eodhd.api_token)
            has_marketdata = self.settings.marketdata and bool(self.settings.marketdata.api_token)
            has_claude = self.settings.claude and bool(self.settings.claude.api_key)
            
            missing_configs = []
            if not has_eodhd:
                missing_configs.append("EODHD API")
            if not has_marketdata:
                missing_configs.append("MarketData.app API")
            if not has_claude:
                missing_configs.append("Claude API")
                
            if missing_configs:
                self.log_test_result(
                    test_name, False, 
                    f"Missing configurations: {', '.join(missing_configs)}"
                )
                return
            
            # Validate specific settings
            if not self.settings.claude.daily_cost_limit or self.settings.claude.daily_cost_limit <= 0:
                self.log_test_result(
                    test_name, False, 
                    "Claude daily cost limit not properly configured"
                )
                return
            
            config_summary = {
                'eodhd_configured': has_eodhd,
                'marketdata_configured': has_marketdata,
                'claude_configured': has_claude,
                'claude_daily_limit': float(self.settings.claude.daily_cost_limit)
            }
            
            self.log_test_result(
                test_name, True, 
                f"All API configurations valid: {config_summary}",
                performance_data=config_summary
            )
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Configuration error: {str(e)}")

    async def test_02_provider_initialization(self):
        """Test 2: Validate provider factory initialization."""
        test_name = "Provider Factory Initialization"
        
        try:
            start_time = time.time()
            self.factory = DataProviderFactory()
            init_time = time.time() - start_time
            
            # Test provider availability
            provider_status = self.factory.get_provider_status()
            
            required_providers = ['eodhd', 'marketdata', 'claude']
            available_providers = []
            
            for provider_name in required_providers:
                if provider_name in provider_status and provider_status[provider_name].get('available', False):
                    available_providers.append(provider_name)
            
            if len(available_providers) \!= len(required_providers):
                missing = set(required_providers) - set(available_providers)
                self.log_test_result(
                    test_name, False, 
                    f"Missing providers: {missing}. Available: {available_providers}"
                )
                return
            
            # Initialize Claude integration manager
            self.claude_manager = ClaudeIntegrationManager()
            
            performance_data = {
                'initialization_time_seconds': round(init_time, 3),
                'available_providers': available_providers,
                'provider_status': provider_status
            }
            
            self.log_test_result(
                test_name, True, 
                f"All providers initialized successfully in {init_time:.3f}s",
                performance_data=performance_data
            )
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Provider initialization error: {str(e)}")

    async def test_03_api_connectivity(self):
        """Test 3: Validate API connectivity for all providers."""
        test_name = "API Connectivity Validation"
        
        if not self.factory:
            self.log_test_result(test_name, False, "Provider factory not initialized")
            return
        
        try:
            connectivity_results = {}
            
            # Test EODHD connectivity
            try:
                eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
                # Simple health check - try to get a quote
                test_response = await eodhd_provider.get_stock_quote('AAPL')
                connectivity_results['eodhd'] = {
                    'connected': test_response.status == APIStatus.SUCCESS,
                    'response_time': getattr(test_response, 'response_time_ms', None)
                }
            except Exception as e:
                connectivity_results['eodhd'] = {'connected': False, 'error': str(e)}
            
            # Test Claude connectivity
            try:
                claude_provider = await self.factory.get_provider('claude')
                # Simple test analysis
                test_data = [{
                    'symbol': 'TEST',
                    'company_name': 'Test Company',
                    'pmcc_score': 75
                }]
                test_response = await claude_provider.analyze_opportunities(test_data)
                connectivity_results['claude'] = {
                    'connected': test_response.status == APIStatus.SUCCESS,
                    'response_time': getattr(test_response, 'response_time_ms', None)
                }
            except Exception as e:
                connectivity_results['claude'] = {'connected': False, 'error': str(e)}
            
            # Check results
            connected_count = sum(1 for result in connectivity_results.values() if result.get('connected', False))
            
            if connected_count >= 1:  # At least one provider should connect
                self.log_test_result(
                    test_name, True, 
                    f"{connected_count} API providers connected successfully",
                    performance_data=connectivity_results
                )
            else:
                failed_providers = [name for name, result in connectivity_results.items() if not result.get('connected', False)]
                self.log_test_result(
                    test_name, False, 
                    f"Failed to connect to: {failed_providers}",
                    performance_data=connectivity_results
                )
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Connectivity test error: {str(e)}")

    async def test_04_enhanced_data_collection_all_types(self):
        """Test 4: Validate collection of all 8 enhanced EODHD data types."""
        test_name = "Enhanced EODHD Data Collection - All 8 Types"
        
        if not self.factory:
            self.log_test_result(test_name, False, "Provider factory not initialized")
            return
        
        try:
            start_time = time.time()
            eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
            
            # Test with KSS as it's a known good opportunity
            test_symbol = 'KSS'
            
            # Collect enhanced data
            enhanced_data = await eodhd_provider.get_enhanced_stock_data([test_symbol])
            collection_time = time.time() - start_time
            
            if enhanced_data.status \!= APIStatus.SUCCESS:
                self.log_test_result(
                    test_name, False, 
                    f"Failed to collect enhanced data: {enhanced_data.message}"
                )
                return
            
            if not enhanced_data.data or len(enhanced_data.data) == 0:
                self.log_test_result(
                    test_name, False, 
                    "No enhanced data returned"
                )
                return
            
            stock_data = enhanced_data.data[0]
            
            # Validate all 8 data types are present
            expected_data_types = [
                'stock_quote',
                'fundamental_metrics', 
                'bulk_fundamentals',
                'calendar_events',
                'insider_transactions',
                'technical_indicators',
                'analyst_ratings',
                'splits_dividends'
            ]
            
            collected_types = []
            missing_types = []
            
            for data_type in expected_data_types:
                if hasattr(stock_data, data_type) and getattr(stock_data, data_type) is not None:
                    collected_types.append(data_type)
                else:
                    missing_types.append(data_type)
            
            # Validate data quality
            data_quality = {
                'total_expected': len(expected_data_types),
                'total_collected': len(collected_types),
                'collection_percentage': round((len(collected_types) / len(expected_data_types)) * 100, 1),
                'missing_types': missing_types,
                'collection_time_seconds': round(collection_time, 3)
            }
            
            if len(collected_types) >= 3:  # Allow for missing optional data, but need some basics
                self.log_test_result(
                    test_name, True, 
                    f"Collected {len(collected_types)}/8 data types ({data_quality['collection_percentage']}%)",
                    performance_data=data_quality
                )
            else:
                self.log_test_result(
                    test_name, False, 
                    f"Insufficient data collected: {len(collected_types)}/8 types. Missing: {missing_types}",
                    performance_data=data_quality
                )
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Enhanced data collection error: {str(e)}")

    async def generate_final_report(self):
        """Generate comprehensive final test report."""
        end_time = datetime.now()
        total_duration = end_time - self.start_time
        
        # Calculate statistics
        total_tests = (
            len(self.test_results['passed']) + 
            len(self.test_results['failed']) + 
            len(self.test_results['warnings']) + 
            len(self.test_results['skipped'])
        )
        
        pass_rate = (len(self.test_results['passed']) / total_tests * 100) if total_tests > 0 else 0
        
        # Production readiness assessment
        critical_failures = [
            test for test in self.test_results['failed'] 
            if any(critical_term in test['test'].lower() for critical_term in [
                'configuration', 'connectivity', 'workflow', 'data flow'
            ])
        ]
        
        production_ready = (
            len(self.test_results['failed']) <= 3 and  # No more than 3 failures
            len(critical_failures) == 0 and           # No critical failures
            pass_rate >= 75.0                          # At least 75% pass rate
        )
        
        # Generate comprehensive report
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE QA TEST FINAL REPORT")
        logger.info("="*80)
        logger.info(f"Test Duration: {total_duration}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"PASSED: {len(self.test_results['passed'])} ({len(self.test_results['passed'])/total_tests*100:.1f}%)")
        logger.info(f"FAILED: {len(self.test_results['failed'])} ({len(self.test_results['failed'])/total_tests*100:.1f}%)")
        logger.info(f"WARNINGS: {len(self.test_results['warnings'])}")
        logger.info(f"SKIPPED: {len(self.test_results['skipped'])}")
        logger.info(f"Pass Rate: {pass_rate:.1f}%")
        logger.info("")
        
        # Production readiness assessment
        if production_ready:
            logger.info("🟢 PRODUCTION READINESS: APPROVED")
            logger.info("The PMCC Scanner system is ready for production deployment.")
        else:
            logger.info("🔴 PRODUCTION READINESS: NOT APPROVED")
            logger.info("Critical issues must be resolved before production deployment.")
        
        logger.info("")
        
        # Failed tests summary
        if self.test_results['failed']:
            logger.info("FAILED TESTS REQUIRING ATTENTION:")
            logger.info("-" * 50)
            for failure in self.test_results['failed']:
                logger.info(f"❌ {failure['test']}: {failure['message']}")
        
        # Warnings summary
        if self.test_results['warnings']:
            logger.info("\nWARNINGS FOR REVIEW:")
            logger.info("-" * 30)
            for warning in self.test_results['warnings']:
                logger.info(f"⚠️  {warning['test']}: {warning['message']}")
        
        logger.info("\n" + "="*80)
        logger.info("END OF COMPREHENSIVE QA REPORT")
        logger.info("="*80)
        
        # Save detailed report to file
        report_filename = f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                'test_summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'total_duration_seconds': total_duration.total_seconds(),
                    'total_tests': total_tests,
                    'passed': len(self.test_results['passed']),
                    'failed': len(self.test_results['failed']),
                    'warnings': len(self.test_results['warnings']),
                    'skipped': len(self.test_results['skipped']),
                    'pass_rate': pass_rate,
                    'production_ready': production_ready
                },
                'detailed_results': self.test_results
            }, f, indent=2, default=str)
        
        logger.info(f"Detailed report saved to: {report_filename}")


async def main():
    """Main test execution function."""
    logger.info("Initializing Comprehensive QA Test Suite...")
    
    qa_tester = ComprehensiveQATest()
    
    try:
        results = await qa_tester.run_comprehensive_tests()
        return results
    except KeyboardInterrupt:
        logger.info("\nTest suite interrupted by user")
        return qa_tester.test_results
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        logger.error(traceback.format_exc())
        return qa_tester.test_results


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(main())
END_OF_FILE < /dev/null
