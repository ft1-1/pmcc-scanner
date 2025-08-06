"""
Application factory for PMCC Scanner.

Provides a centralized way to create and configure the application
with dependency injection and clean component interfaces.
"""

import os
import logging
from typing import Optional, Dict, Any, Protocol
from pathlib import Path

# Configuration and utilities
from src.config import Settings, get_settings
from src.utils.logger import setup_logging, get_logger
from src.utils.error_handler import initialize_error_handler, GlobalErrorHandler
from src.utils.scheduler import JobScheduler, create_daily_scan_scheduler

# Core components
from src.api.sync_marketdata_client import SyncMarketDataClient
from src.api.eodhd_client import EODHDClient
from src.analysis.scanner import PMCCScanner
from src.notifications.notification_manager import NotificationManager

# Provider factory components
from src.config.provider_config import ProviderConfigurationManager, DataProviderSettings
from src.api.provider_factory import SyncDataProviderFactory, FallbackStrategy
from src.api.data_provider import ProviderType


class ComponentInterface(Protocol):
    """Interface for application components."""
    
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status."""
        ...


class ApplicationContainer:
    """
    Dependency injection container for PMCC Scanner components.
    
    Manages component lifecycle and provides clean interfaces
    between different parts of the application.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize application container.
        
        Args:
            settings: Application settings (uses default if None)
        """
        self.settings = settings or get_settings()
        
        # Core components
        self._logger: Optional[logging.Logger] = None
        self._error_handler: Optional[GlobalErrorHandler] = None
        self._api_client: Optional[SyncMarketDataClient] = None  # Now optional
        self._eodhd_client: Optional[EODHDClient] = None
        self._scanner: Optional[PMCCScanner] = None
        self._notification_manager: Optional[NotificationManager] = None
        self._scheduler: Optional[JobScheduler] = None
        
        # Component registry
        self._components: Dict[str, Any] = {}
        self._initialized = False
    
    @property
    def logger(self) -> logging.Logger:
        """Get or create logger."""
        if self._logger is None:
            self._logger = self._create_logger()
        return self._logger
    
    @property
    def error_handler(self) -> GlobalErrorHandler:
        """Get or create error handler."""
        if self._error_handler is None:
            self._error_handler = self._create_error_handler()
        return self._error_handler
    
    @property
    def api_client(self) -> Optional[SyncMarketDataClient]:
        """Get or create API client (optional - deprecated)."""
        if self._api_client is None and hasattr(self.settings, 'marketdata') and self.settings.marketdata and self.settings.marketdata.api_token and self.settings.marketdata.api_token.strip():
            self._api_client = self._create_api_client()
        return self._api_client
    
    @property
    def eodhd_client(self) -> Optional[EODHDClient]:
        """Get or create EODHD client."""
        if self._eodhd_client is None and hasattr(self.settings, 'eodhd') and self.settings.eodhd.api_token:
            self._eodhd_client = self._create_eodhd_client()
        return self._eodhd_client
    
    @property
    def scanner(self) -> PMCCScanner:
        """Get or create PMCC scanner."""
        if self._scanner is None:
            self._scanner = self._create_scanner()
        return self._scanner
    
    @property
    def notification_manager(self) -> Optional[NotificationManager]:
        """Get or create notification manager."""
        if self._notification_manager is None:
            self._notification_manager = self._create_notification_manager()
        return self._notification_manager
    
    @property
    def scheduler(self) -> Optional[JobScheduler]:
        """Get or create scheduler."""
        if self._scheduler is None and self.settings.scan.schedule_enabled:
            self._scheduler = self._create_scheduler()
        return self._scheduler
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            self.logger.info("Initializing application components...")
            
            # Initialize core components in order
            self.error_handler  # Initialize error handler first
            
            # EODHD client is now required for scanner
            if not self.eodhd_client:
                raise ValueError("EODHD client is required for scanner operation")
            
            self.scanner        # Initialize scanner
            
            # Initialize optional components
            if self.settings.notifications.whatsapp_enabled or self.settings.notifications.email_enabled:
                self.notification_manager
            
            if self.settings.scan.schedule_enabled:
                self.scheduler
            
            # Register all components
            self._register_components()
            
                # Validate all components
            if not self._validate_components():
                return False
            
            self._initialized = True
            self.logger.info("All application components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application components: {e}", exc_info=True)
            return False
    
    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status of all components.
        
        Returns:
            Component status dictionary
        """
        status = {
            'initialized': self._initialized,
            'components': {}
        }
        
        for name, component in self._components.items():
            try:
                if hasattr(component, 'get_status'):
                    component_status = component.get_status()
                elif hasattr(component, 'is_healthy'):
                    component_status = {'healthy': component.is_healthy()}
                else:
                    component_status = {'available': True}
                
                status['components'][name] = component_status
                
            except Exception as e:
                status['components'][name] = {
                    'error': str(e),
                    'healthy': False
                }
        
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        health = {
            'healthy': True,
            'components': {},
            'overall_status': 'healthy'
        }
        
        unhealthy_components = []
        
        for name, component in self._components.items():
            try:
                if hasattr(component, 'is_healthy'):
                    component_healthy = component.is_healthy()
                    health['components'][name] = {
                        'healthy': component_healthy,
                        'status': 'healthy' if component_healthy else 'unhealthy'
                    }
                    
                    if not component_healthy:
                        unhealthy_components.append(name)
                        
                else:
                    # Assume healthy if no health check method
                    health['components'][name] = {
                        'healthy': True,
                        'status': 'healthy'
                    }
                    
            except Exception as e:
                health['components'][name] = {
                    'healthy': False,
                    'status': 'error',
                    'error': str(e)
                }
                unhealthy_components.append(name)
        
        # Determine overall health
        if unhealthy_components:
            # Critical components
            critical_components = ['api_client', 'scanner']
            critical_unhealthy = [c for c in unhealthy_components if c in critical_components]
            
            if critical_unhealthy:
                health['healthy'] = False
                health['overall_status'] = 'unhealthy'
            else:
                health['healthy'] = True
                health['overall_status'] = 'degraded'
            
            health['unhealthy_components'] = unhealthy_components
        
        return health
    
    def shutdown(self):
        """Shutdown all components gracefully."""
        self.logger.info("Shutting down application components...")
        
        # Shutdown scheduler first
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=True)
                self.logger.info("Scheduler shutdown complete")
            except Exception as e:
                self.logger.error(f"Error shutting down scheduler: {e}")
        
        # Clean up error handler
        if self._error_handler:
            try:
                self._error_handler.cleanup_old_data()
                self.logger.info("Error handler cleanup complete")
            except Exception as e:
                self.logger.error(f"Error during error handler cleanup: {e}")
        
        self.logger.info("Application shutdown complete")
    
    def _create_logger(self) -> logging.Logger:
        """Create and configure logger."""
        logging_config = {
            'level': self.settings.logging.level.value,
            'enable_file_logging': self.settings.logging.enable_file_logging,
            'log_file': self.settings.logging.log_file,
            'max_bytes': self.settings.logging.max_bytes,
            'backup_count': self.settings.logging.backup_count,
            'enable_console_logging': self.settings.logging.enable_console_logging,
            'console_level': self.settings.logging.console_level.value,
            'enable_json_logging': self.settings.logging.enable_json_logging,
            'include_extra_fields': self.settings.logging.include_extra_fields,
            'syslog_enabled': self.settings.logging.syslog_enabled,
            'syslog_host': self.settings.logging.syslog_host,
            'syslog_port': self.settings.logging.syslog_port,
        }
        
        return setup_logging(logging_config)
    
    def _create_error_handler(self) -> GlobalErrorHandler:
        """Create and configure error handler."""
        return initialize_error_handler(self.logger)
    
    def _create_api_client(self) -> Optional[SyncMarketDataClient]:
        """Create and configure API client (deprecated)."""
        if not hasattr(self.settings, 'marketdata') or not self.settings.marketdata or not self.settings.marketdata.api_token or not self.settings.marketdata.api_token.strip():
            self.logger.info("MarketData API not configured - skipping client creation")
            return None
        
        self.logger.warning("Creating MarketData API client (deprecated - EODHD is now preferred)")
        
        client = SyncMarketDataClient(
            api_token=self.settings.marketdata.api_token,
            base_url=self.settings.marketdata.base_url
        )
        
        self.logger.info("API client created successfully")
        return client
    
    def _create_eodhd_client(self) -> EODHDClient:
        """Create and configure EODHD client."""
        self.logger.info("Creating EODHD API client...")
        
        client = EODHDClient(
            api_token=self.settings.eodhd.api_token,
            base_url=self.settings.eodhd.base_url,
            enable_tradetime_filtering=self.settings.scan.enable_tradetime_filtering,
            tradetime_lookback_days=self.settings.scan.tradetime_lookback_days,
            custom_tradetime_date=self.settings.scan.custom_tradetime_date
        )
        
        self.logger.info("EODHD client created successfully")
        return client
    
    def _create_scanner(self) -> PMCCScanner:
        """Create and configure PMCC scanner."""
        self.logger.info("Creating PMCC scanner...")
        
        # Check if we should use the new provider factory system
        use_provider_factory = getattr(self.settings, 'use_provider_factory', True)
        
        if use_provider_factory:
            return self._create_scanner_with_provider_factory()
        else:
            return self._create_scanner_legacy()
    
    def _create_scanner_with_provider_factory(self) -> PMCCScanner:
        """Create scanner using the provider factory system."""
        self.logger.info("Creating PMCC scanner with provider factory...")
        
        try:
            # Configure provider settings based on application settings
            # Use settings from environment if available, otherwise use defaults
            if hasattr(self.settings, 'providers'):
                # Use settings from the environment
                provider_settings = self.settings.providers
            else:
                # Create default settings
                provider_settings = DataProviderSettings(
                    primary_provider=ProviderType.EODHD,  # EODHD for screening
                    fallback_strategy=FallbackStrategy.OPERATION_SPECIFIC,
                    preferred_stock_screener=ProviderType.EODHD,
                    preferred_options_provider=ProviderType.MARKETDATA if hasattr(self.settings, 'marketdata') and self.settings.marketdata.api_token else ProviderType.EODHD,
                    preferred_quotes_provider=ProviderType.MARKETDATA if hasattr(self.settings, 'marketdata') and self.settings.marketdata.api_token else ProviderType.EODHD,
                    preferred_greeks_provider=ProviderType.MARKETDATA if hasattr(self.settings, 'marketdata') and self.settings.marketdata.api_token else ProviderType.EODHD,
                    health_check_interval_seconds=300,
                    max_concurrent_requests_per_provider=10,
                    prioritize_cost_efficiency=True,
                    max_daily_api_credits=10000
                )
            
            # Create scanner with provider factory
            scanner = PMCCScanner.create_with_provider_factory(provider_settings)
            
            # Validate provider configuration
            provider_status = scanner.get_provider_status()
            available_providers = []
            
            if 'config_summary' in provider_status:
                for provider, info in provider_status['config_summary'].get('providers', {}).items():
                    if info.get('available'):
                        available_providers.append(provider)
            
            if not available_providers:
                raise ValueError("No data providers are available. Check API token configuration.")
            
            self.logger.info(f"PMCC scanner created with provider factory. Available providers: {', '.join(available_providers)}")
            return scanner
            
        except Exception as e:
            self.logger.warning(f"Failed to create scanner with provider factory: {e}")
            self.logger.info("Falling back to legacy scanner creation...")
            return self._create_scanner_legacy()
    
    def _create_scanner_legacy(self) -> PMCCScanner:
        """Create scanner using legacy method for backward compatibility."""
        self.logger.info("Creating PMCC scanner with legacy method...")
        
        if not self.eodhd_client:
            raise ValueError("EODHD client is required for scanner")
        
        # Pass EODHD client as primary and configuration for comprehensive options processing
        scanner = PMCCScanner(
            eodhd_client=self.eodhd_client, 
            api_client=self.api_client,
            eodhd_config=self.settings.eodhd  # Pass EODHD configuration for batch processing
        )
        
        self.logger.info("PMCC scanner created successfully with legacy method")
        return scanner
    
    def _create_notification_manager(self) -> Optional[NotificationManager]:
        """Create and configure notification manager."""
        try:
            self.logger.info("Creating notification manager...")
            
            manager = NotificationManager.create_from_env()
            
            # Test connectivity
            connectivity = manager.test_connectivity()
            active_channels = [channel for channel, status in connectivity.items() if status]
            
            if not active_channels:
                self.logger.warning("No notification channels are available")
                return None
            else:
                self.logger.info(f"Notification manager created with channels: {active_channels}")
                return manager
        
        except Exception as e:
            self.logger.warning(f"Failed to create notification manager: {e}")
            return None
    
    def _create_scheduler(self) -> Optional[JobScheduler]:
        """Create and configure job scheduler."""
        try:
            self.logger.info("Creating job scheduler...")
            
            # Create scan function that uses this container's scanner
            def scan_function():
                return self.scanner.scan()
            
            scheduler = create_daily_scan_scheduler(
                scan_function=scan_function,
                scan_time=self.settings.scan.scan_time,
                timezone=self.settings.scan.timezone,
                logger=self.logger
            )
            
            self.logger.info(f"Scheduler created for daily scans at {self.settings.scan.scan_time}")
            return scheduler
        
        except Exception as e:
            self.logger.error(f"Failed to create scheduler: {e}")
            return None
    
    def _register_components(self):
        """Register all components in the registry."""
        if self._logger:
            self._components['logger'] = self._logger
        
        if self._error_handler:
            self._components['error_handler'] = self._error_handler
        
        if self._api_client:
            self._components['api_client'] = self._api_client
        
        if self._eodhd_client:
            self._components['eodhd_client'] = self._eodhd_client
        
        if self._scanner:
            self._components['scanner'] = self._scanner
        
        if self._notification_manager:
            self._components['notification_manager'] = self._notification_manager
        
        if self._scheduler:
            self._components['scheduler'] = self._scheduler
    
    def _validate_components(self) -> bool:
        """Validate that all required components are working."""
        # Required components (EODHD client and scanner are now required)
        required_components = ['eodhd_client', 'scanner']
        
        for component_name in required_components:
            if component_name not in self._components:
                self.logger.error(f"Required component '{component_name}' not initialized")
                return False
            
            component = self._components[component_name]
            
            # Test if component has basic functionality
            try:
                if hasattr(component, 'is_healthy'):
                    if not component.is_healthy():
                        self.logger.error(f"Component '{component_name}' health check failed")
                        return False
                
            except Exception as e:
                self.logger.error(f"Error validating component '{component_name}': {e}")
                return False
        
        return True


class ApplicationFactory:
    """Factory for creating configured PMCC Scanner applications."""
    
    @staticmethod
    def create_container(settings: Optional[Settings] = None) -> ApplicationContainer:
        """
        Create application container with components.
        
        Args:
            settings: Application settings
            
        Returns:
            Configured ApplicationContainer
        """
        return ApplicationContainer(settings)
    
    @staticmethod
    def create_production_app() -> ApplicationContainer:
        """
        Create production-ready application.
        
        Returns:
            Production ApplicationContainer
        """
        # Force production environment
        os.environ['ENVIRONMENT'] = 'production'
        
        # Load production settings
        from config import reload_settings
        settings = reload_settings()
        
        if not settings.is_production:
            raise ValueError("Failed to configure production environment")
        
        return ApplicationFactory.create_container(settings)
    
    @staticmethod
    def create_development_app() -> ApplicationContainer:
        """
        Create development application.
        
        Returns:
            Development ApplicationContainer
        """
        # Force development environment
        os.environ['ENVIRONMENT'] = 'development'
        
        # Load development settings
        from config import reload_settings
        settings = reload_settings()
        
        return ApplicationFactory.create_container(settings)
    
    @staticmethod
    def create_test_app() -> ApplicationContainer:
        """
        Create test application with minimal configuration.
        
        Returns:
            Test ApplicationContainer
        """
        # Force test environment
        os.environ['ENVIRONMENT'] = 'testing'
        
        # Disable notifications for testing
        os.environ['NOTIFICATION_WHATSAPP_ENABLED'] = 'false'
        os.environ['NOTIFICATION_EMAIL_ENABLED'] = 'false'
        
        # Disable scheduling for testing
        os.environ['SCAN_SCHEDULE_ENABLED'] = 'false'
        
        # Load test settings
        from config import reload_settings
        settings = reload_settings()
        
        return ApplicationFactory.create_container(settings)


def create_app(environment: str = None) -> ApplicationContainer:
    """
    Convenience function to create application.
    
    Args:
        environment: Environment name (development, production, testing)
        
    Returns:
        Configured ApplicationContainer
    """
    if environment:
        os.environ['ENVIRONMENT'] = environment
    
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ApplicationFactory.create_production_app()
    elif env == 'testing':
        return ApplicationFactory.create_test_app()
    else:
        return ApplicationFactory.create_development_app()


if __name__ == "__main__":
    """Test the application factory."""
    import sys
    
    # Create test application
    app = create_app('testing')
    
    try:
        # Initialize application
        if not app.initialize():
            print("❌ Failed to initialize application")
            sys.exit(1)
        
        print("✅ Application initialized successfully")
        
        # Check component status
        status = app.get_component_status()
        print(f"📊 Components: {list(status['components'].keys())}")
        
        # Perform health check
        health = app.health_check()
        print(f"🏥 Health: {health['overall_status']}")
        
        # Show detailed status
        for component, component_status in health['components'].items():
            status_icon = "✅" if component_status['healthy'] else "❌"
            print(f"   {status_icon} {component}: {component_status['status']}")
        
        if health['healthy']:
            print("🎉 All systems operational!")
        else:
            print("⚠️  Some issues detected")
            if 'unhealthy_components' in health:
                print(f"   Unhealthy: {health['unhealthy_components']}")
    
    except Exception as e:
        print(f"💥 Error: {e}")
        sys.exit(1)
    
    finally:
        # Shutdown
        app.shutdown()