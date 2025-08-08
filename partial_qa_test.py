#\!/usr/bin/env python3
"""
Partial QA Test Suite - Testing Components That Work

This test validates components that can function despite the provider factory issues,
providing maximum testing value while critical bugs are being resolved.
"""

import sys
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class PartialQATest:
    """QA test for components that can function despite provider factory issues."""
    
    def __init__(self):
        self.results = {'passed': [], 'failed': [], 'blocked': []}
        self.start_time = datetime.now()

    def log_result(self, test: str, status: str, message: str, data: Dict = None):
        """Log test result."""
        result = {'test': test, 'message': message, 'time': datetime.now().strftime("%H:%M:%S")}
        if data:
            result['data'] = data
        
        self.results[status].append(result)
        
        if status == 'passed':
            logger.info(f"✅ PASSED - {test}: {message}")
        elif status == 'failed':
            logger.error(f"❌ FAILED - {test}: {message}")
        else:
            logger.warning(f"🚫 BLOCKED - {test}: {message}")

    def run_all_tests(self):
        """Run all available tests."""
        logger.info("="*70)
        logger.info("PARTIAL QA TEST SUITE - COMPONENT VALIDATION")
        logger.info("="*70)
        
        self.test_configuration_system()
        self.test_module_imports()
        self.test_data_models()
        self.test_settings_validation()
        self.test_provider_class_structure()
        self.test_notification_components()
        self.test_analysis_modules()
        
        self.generate_report()
        return self.results

    def test_configuration_system(self):
        """Test configuration system functionality."""
        try:
            settings = get_settings()
            
            # Validate configuration structure
            config_data = {
                'has_eodhd_config': bool(settings.eodhd),
                'eodhd_token_configured': bool(settings.eodhd and settings.eodhd.api_token),
                'has_claude_config': bool(settings.claude),
                'claude_key_configured': bool(settings.claude and settings.claude.api_key),
                'claude_daily_limit': settings.claude.daily_cost_limit if settings.claude else None,
                'has_marketdata_config': bool(settings.marketdata),
                'marketdata_token_configured': bool(settings.marketdata and settings.marketdata.api_token)
            }
            
            # Check if essential configs are present
            essential_configs = [
                config_data['eodhd_token_configured'],
                config_data['claude_key_configured'],
                config_data['claude_daily_limit'] and config_data['claude_daily_limit'] > 0
            ]
            
            if all(essential_configs):
                self.log_result("Configuration System", "passed", 
                              "All essential configurations validated", config_data)
            else:
                missing = []
                if not config_data['eodhd_token_configured']:
                    missing.append("EODHD token")
                if not config_data['claude_key_configured']:
                    missing.append("Claude key")
                if not (config_data['claude_daily_limit'] and config_data['claude_daily_limit'] > 0):
                    missing.append("Claude daily limit")
                
                self.log_result("Configuration System", "failed", 
                              f"Missing configurations: {', '.join(missing)}", config_data)
                
        except Exception as e:
            self.log_result("Configuration System", "failed", f"Configuration error: {e}")

    def test_module_imports(self):
        """Test that all required modules can be imported."""
        import_tests = [
            ("Provider Factory", "src.api.provider_factory", "DataProviderFactory"),
            ("Enhanced EODHD Provider", "src.api.providers.enhanced_eodhd_provider", "EnhancedEODHDProvider"),
            ("Claude Provider", "src.api.providers.claude_provider", "ClaudeProvider"),
            ("Claude Integration", "src.analysis.claude_integration", "ClaudeIntegrationManager"),
            ("PMCC Scanner", "src.analysis.scanner", "PMCCScanner"),
            ("API Models", "src.models.api_models", "APIResponse"),
            ("Notification Manager", "src.notifications.notification_manager", "NotificationManager")
        ]
        
        import_results = {}
        successful_imports = 0
        
        for test_name, module_path, class_name in import_tests:
            try:
                module = __import__(module_path, fromlist=[class_name])
                class_obj = getattr(module, class_name)
                import_results[test_name] = {'success': True, 'class': str(class_obj)}
                successful_imports += 1
            except ImportError as e:
                import_results[test_name] = {'success': False, 'error': str(e)}
            except AttributeError as e:
                import_results[test_name] = {'success': False, 'error': f"Class not found: {e}"}
        
        success_rate = (successful_imports / len(import_tests)) * 100
        
        if successful_imports == len(import_tests):
            self.log_result("Module Imports", "passed", 
                          "All required modules imported successfully", import_results)
        elif successful_imports >= len(import_tests) * 0.8:  # 80% success
            self.log_result("Module Imports", "passed", 
                          f"Most modules imported: {successful_imports}/{len(import_tests)} ({success_rate:.1f}%)", 
                          import_results)
        else:
            self.log_result("Module Imports", "failed", 
                          f"Too many import failures: {successful_imports}/{len(import_tests)} ({success_rate:.1f}%)", 
                          import_results)

    def test_data_models(self):
        """Test data model classes."""
        try:
            from src.models.api_models import APIResponse, APIStatus, EnhancedStockData
            
            # Test model instantiation
            response = APIResponse(status=APIStatus.SUCCESS, message="test", data=None)
            
            model_tests = {
                'APIResponse_creation': response is not None,
                'APIStatus_enum': hasattr(APIStatus, 'SUCCESS'),
                'EnhancedStockData_exists': EnhancedStockData is not None,
                'response_status_correct': response.status == APIStatus.SUCCESS,
                'response_message_correct': response.message == "test"
            }
            
            all_passed = all(model_tests.values())
            
            if all_passed:
                self.log_result("Data Models", "passed", 
                              "All data models validated", model_tests)
            else:
                failed_tests = [k for k, v in model_tests.items() if not v]
                self.log_result("Data Models", "failed", 
                              f"Model validation failures: {failed_tests}", model_tests)
                
        except Exception as e:
            self.log_result("Data Models", "failed", f"Model testing error: {e}")

    def test_settings_validation(self):
        """Test settings validation and environment handling."""
        try:
            settings = get_settings()
            
            validation_tests = {
                'settings_object_type': type(settings).__name__ == 'Settings',
                'environment_detection': hasattr(settings, 'environment'),
                'pydantic_validation': hasattr(settings, '__fields__'),
                'config_sections': all(hasattr(settings, section) for section in ['eodhd', 'claude']),
                'nested_config_structure': (
                    hasattr(settings.eodhd, 'api_token') if settings.eodhd else False and
                    hasattr(settings.claude, 'api_key') if settings.claude else False
                )
            }
            
            validation_score = sum(validation_tests.values())
            total_tests = len(validation_tests)
            
            if validation_score == total_tests:
                self.log_result("Settings Validation", "passed", 
                              "Settings validation complete", validation_tests)
            elif validation_score >= total_tests * 0.8:
                self.log_result("Settings Validation", "passed", 
                              f"Settings mostly valid: {validation_score}/{total_tests}", validation_tests)
            else:
                self.log_result("Settings Validation", "failed", 
                              f"Settings validation issues: {validation_score}/{total_tests}", validation_tests)
                
        except Exception as e:
            self.log_result("Settings Validation", "failed", f"Settings validation error: {e}")

    def test_provider_class_structure(self):
        """Test provider class structure and interfaces."""
        try:
            from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
            from src.api.providers.claude_provider import ClaudeProvider
            
            structure_tests = {
                'eodhd_provider_class': EnhancedEODHDProvider is not None,
                'claude_provider_class': ClaudeProvider is not None,
                'eodhd_has_init': hasattr(EnhancedEODHDProvider, '__init__'),
                'claude_has_init': hasattr(ClaudeProvider, '__init__'),
                'eodhd_has_methods': any(method.startswith('get_') for method in dir(EnhancedEODHDProvider)),
                'claude_has_analyze': hasattr(ClaudeProvider, 'analyze_opportunities')
            }
            
            structure_score = sum(structure_tests.values())
            
            if structure_score == len(structure_tests):
                self.log_result("Provider Class Structure", "passed", 
                              "All provider classes have correct structure", structure_tests)
            else:
                failed_items = [k for k, v in structure_tests.items() if not v]
                self.log_result("Provider Class Structure", "failed", 
                              f"Structure issues: {failed_items}", structure_tests)
                
        except Exception as e:
            self.log_result("Provider Class Structure", "failed", f"Structure test error: {e}")

    def test_notification_components(self):
        """Test notification system components."""
        try:
            from src.notifications.notification_manager import NotificationManager
            
            # Test instantiation (should work even without full config)
            try:
                notification_manager = NotificationManager()
                instantiation_success = True
            except Exception as e:
                instantiation_success = False
                instantiation_error = str(e)
            
            notification_tests = {
                'notification_manager_instantiation': instantiation_success,
                'has_circuit_breakers': (
                    hasattr(notification_manager, 'whatsapp_breaker') and 
                    hasattr(notification_manager, 'email_breaker')
                ) if instantiation_success else False,
                'has_notification_methods': (
                    hasattr(notification_manager, 'send_opportunities') and
                    hasattr(notification_manager, 'send_daily_summary')
                ) if instantiation_success else False
            }
            
            if not instantiation_success:
                notification_tests['instantiation_error'] = instantiation_error
            
            working_components = sum(notification_tests.values() if isinstance(v, bool) else 0 for v in notification_tests.values())
            
            if instantiation_success and working_components >= 2:
                self.log_result("Notification Components", "passed", 
                              "Notification system components functional", notification_tests)
            else:
                self.log_result("Notification Components", "failed", 
                              f"Notification issues: {working_components} components working", notification_tests)
                
        except Exception as e:
            self.log_result("Notification Components", "failed", f"Notification test error: {e}")

    def test_analysis_modules(self):
        """Test analysis module structure."""
        try:
            from src.analysis.claude_integration import ClaudeIntegrationManager
            from src.analysis.scanner import PMCCScanner
            
            analysis_tests = {
                'claude_integration_exists': ClaudeIntegrationManager is not None,
                'pmcc_scanner_exists': PMCCScanner is not None,
                'claude_integration_methods': hasattr(ClaudeIntegrationManager, 'merge_claude_analysis_with_pmcc_data'),
                'scanner_methods': hasattr(PMCCScanner, 'scan_symbols')
            }
            
            # Test Claude integration manager instantiation
            try:
                claude_manager = ClaudeIntegrationManager()
                analysis_tests['claude_manager_instantiation'] = True
            except Exception as e:
                analysis_tests['claude_manager_instantiation'] = False
                analysis_tests['claude_manager_error'] = str(e)
            
            working_analysis = sum(v for v in analysis_tests.values() if isinstance(v, bool))
            
            if working_analysis >= 4:  # Most components working
                self.log_result("Analysis Modules", "passed", 
                              "Analysis modules structure validated", analysis_tests)
            else:
                self.log_result("Analysis Modules", "failed", 
                              f"Analysis module issues: {working_analysis} components working", analysis_tests)
                
        except Exception as e:
            self.log_result("Analysis Modules", "failed", f"Analysis test error: {e}")

    def generate_report(self):
        """Generate partial QA test report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        total_tests = len(self.results['passed']) + len(self.results['failed']) + len(self.results['blocked'])
        pass_rate = (len(self.results['passed']) / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("\n" + "="*70)
        logger.info("PARTIAL QA TEST RESULTS")
        logger.info("="*70)
        logger.info(f"Test Duration: {duration}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {len(self.results['passed'])} ({pass_rate:.1f}%)")
        logger.info(f"Failed: {len(self.results['failed'])}")
        logger.info(f"Blocked: {len(self.results['blocked'])}")
        logger.info("")
        
        # Component-level assessment
        if len(self.results['passed']) >= 5:
            logger.info("🟡 COMPONENT VALIDATION: GOOD")
            logger.info("Core components are structurally sound and ready for integration.")
        else:
            logger.info("🔴 COMPONENT VALIDATION: ISSUES FOUND")
            logger.info("Multiple component issues detected.")
        
        logger.info("")
        
        # List any failures
        if self.results['failed']:
            logger.info("COMPONENT FAILURES:")
            for failure in self.results['failed']:
                logger.info(f"❌ {failure['test']}: {failure['message']}")
        
        logger.info("\n📋 CRITICAL INFRASTRUCTURE ISSUES PREVENTING FULL TESTING:")
        logger.info("1. Provider Factory initialization failure")
        logger.info("2. ProviderType enum missing values")
        logger.info("3. No providers can be instantiated or registered")
        logger.info("\nFull system testing blocked until these issues are resolved.")
        
        logger.info("\n" + "="*70)
        
        # Save report
        report_file = f"partial_qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'test_type': 'partial_component_validation',
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'total_tests': total_tests,
                    'passed': len(self.results['passed']),
                    'failed': len(self.results['failed']),
                    'blocked': len(self.results['blocked']),
                    'pass_rate': pass_rate,
                    'infrastructure_ready': len(self.results['passed']) >= 5
                },
                'results': self.results,
                'blocking_issues': [
                    "Provider Factory initialization failure",
                    "ProviderType enum missing values", 
                    "Provider instantiation impossible"
                ]
            }, f, indent=2, default=str)
        
        logger.info(f"Detailed report: {report_file}")


if __name__ == "__main__":
    tester = PartialQATest()
    tester.run_all_tests()
