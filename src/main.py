"""
Main application entry point for PMCC Scanner.

Orchestrates the complete application lifecycle including initialization,
scheduled scanning, error handling, and graceful shutdown.
"""

import os
import sys
import signal
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
import json

try:
    # Try absolute imports first (when running from project root)
    from src.config import get_settings, Settings, Environment
    from src.utils.logger import get_logger, get_performance_logger
    from src.utils.error_handler import get_error_handler, monitor_performance, handle_errors
    
    # Application factory
    from src.app_factory import create_app, ApplicationContainer
    
    # Core components for configuration
    from src.analysis.scanner import ScanConfiguration, ScanResults
    from src.analysis.stock_screener import ScreeningCriteria
    from src.analysis.options_analyzer import LEAPSCriteria, ShortCallCriteria
    
    # Models
    from src.models.pmcc_models import PMCCCandidate

except ImportError:
    # Fallback: Add src directory to path and use relative imports
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        # Configuration and utilities
        from config import get_settings, Settings, Environment
        from utils.logger import get_logger, get_performance_logger
        from utils.error_handler import get_error_handler, monitor_performance, handle_errors
        
        # Application factory
        from app_factory import create_app, ApplicationContainer
        
        # Core components for configuration
        from analysis.scanner import ScanConfiguration, ScanResults
        from analysis.stock_screener import ScreeningCriteria
        from analysis.options_analyzer import LEAPSCriteria, ShortCallCriteria
        
        # Models
        from models.pmcc_models import PMCCCandidate
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all dependencies are installed and the working directory is correct.")
        sys.exit(1)


class PMCCApplication:
    """Main PMCC Scanner application."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """
        Initialize the PMCC Scanner application.
        
        Args:
            config_override: Optional configuration overrides
        """
        # Apply configuration overrides if provided
        if config_override:
            for key, value in config_override.items():
                os.environ[key] = str(value)
        
        # Create application container
        self.container = create_app()
        self.settings = self.container.settings
        
        # Get components from container
        self.logger = self.container.logger
        self.perf_logger = get_performance_logger()
        self.error_handler = get_error_handler()
        
        # Application state
        self.initialized = False
        self.running = False
        self.shutdown_requested = False
        self.last_scan_result: Optional[ScanResults] = None
        self.startup_time = datetime.now()
        self.health_server: Optional[threading.Thread] = None
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info(
            f"PMCC Scanner application initialized",
            extra={
                "version": self.settings.app_version,
                "environment": self.settings.environment.value,
                "debug": self.settings.debug
            }
        )
    
    @monitor_performance("application", "initialize")
    def initialize(self) -> bool:
        """
        Initialize all application components.
        
        Returns:
            True if initialization successful
        """
        if self.initialized:
            self.logger.warning("Application already initialized")
            return True
        
        try:
            self.logger.info("Initializing application components...")
            
            # Initialize container components
            if not self.container.initialize():
                self.logger.error("Failed to initialize application container")
                return False
            
            # Start health check server if enabled
            if self.settings.monitoring.health_check_enabled:
                self._start_health_server()
            
            self.initialized = True
            self.logger.info("All components initialized successfully")
            
            return True
            
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "initialize"})
            return False
    
    @monitor_performance("application", "start")
    def start(self) -> bool:
        """
        Start the application.
        
        Returns:
            True if started successfully
        """
        if not self.initialized:
            if not self.initialize():
                return False
        
        if self.running:
            self.logger.warning("Application is already running")
            return True
        
        try:
            self.logger.info("Starting PMCC Scanner application...")
            
            # Start scheduler if enabled
            if self.settings.scan.schedule_enabled and self.container.scheduler:
                self.container.scheduler.start()
                self.logger.info("Scheduler started")
            
            self.running = True
            
            # Send startup notification
            if self.container.notification_manager:
                try:
                    self.container.notification_manager.send_system_alert(
                        f"PMCC Scanner started successfully in {self.settings.environment.value} environment",
                        severity="info"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to send startup notification: {e}")
            
            self.logger.info("PMCC Scanner application started successfully")
            return True
            
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "start"})
            return False
    
    def stop(self):
        """Stop the application gracefully."""
        if not self.running:
            self.logger.info("Application is not running")
            return
        
        self.logger.info("Stopping PMCC Scanner application...")
        self.shutdown_requested = True
        
        try:
            # Send shutdown notification
            if self.container.notification_manager:
                try:
                    self.container.notification_manager.send_system_alert(
                        "PMCC Scanner shutting down",
                        severity="info"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to send shutdown notification: {e}")
            
            # Shutdown container components
            self.container.shutdown()
            
            self.running = False
            self.logger.info("PMCC Scanner application stopped")
            
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "stop"})
    
    @monitor_performance("application", "scan")
    def run_scan(self) -> Optional[ScanResults]:
        """
        Execute a single PMCC scan.
        
        Returns:
            Scan results or None if failed
        """
        if not self.initialized:
            self.logger.error("Application not initialized")
            return None
        
        self.logger.info("Starting PMCC scan...")
        
        try:
            with self.perf_logger.timer("pmcc_scan"):
                # Create scan configuration
                scan_config = self._create_scan_config()
                
                # Execute scan using container's scanner
                results = self.container.scanner.scan(scan_config)
                
                # Store results
                self.last_scan_result = results
                
                # Export results if enabled
                if self.settings.scan.export_results:
                    self._export_scan_results(results)
                
                # Send notifications (always send daily summary regardless of opportunities found)
                if self.container.notification_manager:
                    self._send_scan_notifications(results)
                
                # Log summary
                self._log_scan_summary(results)
                
                return results
        
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "scan"})
            
            # Send error notification
            if self.container.notification_manager:
                try:
                    self.container.notification_manager.send_system_alert(
                        f"PMCC scan failed: {str(e)}",
                        severity="error"
                    )
                except Exception as notify_error:
                    self.logger.error(f"Failed to send error notification: {notify_error}")
            
            return None
    
    def run_once(self) -> bool:
        """
        Run a single scan and exit.
        
        Returns:
            True if successful
        """
        if not self.initialize():
            return False
        
        result = self.run_scan()
        return result is not None and not result.errors
    
    def run_daemon(self):
        """Run as a daemon with scheduled scans."""
        if not self.start():
            sys.exit(1)
        
        try:
            self.logger.info("Running in daemon mode...")
            
            # Keep running until shutdown requested
            while not self.shutdown_requested:
                import time
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get application status.
        
        Returns:
            Status information dictionary
        """
        status = {
            'application': {
                'name': self.settings.app_name,
                'version': self.settings.app_version,
                'environment': self.settings.environment.value,
                'initialized': self.initialized,
                'running': self.running,
                'startup_time': self.startup_time.isoformat(),
                'uptime_seconds': (datetime.now() - self.startup_time).total_seconds()
            }
        }
        
        # Add container component status
        if self.initialized:
            status.update(self.container.get_component_status())
        
        # Add scheduler status if available
        if self.container.scheduler:
            status['scheduler'] = self.container.scheduler.get_scheduler_stats()
        
        # Add last scan info if available
        if self.last_scan_result:
            status['last_scan'] = {
                'scan_id': self.last_scan_result.scan_id,
                'completed_at': self.last_scan_result.completed_at.isoformat() if self.last_scan_result.completed_at else None,
                'duration_seconds': self.last_scan_result.total_duration_seconds,
                'opportunities_found': self.last_scan_result.opportunities_found,
                'errors': len(self.last_scan_result.errors),
                'warnings': len(self.last_scan_result.warnings)
            }
        
        # Add connectivity status
        if self.container.notification_manager:
            status['connectivity'] = self.container.notification_manager.test_connectivity()
        
        # Add error handler metrics
        status['error_metrics'] = self.error_handler.get_error_summary(hours=24)
        status['performance_metrics'] = self.error_handler.get_performance_summary(hours=24)
        
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        base_health = {
            'timestamp': datetime.now().isoformat(),
            'application': {
                'healthy': self.initialized and self.running,
                'details': 'Application running normally' if self.initialized and self.running else 'Application not ready'
            }
        }
        
        # Get container health check if initialized
        if self.initialized:
            container_health = self.container.health_check()
            base_health.update(container_health)
        else:
            base_health.update({
                'healthy': False,
                'overall_status': 'unhealthy',
                'components': {},
                'unhealthy_components': ['application']
            })
        
        # Add error handler health metrics
        error_health = self.error_handler.get_health_status()
        base_health['system_health'] = error_health.to_dict()
        
        return base_health
    
    
    def _create_scan_config(self) -> ScanConfiguration:
        """Create scan configuration from settings."""
        # Parse custom symbols if provided
        custom_symbols = None
        if self.settings.scan.custom_symbols:
            custom_symbols = [s.strip().upper() for s in self.settings.scan.custom_symbols.split(',')]
        
        # Create screening criteria
        # Convert market cap from actual dollars to millions for ScreeningCriteria
        min_market_cap_millions = self.settings.scan.min_market_cap / Decimal('1000000') if self.settings.scan.min_market_cap else Decimal('50')
        max_market_cap_millions = self.settings.scan.max_market_cap / Decimal('1000000') if self.settings.scan.max_market_cap else Decimal('5000')
        
        screening_criteria = ScreeningCriteria(
            min_price=self.settings.scan.min_stock_price,
            max_price=self.settings.scan.max_stock_price,
            min_daily_volume=self.settings.scan.min_volume,
            min_market_cap=min_market_cap_millions,
            max_market_cap=max_market_cap_millions
        )
        
        # Create LEAPS criteria
        leaps_criteria = LEAPSCriteria(
            min_dte=self.settings.scan.leaps_min_dte,
            max_dte=self.settings.scan.leaps_max_dte,
            min_delta=self.settings.scan.leaps_min_delta,
            max_delta=self.settings.scan.leaps_max_delta
        )
        
        # Create short call criteria
        short_criteria = ShortCallCriteria(
            min_dte=self.settings.scan.short_min_dte,
            max_dte=self.settings.scan.short_max_dte,
            min_delta=self.settings.scan.short_min_delta,
            max_delta=self.settings.scan.short_max_delta
        )
        
        # Determine Claude availability
        claude_available = (
            self.settings.claude and 
            self.settings.claude.is_configured and 
            self.settings.scan.claude_analysis_enabled
        )
        
        # Determine enhanced data collection availability
        enhanced_data_available = (
            self.settings.eodhd and 
            self.settings.scan.enhanced_data_collection_enabled
        )
        
        return ScanConfiguration(
            universe=self.settings.scan.default_universe,
            custom_symbols=custom_symbols,
            max_stocks_to_screen=self.settings.scan.max_stocks_to_screen,
            screening_criteria=screening_criteria,
            leaps_criteria=leaps_criteria,
            short_criteria=short_criteria,
            max_risk_per_trade=self.settings.scan.max_risk_per_trade,
            risk_free_rate=self.settings.scan.risk_free_rate,
            max_opportunities=self.settings.scan.max_opportunities,
            best_per_symbol_only=self.settings.scan.best_per_symbol_only,
            min_total_score=self.settings.scan.min_total_score,
            options_source=self.settings.scan.options_source,
            use_hybrid_flow=self.settings.scan.use_hybrid_flow,
            # AI Enhancement settings (Phase 3)
            claude_analysis_enabled=claude_available,
            enhanced_data_collection_enabled=enhanced_data_available,
            top_n_opportunities=self.settings.scan.top_n_opportunities,
            min_claude_confidence=self.settings.scan.min_claude_confidence,
            min_combined_score=self.settings.scan.min_combined_score,
            require_all_data_sources=self.settings.scan.require_all_data_sources
        )
    
    def _export_scan_results(self, results: ScanResults):
        """Export scan results to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pmcc_scan_{timestamp}.{self.settings.scan.export_format}"
            
            # Use the scanner's export_results method which handles directory creation
            exported_file = self.container.scanner.export_results(
                results, 
                self.settings.scan.export_format, 
                filename,
                self.settings.data_dir
            )
            self.logger.info(f"Scan results exported to {exported_file}")
            
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "export_results"})
    
    def _send_scan_notifications(self, results: ScanResults):
        """Send notifications for scan results."""
        try:
            # Prepare scan metadata for the notification
            scan_metadata = {
                'duration_seconds': results.total_duration_seconds or 0,
                'stocks_screened': results.stocks_screened,
                'stocks_passed_screening': results.stocks_passed_screening,
                'options_analyzed': results.options_analyzed,
                'opportunities_found': results.opportunities_found
            }
            
            # Always send comprehensive daily summary (includes ALL opportunities or none)
            # This replaces the previous logic of individual vs multiple notifications
            all_opportunities = results.top_opportunities or []
            
            # Extract enhanced data for AI-enhanced notifications
            enhanced_data = self._extract_enhanced_data_for_notifications(all_opportunities)
            
            self.container.notification_manager.send_multiple_opportunities(
                all_opportunities, 
                scan_metadata,
                enhanced_data=enhanced_data
            )
        
        except Exception as e:
            self.error_handler.report_error(e, "application", context={"operation": "send_notifications"})
    
    def _convert_analysis_to_dict(self, analysis: 'PMCCAnalysis') -> Dict[str, Any]:
        """
        Convert PMCCAnalysis object to dictionary format for email formatter.
        
        Args:
            analysis: PMCCAnalysis object
            
        Returns:
            Dictionary with analysis data
        """
        if not analysis:
            return {}
        
        return {
            'long_call': {
                'option_symbol': analysis.long_call.option_symbol,
                'strike': float(analysis.long_call.strike),
                'expiration': analysis.long_call.expiration,
                'dte': analysis.long_call.dte,
                'bid': float(analysis.long_call.bid) if analysis.long_call.bid else None,
                'ask': float(analysis.long_call.ask) if analysis.long_call.ask else None,
                'delta': float(analysis.long_call.delta) if analysis.long_call.delta else None
            },
            'short_call': {
                'option_symbol': analysis.short_call.option_symbol,
                'strike': float(analysis.short_call.strike),
                'expiration': analysis.short_call.expiration,
                'dte': analysis.short_call.dte,
                'bid': float(analysis.short_call.bid) if analysis.short_call.bid else None,
                'ask': float(analysis.short_call.ask) if analysis.short_call.ask else None,
                'delta': float(analysis.short_call.delta) if analysis.short_call.delta else None
            }
        }
    
    def _extract_enhanced_data_for_notifications(self, opportunities: List['PMCCCandidate']) -> Optional[List[Dict[str, Any]]]:
        """
        Extract enhanced data with AI insights from PMCCCandidate objects for notifications.
        
        This converts PMCCCandidate objects with AI insights to the dictionary format
        expected by the email formatters for AI-enhanced notifications.
        
        Args:
            opportunities: List of PMCCCandidate objects with potential AI insights
            
        Returns:
            List of dictionaries with AI insights, or None if no AI data available
        """
        if not opportunities:
            return None
        
        enhanced_data = []
        has_ai_insights = False
        
        for candidate in opportunities:
            # Check if candidate has AI insights
            if not candidate.ai_insights and not candidate.claude_score:
                continue
            
            has_ai_insights = True
            
            # Extract traditional PMCC metrics
            net_debit = float(candidate.analysis.net_debit) if candidate.analysis.net_debit else 0.0
            max_profit = (
                float(candidate.analysis.risk_metrics.max_profit) 
                if candidate.analysis.risk_metrics and candidate.analysis.risk_metrics.max_profit 
                else 0.0
            )
            
            # Create enhanced data dictionary
            enhanced_opportunity = {
                'symbol': candidate.symbol,
                'underlying_price': float(candidate.underlying_price),
                'net_debit': net_debit,
                'max_profit': max_profit,
                
                # Traditional PMCC scoring
                'pmcc_score': float(candidate.total_score) if candidate.total_score else 0.0,
                'liquidity_score': float(candidate.liquidity_score) if candidate.liquidity_score else 0.0,
                
                # AI Analysis Results
                'claude_score': candidate.claude_score or 0.0,
                'combined_score': candidate.combined_score or float(candidate.total_score or 0.0),
                'claude_confidence': candidate.claude_confidence or 0.0,
                'claude_reasoning': candidate.claude_reasoning or "",
                'ai_recommendation': candidate.ai_recommendation or "hold",
                'claude_analyzed': bool(candidate.ai_insights or candidate.claude_score),
                
                # AI insights (the critical missing piece!)
                'ai_insights': candidate.ai_insights or {},
                
                # Include the full analysis object with contract details
                # Convert PMCCAnalysis object to dictionary format for email formatter
                'analysis': self._convert_analysis_to_dict(candidate.analysis) if hasattr(candidate, 'analysis') and candidate.analysis else None
            }
            
            enhanced_data.append(enhanced_opportunity)
        
        # Return enhanced data only if we found AI insights
        if has_ai_insights and enhanced_data:
            self.logger.info(f"Extracted enhanced data with AI insights for {len(enhanced_data)} opportunities")
            return enhanced_data
        else:
            self.logger.debug("No AI insights found in opportunities, returning None for enhanced_data")
            return None
    
    def _log_scan_summary(self, results: ScanResults):
        """Log scan summary."""
        summary = self.container.scanner.get_scan_summary(results)
        
        self.logger.info(
            "PMCC scan completed",
            extra={
                "scan_id": results.scan_id,
                "duration_seconds": results.total_duration_seconds,
                "opportunities_found": results.opportunities_found,
                "stocks_screened": results.stocks_screened,
                "success_rate": summary['statistics']['success_rate'],
                "errors": len(results.errors),
                "warnings": len(results.warnings)
            }
        )
    
    def _start_health_server(self):
        """Start health check HTTP server."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            class HealthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == self.server.health_path:
                        health = self.server.app.health_check()
                        
                        self.send_response(200 if health['healthy'] else 503)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(health, indent=2).encode())
                    
                    elif self.path == '/status':
                        status = self.server.app.get_status()
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(status, indent=2, default=str).encode())
                    
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    # Suppress HTTP server logs
                    pass
            
            server = HTTPServer(('0.0.0.0', self.settings.monitoring.health_check_port), HealthHandler)
            server.app = self
            server.health_path = self.settings.monitoring.health_check_path
            
            def run_server():
                self.logger.info(f"Health check server listening on port {self.settings.monitoring.health_check_port}")
                server.serve_forever()
            
            self.health_server = threading.Thread(target=run_server, daemon=True)
            self.health_server.start()
        
        except Exception as e:
            self.logger.warning(f"Failed to start health check server: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PMCC Scanner Application")
    parser.add_argument("--mode", choices=["daemon", "once", "test"], default="daemon",
                       help="Run mode: daemon (scheduled), once (single scan), test (validation)")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--env", help="Environment override")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Log level override")
    parser.add_argument("--no-notifications", action="store_true",
                       help="Disable notifications")
    
    args = parser.parse_args()
    
    # Prepare configuration overrides
    config_override = {}
    
    if args.env:
        os.environ['ENVIRONMENT'] = args.env
    
    if args.log_level:
        os.environ['LOG_LEVEL'] = args.log_level
    
    if args.no_notifications:
        os.environ['NOTIFICATION_WHATSAPP_ENABLED'] = 'false'
        os.environ['NOTIFICATION_EMAIL_ENABLED'] = 'false'
    
    try:
        # Create and initialize application
        app = PMCCApplication(config_override)
        
        if args.mode == "test":
            # Test mode - validate configuration and connectivity
            print("🔧 Testing PMCC Scanner configuration...")
            
            if not app.initialize():
                print("❌ Initialization failed")
                return 1
            
            health = app.health_check()
            
            print(f"📊 Health check: {'✅ HEALTHY' if health['healthy'] else '❌ UNHEALTHY'}")
            
            for check_name, check_result in health['checks'].items():
                status = "✅" if check_result['healthy'] else "❌"
                print(f"   {check_name}: {status} {check_result['details']}")
            
            if health['healthy']:
                print("🎉 All systems operational!")
                return 0
            else:
                print("⚠️  Some issues detected. Please check configuration.")
                return 1
        
        elif args.mode == "once":
            # Single scan mode
            print("\n" + "=" * 80)
            print("🔍 PMCC SCANNER - SINGLE SCAN MODE")
            print("=" * 80 + "\n")
            
            success = app.run_once()
            
            if success:
                print("\n" + "=" * 80)
                print("✅ SCAN COMPLETED SUCCESSFULLY")
                if app.last_scan_result:
                    print(f"   🎯 Found {app.last_scan_result.opportunities_found} opportunities")
                    print(f"   📊 Analyzed {app.last_scan_result.options_analyzed} stocks")
                    print(f"   ⏱️  Duration: {app.last_scan_result.total_duration_seconds:.1f} seconds")
                print("=" * 80 + "\n")
                return 0
            else:
                print("\n" + "=" * 80)
                print("❌ SCAN FAILED")
                print("=" * 80 + "\n")
                return 1
        
        else:
            # Daemon mode (default)
            print("🚀 Starting PMCC Scanner daemon...")
            app.run_daemon()
            return 0
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return 0
    
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())