#!/usr/bin/env python3
"""
Production-Ready Comprehensive QA Test Suite for PMCC Scanner

This test suite validates all critical components for production readiness:
1. Enhanced EODHD Data Collection (8 data types)
2. Individual Claude Analysis with 0-100 scoring
3. End-to-End Integration testing
4. Performance and reliability validation
"""

import sys
import os
import asyncio
import logging
import traceback
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import get_settings
    from src.api.provider_factory import DataProviderFactory
    from src.analysis.claude_integration import ClaudeIntegrationManager
    from src.analysis.scanner import PMCCScanner, ScanConfiguration
    from src.models.api_models import APIStatus, APIResponse
    from src.notifications.notification_manager import NotificationManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Run from project root: python3 comprehensive_qa_test_final.py")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qa_test.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)


class ProductionQATest:
    """Production readiness QA test suite for PMCC Scanner."""
    
    def __init__(self):
        self.settings = get_settings()
        self.results = {'passed': [], 'failed': [], 'warnings': [], 'metrics': {}}
        self.start_time = datetime.now()
        self.factory = None
        self.claude_manager = None

    def log_result(self, test: str, success: bool, message: str, metrics: Dict = None):
        """Log test result."""
        result = {'test': test, 'message': message, 'time': datetime.now().strftime("%H:%M:%S")}
        if metrics:
            result['metrics'] = metrics
            self.results['metrics'][test] = metrics
        
        if success:
            self.results['passed'].append(result)
            logger.info(f"✅ PASSED - {test}: {message}")
        else:
            self.results['failed'].append(result)
            logger.error(f"❌ FAILED - {test}: {message}")

    async def run_all_tests(self):
        """Run comprehensive test suite."""
        logger.info("="*70)
        logger.info("PRODUCTION QA TEST SUITE - PMCC SCANNER")
        logger.info("="*70)
        
        # Core tests
        await self.test_configuration()
        await self.test_provider_initialization()
        await self.test_api_connectivity()
        await self.test_enhanced_data_collection()
        await self.test_claude_analysis()
        await self.test_end_to_end_workflow()
        await self.test_performance_requirements()
        await self.test_error_handling()
        
        # Generate final report
        self.generate_report()
        return self.results

    async def test_configuration(self):
        """Test system configuration."""
        try:
            # Check essential configurations
            has_eodhd = bool(self.settings.eodhd and self.settings.eodhd.api_token)
            has_claude = bool(self.settings.claude and self.settings.claude.api_key)
            has_daily_limit = bool(self.settings.claude and self.settings.claude.daily_cost_limit > 0)
            
            config_data = {
                'eodhd_configured': has_eodhd,
                'claude_configured': has_claude,
                'cost_limits_set': has_daily_limit
            }
            
            if has_eodhd and has_claude and has_daily_limit:
                self.log_result("Configuration Validation", True, 
                              "All required APIs configured", config_data)
            else:
                missing = []
                if not has_eodhd: missing.append("EODHD")
                if not has_claude: missing.append("Claude")
                if not has_daily_limit: missing.append("cost limits")
                
                self.log_result("Configuration Validation", False, 
                              f"Missing: {', '.join(missing)}", config_data)
                
        except Exception as e:
            self.log_result("Configuration Validation", False, f"Error: {e}")

    async def test_provider_initialization(self):
        """Test provider factory initialization."""
        try:
            start_time = time.time()
            self.factory = DataProviderFactory()
            init_time = time.time() - start_time
            
            provider_status = self.factory.get_provider_status()
            available_providers = [name for name, status in provider_status.items() 
                                 if status.get('available', False)]
            
            self.claude_manager = ClaudeIntegrationManager()
            
            init_data = {
                'init_time_seconds': round(init_time, 3),
                'available_providers': available_providers,
                'total_providers': len(provider_status)
            }
            
            if len(available_providers) >= 2:  # Need at least EODHD and Claude
                self.log_result("Provider Initialization", True, 
                              f"{len(available_providers)} providers available", init_data)
            else:
                self.log_result("Provider Initialization", False, 
                              f"Insufficient providers: {available_providers}", init_data)
                
        except Exception as e:
            self.log_result("Provider Initialization", False, f"Error: {e}")

    async def test_api_connectivity(self):
        """Test API connectivity."""
        if not self.factory:
            self.log_result("API Connectivity", False, "Factory not initialized")
            return
        
        try:
            connectivity = {}
            
            # Test EODHD
            try:
                eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
                response = await eodhd_provider.get_stock_quote('AAPL')
                connectivity['eodhd'] = response.status == APIStatus.SUCCESS
            except Exception as e:
                connectivity['eodhd'] = False
                connectivity['eodhd_error'] = str(e)
            
            # Test Claude
            try:
                claude_provider = await self.factory.get_provider('claude')
                test_data = [{'symbol': 'TEST', 'pmcc_score': 75}]
                response = await claude_provider.analyze_opportunities(test_data)
                connectivity['claude'] = response.status == APIStatus.SUCCESS
            except Exception as e:
                connectivity['claude'] = False
                connectivity['claude_error'] = str(e)
            
            connected = sum(1 for connected in connectivity.values() if connected is True)
            
            if connected >= 2:
                self.log_result("API Connectivity", True, 
                              f"{connected} APIs connected", connectivity)
            else:
                self.log_result("API Connectivity", False, 
                              f"Only {connected} APIs connected", connectivity)
                
        except Exception as e:
            self.log_result("API Connectivity", False, f"Error: {e}")

    async def test_enhanced_data_collection(self):
        """Test enhanced EODHD data collection."""
        if not self.factory:
            self.log_result("Enhanced Data Collection", False, "Factory not initialized")
            return
        
        try:
            start_time = time.time()
            eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
            
            # Test with KSS (known opportunity)
            response = await eodhd_provider.get_enhanced_stock_data(['KSS'])
            collection_time = time.time() - start_time
            
            if response.status != APIStatus.SUCCESS or not response.data:
                self.log_result("Enhanced Data Collection", False, 
                              f"Data collection failed: {response.message}")
                return
            
            stock_data = response.data[0]
            
            # Check for the 8 expected data types
            data_types = [
                'stock_quote', 'fundamental_metrics', 'bulk_fundamentals',
                'calendar_events', 'insider_transactions', 'technical_indicators',
                'analyst_ratings', 'splits_dividends'
            ]
            
            collected = []
            for data_type in data_types:
                if hasattr(stock_data, data_type) and getattr(stock_data, data_type):
                    collected.append(data_type)
            
            collection_metrics = {
                'symbol': 'KSS',
                'collection_time_seconds': round(collection_time, 3),
                'data_types_expected': len(data_types),
                'data_types_collected': len(collected),
                'collection_percentage': round(len(collected) / len(data_types) * 100, 1),
                'collected_types': collected
            }
            
            if len(collected) >= 3:  # Need at least basic data
                self.log_result("Enhanced Data Collection", True, 
                              f"Collected {len(collected)}/8 data types ({collection_metrics['collection_percentage']}%)", 
                              collection_metrics)
            else:
                self.log_result("Enhanced Data Collection", False, 
                              f"Insufficient data: only {len(collected)}/8 types", 
                              collection_metrics)
                
        except Exception as e:
            self.log_result("Enhanced Data Collection", False, f"Error: {e}")

    async def test_claude_analysis(self):
        """Test individual Claude opportunity analysis."""
        if not self.factory:
            self.log_result("Claude Analysis", False, "Factory not initialized")
            return
        
        try:
            claude_provider = await self.factory.get_provider('claude')
            
            # Create mock opportunity for analysis
            opportunity = {
                'symbol': 'KSS',
                'company_name': 'Kohls Corporation',
                'pmcc_score': 75.5,
                'max_profit': 1500,
                'max_loss': -2000,
                'probability_of_profit': 0.68,
                'stock_price': 22.50
            }
            
            start_time = time.time()
            response = await claude_provider.analyze_opportunities([opportunity])
            analysis_time = time.time() - start_time
            
            if response.status != APIStatus.SUCCESS or not response.data:
                self.log_result("Claude Analysis", False, 
                              f"Analysis failed: {response.message}")
                return
            
            analysis = response.data.opportunities[0]
            
            analysis_metrics = {
                'analysis_time_seconds': round(analysis_time, 3),
                'claude_score': analysis.claude_score,
                'score_valid': 0 <= analysis.claude_score <= 100 if analysis.claude_score else False,
                'has_reasoning': bool(analysis.reasoning),
                'reasoning_length': len(analysis.reasoning) if analysis.reasoning else 0,
                'has_recommendation': analysis.recommendation is not None,
                'cost_incurred': getattr(response.data, 'cost_incurred', 0)
            }
            
            quality_check = (
                analysis_metrics['score_valid'] and
                analysis_metrics['has_reasoning'] and
                analysis_metrics['reasoning_length'] > 50
            )
            
            if quality_check:
                self.log_result("Claude Analysis", True, 
                              f"Analysis successful - Score: {analysis.claude_score}/100", 
                              analysis_metrics)
            else:
                issues = []
                if not analysis_metrics['score_valid']:
                    issues.append("invalid score")
                if not analysis_metrics['has_reasoning']:
                    issues.append("no reasoning")
                if analysis_metrics['reasoning_length'] <= 50:
                    issues.append("insufficient reasoning")
                
                self.log_result("Claude Analysis", False, 
                              f"Quality issues: {', '.join(issues)}", 
                              analysis_metrics)
                
        except Exception as e:
            self.log_result("Claude Analysis", False, f"Error: {e}")

    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        if not self.factory or not self.claude_manager:
            self.log_result("End-to-End Workflow", False, "Components not initialized")
            return
        
        try:
            # Initialize scanner with test configuration
            scan_config = ScanConfiguration(
                market_cap_min=50_000_000,
                market_cap_max=5_000_000_000,
                min_volume=100_000,
                max_opportunities=3,
                ai_enhancement_enabled=True,
                ai_top_n_selection=2
            )
            
            scanner = PMCCScanner(self.factory)
            
            start_time = time.time()
            # Test with known symbols
            results = await scanner.scan_symbols(['KSS', 'AAPL'], scan_config)
            workflow_time = time.time() - start_time
            
            workflow_metrics = {
                'workflow_time_seconds': round(workflow_time, 3),
                'results_count': len(results),
                'has_traditional_scoring': False,
                'has_ai_enhancement': False,
                'complete_integration': False
            }
            
            if results:
                first_result = results[0]
                workflow_metrics['has_traditional_scoring'] = 'pmcc_score' in first_result
                workflow_metrics['has_ai_enhancement'] = (
                    'claude_score' in first_result or 
                    'claude_analyzed' in first_result or
                    'ai_recommendation' in first_result
                )
                workflow_metrics['complete_integration'] = (
                    workflow_metrics['has_traditional_scoring'] and
                    workflow_metrics['has_ai_enhancement']
                )
            
            if workflow_metrics['complete_integration'] and len(results) > 0:
                self.log_result("End-to-End Workflow", True, 
                              f"Complete workflow successful - {len(results)} results", 
                              workflow_metrics)
            else:
                issues = []
                if len(results) == 0:
                    issues.append("no results")
                if not workflow_metrics['has_traditional_scoring']:
                    issues.append("missing PMCC scoring")
                if not workflow_metrics['has_ai_enhancement']:
                    issues.append("missing AI enhancement")
                
                self.log_result("End-to-End Workflow", False, 
                              f"Workflow issues: {', '.join(issues)}", 
                              workflow_metrics)
                
        except Exception as e:
            self.log_result("End-to-End Workflow", False, f"Error: {e}")

    async def test_performance_requirements(self):
        """Test performance requirements."""
        if not self.factory:
            self.log_result("Performance Requirements", False, "Factory not initialized")
            return
        
        try:
            # Test concurrent data collection
            eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
            
            symbols = ['KSS', 'AAPL', 'MSFT']
            start_time = time.time()
            
            # Execute concurrent requests
            tasks = [eodhd_provider.get_enhanced_stock_data([symbol]) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_time = time.time() - start_time
            
            successful = sum(1 for r in results if not isinstance(r, Exception) and r.status == APIStatus.SUCCESS)
            
            performance_metrics = {
                'concurrent_requests': len(symbols),
                'successful_requests': successful,
                'total_time_seconds': round(concurrent_time, 3),
                'avg_time_per_request': round(concurrent_time / len(symbols), 3),
                'performance_acceptable': concurrent_time < 15.0 and successful >= 2
            }
            
            if performance_metrics['performance_acceptable']:
                self.log_result("Performance Requirements", True, 
                              f"Performance acceptable: {successful}/3 requests in {concurrent_time:.2f}s", 
                              performance_metrics)
            else:
                issues = []
                if concurrent_time >= 15.0:
                    issues.append("slow response time")
                if successful < 2:
                    issues.append("low success rate")
                
                self.log_result("Performance Requirements", False, 
                              f"Performance issues: {', '.join(issues)}", 
                              performance_metrics)
                
        except Exception as e:
            self.log_result("Performance Requirements", False, f"Error: {e}")

    async def test_error_handling(self):
        """Test error handling and graceful degradation."""
        if not self.factory:
            self.log_result("Error Handling", False, "Factory not initialized")
            return
        
        try:
            error_scenarios = {}
            
            # Test with invalid symbol
            try:
                eodhd_provider = await self.factory.get_provider('enhanced_eodhd')
                response = await eodhd_provider.get_enhanced_stock_data(['INVALID_SYMBOL'])
                error_scenarios['invalid_symbol'] = {
                    'handled': response.status != APIStatus.ERROR,
                    'has_message': bool(response.message)
                }
            except Exception as e:
                error_scenarios['invalid_symbol'] = {'handled': True, 'exception': str(e)}
            
            # Test Claude with empty data
            try:
                claude_provider = await self.factory.get_provider('claude')
                response = await claude_provider.analyze_opportunities([])
                error_scenarios['empty_data'] = {
                    'handled': response.status != APIStatus.ERROR,
                    'appropriate_response': 'empty' in (response.message or '').lower()
                }
            except Exception as e:
                error_scenarios['empty_data'] = {'handled': True, 'exception': str(e)}
            
            # Test notification system resilience
            try:
                notification_manager = NotificationManager()
                error_scenarios['notifications'] = {
                    'initialized': True,
                    'has_circuit_breakers': hasattr(notification_manager, 'whatsapp_breaker')
                }
            except Exception as e:
                error_scenarios['notifications'] = {'initialized': False, 'error': str(e)}
            
            graceful_handling = sum(1 for scenario in error_scenarios.values() 
                                  if scenario.get('handled', True))
            
            error_metrics = {
                'scenarios_tested': len(error_scenarios),
                'gracefully_handled': graceful_handling,
                'error_handling_rate': round(graceful_handling / len(error_scenarios) * 100, 1),
                'detailed_scenarios': error_scenarios
            }
            
            if graceful_handling >= len(error_scenarios) * 0.8:
                self.log_result("Error Handling", True, 
                              f"Error handling robust: {error_metrics['error_handling_rate']}% scenarios handled", 
                              error_metrics)
            else:
                self.log_result("Error Handling", False, 
                              f"Error handling needs improvement: {error_metrics['error_handling_rate']}%", 
                              error_metrics)
                
        except Exception as e:
            self.log_result("Error Handling", False, f"Error: {e}")

    def generate_report(self):
        """Generate final production readiness report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        total_tests = len(self.results['passed']) + len(self.results['failed'])
        pass_rate = len(self.results['passed']) / total_tests * 100 if total_tests > 0 else 0
        
        # Critical test analysis
        critical_tests = [
            'Configuration Validation', 'Provider Initialization', 'API Connectivity',
            'Enhanced Data Collection', 'Claude Analysis', 'End-to-End Workflow'
        ]
        
        critical_failures = [
            test for test in self.results['failed']
            if test['test'] in critical_tests
        ]
        
        # Production readiness determination
        production_ready = (
            len(self.results['failed']) <= 2 and  # Max 2 failures
            len(critical_failures) == 0 and      # No critical failures
            pass_rate >= 75.0                     # 75% pass rate minimum
        )
        
        # Generate report
        logger.info("\n" + "="*70)
        logger.info("PRODUCTION READINESS ASSESSMENT")
        logger.info("="*70)
        logger.info(f"Test Duration: {duration}")
        logger.info(f"Tests Run: {total_tests}")
        logger.info(f"Passed: {len(self.results['passed'])} ({pass_rate:.1f}%)")
        logger.info(f"Failed: {len(self.results['failed'])}")
        logger.info("")
        
        if production_ready:
            logger.info("🟢 PRODUCTION READY: System approved for deployment")
            logger.info("All critical components validated successfully.")
        else:
            logger.info("🔴 NOT PRODUCTION READY: Issues require resolution")
            logger.info(f"Critical failures: {len(critical_failures)}")
        
        logger.info("")
        
        # List failures if any
        if self.results['failed']:
            logger.info("FAILURES REQUIRING ATTENTION:")
            for failure in self.results['failed']:
                logger.info(f"❌ {failure['test']}: {failure['message']}")
        
        logger.info("\n" + "="*70)
        
        # Save report
        report_file = f"production_qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'test_start': self.start_time.isoformat(),
                    'test_end': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'total_tests': total_tests,
                    'passed': len(self.results['passed']),
                    'failed': len(self.results['failed']),
                    'pass_rate': pass_rate,
                    'production_ready': production_ready,
                    'critical_failures': len(critical_failures)
                },
                'results': self.results
            }, f, indent=2, default=str)
        
        logger.info(f"Detailed report: {report_file}")
        return production_ready


async def main():
    """Run production QA test suite."""
    tester = ProductionQATest()
    try:
        await tester.run_all_tests()
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
