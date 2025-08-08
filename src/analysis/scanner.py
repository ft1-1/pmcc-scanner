"""
Main PMCC Scanner orchestrator.

Coordinates the entire PMCC scanning workflow from stock screening
to final opportunity ranking and reporting.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
from decimal import Decimal
from datetime import datetime
import json
import csv
import os
from pathlib import Path

try:
    from src.analysis.stock_screener import StockScreener, ScreeningCriteria, StockScreenResult
    from src.analysis.options_analyzer import OptionsAnalyzer, LEAPSCriteria, ShortCallCriteria, PMCCOpportunity
    from src.analysis.risk_calculator import RiskCalculator, ComprehensiveRisk
    from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
    from src.models.api_models import StockQuote, OptionContract, EnhancedStockData
    from src.api.provider_factory import SyncDataProviderFactory, FallbackStrategy
    from src.api.data_provider import ProviderType, ScreeningCriteria as ProviderScreeningCriteria
    from src.config.provider_config import ProviderConfigurationManager, DataProviderSettings
    from src.config.settings import Settings, get_settings
    # Enhanced workflow components
    from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
    from src.api.claude_client import ClaudeClient
    from src.analysis.claude_integration import ClaudeIntegrationManager
    # Legacy imports for backward compatibility
    from src.api.sync_marketdata_client import SyncMarketDataClient as MarketDataClient
    from src.api.eodhd_client import EODHDClient
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from analysis.stock_screener import StockScreener, ScreeningCriteria, StockScreenResult
    from analysis.options_analyzer import OptionsAnalyzer, LEAPSCriteria, ShortCallCriteria, PMCCOpportunity
    from analysis.risk_calculator import RiskCalculator, ComprehensiveRisk
    from models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
    from models.api_models import StockQuote, OptionContract, EnhancedStockData
    from api.provider_factory import SyncDataProviderFactory, FallbackStrategy
    from api.data_provider import ProviderType, ScreeningCriteria as ProviderScreeningCriteria
    from config.provider_config import ProviderConfigurationManager, DataProviderSettings
    from config.settings import Settings
    # Enhanced workflow components
    from api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
    from api.claude_client import ClaudeClient
    from analysis.claude_integration import ClaudeIntegrationManager
    # Legacy imports for backward compatibility
    from api.sync_marketdata_client import SyncMarketDataClient as MarketDataClient
    from api.eodhd_client import EODHDClient


logger = logging.getLogger(__name__)


@dataclass
class ScanConfiguration:
    """Configuration for PMCC scanning."""
    
    # Universe settings  
    universe: str = "SP500"  # "SP500", "NASDAQ100", "EODHD_PMCC", "DEMO", or custom list
    custom_symbols: Optional[List[str]] = None
    max_stocks_to_screen: int = 100
    
    # Data source settings
    options_source: str = "marketdata"  # "marketdata" or "eodhd"
    stock_screener_source: str = "eodhd"  # "eodhd" or "marketdata"
    use_hybrid_flow: bool = True  # EODHD stocks -> MarketData quotes -> EODHD/MarketData options
    
    # Screening criteria
    screening_criteria: Optional[ScreeningCriteria] = None
    leaps_criteria: Optional[LEAPSCriteria] = None
    short_criteria: Optional[ShortCallCriteria] = None
    
    # Risk management
    account_size: Optional[Decimal] = None
    max_risk_per_trade: Decimal = Decimal('0.02')  # 2%
    risk_free_rate: Decimal = Decimal('0.05')  # 5%
    
    # Output settings
    max_opportunities: int = 25
    min_total_score: Decimal = Decimal('60')  # Minimum score to include
    best_per_symbol_only: bool = True  # Only keep best opportunity per stock
    
    # Advanced settings
    include_dividend_analysis: bool = True
    perform_scenario_analysis: bool = True
    calculate_greeks: bool = True
    
    # AI Enhancement settings (Phase 3)
    claude_analysis_enabled: bool = True  # Auto-detects based on API key availability
    enhanced_data_collection_enabled: bool = True  # Enable enhanced EODHD data collection
    top_n_opportunities: int = 10  # Number of top opportunities to select after AI analysis
    min_claude_confidence: float = 60.0  # Minimum Claude confidence threshold
    min_combined_score: float = 70.0  # Minimum combined score threshold
    require_all_data_sources: bool = False  # Require all data sources for AI analysis


@dataclass
class ProviderUsageStats:
    """Statistics for provider usage during a scan."""
    provider_type: ProviderType
    operations_count: int = 0
    total_latency_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    credits_used: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for this provider."""
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency for this provider."""
        return self.total_latency_ms / self.operations_count if self.operations_count > 0 else 0.0


@dataclass
class ScanResults:
    """Results from a complete PMCC scan."""
    
    # Summary statistics
    scan_id: str = field(default_factory=lambda: f"scan_{int(datetime.now().timestamp())}")
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    
    # Processing statistics
    stocks_screened: int = 0
    stocks_passed_screening: int = 0
    options_analyzed: int = 0
    opportunities_found: int = 0
    
    # Results
    top_opportunities: List[PMCCCandidate] = None
    screening_results: List[StockScreenResult] = None
    
    # Complete option chain data for all analyzed stocks
    analyzed_option_chains: Dict[str, 'OptionChain'] = None  # symbol -> OptionChain
    
    # Provider usage tracking
    provider_usage: Dict[ProviderType, ProviderUsageStats] = None
    operation_routing: Dict[str, List[Tuple[str, ProviderType, bool]]] = None  # operation -> [(symbol, provider, success)]
    
    # Metadata
    configuration: Optional[ScanConfiguration] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.top_opportunities is None:
            self.top_opportunities = []
        if self.screening_results is None:
            self.screening_results = []
        if self.analyzed_option_chains is None:
            self.analyzed_option_chains = {}
        if self.provider_usage is None:
            self.provider_usage = {}
        if self.operation_routing is None:
            self.operation_routing = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def success_rate(self) -> float:
        """Calculate screening success rate."""
        if self.stocks_screened > 0:
            return self.stocks_passed_screening / self.stocks_screened
        return 0.0
    
    @property
    def opportunity_rate(self) -> float:
        """Calculate opportunity discovery rate."""
        if self.stocks_passed_screening > 0:
            return self.opportunities_found / self.stocks_passed_screening
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'scan_id': self.scan_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_seconds': self.total_duration_seconds,
            'stats': {
                'stocks_screened': self.stocks_screened,
                'stocks_passed_screening': self.stocks_passed_screening,
                'options_analyzed': self.options_analyzed,
                'opportunities_found': self.opportunities_found,
                'success_rate': self.success_rate,
                'opportunity_rate': self.opportunity_rate
            },
            'provider_usage': {
                provider.value: {
                    'operations_count': stats.operations_count,
                    'success_rate': stats.success_rate,
                    'average_latency_ms': stats.average_latency_ms,
                    'credits_used': stats.credits_used
                } for provider, stats in self.provider_usage.items()
            },
            'operation_routing': self.operation_routing,
            'top_opportunities': [opp.to_dict() for opp in self.top_opportunities],
            'analyzed_option_chains': {
                symbol: {
                    'underlying': chain.underlying,
                    'underlying_price': float(chain.underlying_price) if chain.underlying_price else None,
                    'updated': chain.updated.isoformat() if chain.updated else None,
                    'total_contracts': len(chain.contracts),
                    'calls_count': len([c for c in chain.contracts if c.side.value == 'call']),
                    'puts_count': len([c for c in chain.contracts if c.side.value == 'put']),
                    'leaps_calls_count': len([c for c in chain.contracts if c.side.value == 'call' and c.is_leaps]),
                    # Include basic stats but full chain is in PMCCCandidate
                    'expiration_dates': sorted(list(set(c.expiration.date().isoformat() for c in chain.contracts))),
                    'strike_range': {
                        'min': float(min(c.strike for c in chain.contracts if c.strike)),
                        'max': float(max(c.strike for c in chain.contracts if c.strike))
                    } if chain.contracts and any(c.strike for c in chain.contracts) else None
                } for symbol, chain in self.analyzed_option_chains.items()
            },
            'errors': self.errors,
            'warnings': self.warnings
        }


class PMCCScanner:
    """Main PMCC scanner that orchestrates the entire workflow with provider abstraction."""
    
    def __init__(self, 
                 api_client: Optional[MarketDataClient] = None,  # Legacy first param for backward compatibility
                 eodhd_client: Optional[EODHDClient] = None,
                 eodhd_config=None,
                 # New provider factory parameters
                 provider_factory: Optional[SyncDataProviderFactory] = None,
                 provider_config_manager: Optional[ProviderConfigurationManager] = None):
        """
        Initialize scanner with provider factory for automatic failover.
        
        Args:
            api_client: Legacy MarketData client (for backward compatibility)
            eodhd_client: Legacy EODHD client (for backward compatibility)
            eodhd_config: Legacy EODHD configuration (for backward compatibility)
            provider_factory: Data provider factory for automatic failover (preferred)
            provider_config_manager: Provider configuration manager (preferred)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize provider system
        if provider_factory is not None:
            self.provider_factory = provider_factory
            self.provider_config_manager = provider_config_manager or ProviderConfigurationManager()
            self.use_provider_factory = True
            self.logger.info("PMCCScanner initialized with provider factory")
        elif api_client is not None or eodhd_client is not None:
            # Legacy initialization
            self.logger.warning("Using legacy initialization. Consider updating to use provider factory.")
            self._initialize_legacy_mode(eodhd_client, api_client, eodhd_config)
            self.use_provider_factory = False
        else:
            # No parameters provided - try to create provider factory from environment
            self.logger.info("No explicit providers given, attempting to initialize provider factory from environment")
            try:
                from src.config.settings import get_settings
                settings = get_settings()
                if settings.has_valid_provider_configuration():
                    from src.config.provider_config import ProviderConfigurationManager
                    self.provider_config_manager = ProviderConfigurationManager()
                    self.provider_factory = SyncDataProviderFactory()
                    self.use_provider_factory = True
                    self.logger.info("PMCCScanner initialized with auto-detected provider factory")
                else:
                    raise ValueError("No valid provider configuration found")
            except Exception as e:
                self.logger.error(f"Failed to initialize provider factory from environment: {e}")
                raise ValueError("No providers specified and unable to auto-detect configuration. Please provide either provider_factory or legacy clients.")
        
        # Initialize components
        self.risk_calculator = RiskCalculator()
        self.options_analyzer = None
        
        # Enhanced workflow components (Phase 3)
        self.enhanced_eodhd_provider: Optional[SyncEnhancedEODHDProvider] = None
        self.claude_client: Optional[ClaudeClient] = None
        self.claude_integration_manager: Optional[ClaudeIntegrationManager] = None
        
        # Provider usage tracking
        self.current_scan_usage: Dict[ProviderType, ProviderUsageStats] = {}
        self.current_operation_routing: Dict[str, List[Tuple[str, ProviderType, bool]]] = {}
        
        if self.use_provider_factory:
            # Initialize options analyzer with default configuration
            default_config = ScanConfiguration()
            self._initialize_options_analyzer(default_config)
            self.logger.info("PMCCScanner initialized with multi-provider support and automatic failover")
        else:
            self.logger.info("PMCCScanner initialized in legacy mode")
    
    def _initialize_legacy_mode(self, eodhd_client: Optional[EODHDClient], 
                              api_client: Optional[MarketDataClient], 
                              eodhd_config):
        """Initialize scanner in legacy mode for backward compatibility."""
        self.eodhd_client = eodhd_client
        self.api_client = api_client
        self.eodhd_config = eodhd_config
        
        # For testing purposes, we can work with just the MarketData client
        # but we need to create minimal stubs for missing components
        if api_client and not eodhd_client:
            self.logger.info("Legacy mode with MarketData client only - creating minimal EODHD stub")
            # Create a minimal mock EODHD client for testing
            from unittest.mock import Mock
            self.eodhd_client = Mock()
            self.eodhd_client.config = Mock()
            self.eodhd_client.config.api_key = "test_key"
            self.eodhd_client.api_token = "test_token"
            self.eodhd_client.base_url = "https://test.api.com"
            self.eodhd_client.timeout = Mock()
            self.eodhd_client.timeout.total = 30
            self.eodhd_client.max_retries = 3
            self.eodhd_client.retry_backoff = 1.0
            
        elif eodhd_client and not api_client:
            self.logger.info("Legacy mode with EODHD client only")
            
        elif not eodhd_client and not api_client:
            raise ValueError("At least one client (EODHD or MarketData) is required in legacy mode")
        
        # Initialize stock screener with available clients
        self.stock_screener = StockScreener(api_client, eodhd_client)
        self.sync_eodhd_client = None
    
    def _initialize_options_analyzer(self, config: ScanConfiguration):
        """
        Initialize options analyzer based on configuration and provider setup.
        
        Args:
            config: Scan configuration specifying options source
        """
        if self.use_provider_factory:
            # Use provider factory to get best provider for options
            # Respect the configuration for preferred options provider
            preferred_options_provider = getattr(config, 'options_source', None)
            if preferred_options_provider == 'eodhd':
                preferred_provider = ProviderType.EODHD
            elif preferred_options_provider == 'marketdata':
                preferred_provider = ProviderType.MARKETDATA
            else:
                # Use the global configuration from provider factory
                preferred_provider = None
            
            options_provider = self.provider_factory.get_provider(
                "get_options_chain",
                preferred_provider=preferred_provider
            )
            
            self.logger.info(f"Requested options provider: {preferred_provider}, Got: {options_provider.provider_type if options_provider else None}")
            
            if options_provider:
                self.options_analyzer = OptionsAnalyzer(
                    data_provider=options_provider,
                    config=getattr(self, 'eodhd_config', {})  # Pass legacy config if available
                )
                self.logger.info(f"Options analyzer initialized with provider: {options_provider.provider_type}")
            else:
                raise ValueError("No provider available for options analysis")
        else:
            # Legacy initialization
            options_source = config.options_source.lower()
            
            if options_source == "eodhd":
                if not self.eodhd_client:
                    raise ValueError("EODHD client required when options_source='eodhd'")
                
                # Create sync wrapper if not already created
                if not self.sync_eodhd_client:
                    # Check if this is a mock client (for testing)
                    from unittest.mock import Mock
                    if isinstance(self.eodhd_client, Mock):
                        # For testing - use a minimal mock sync client
                        self.sync_eodhd_client = Mock()
                    else:
                        # Real client - create sync wrapper
                        from src.api.sync_eodhd_client import SyncEODHDClient
                        self.sync_eodhd_client = SyncEODHDClient(
                            api_token=self.eodhd_client.api_token,
                            base_url=self.eodhd_client.base_url,
                            timeout=self.eodhd_client.timeout.total,
                            max_retries=self.eodhd_client.max_retries,
                            retry_backoff=self.eodhd_client.retry_backoff
                        )
                
                self.options_analyzer = OptionsAnalyzer(
                    data_provider=None,  # Use legacy mode
                    eodhd_client=self.sync_eodhd_client,
                    api_client=self.api_client,  # Pass both clients for better compatibility
                    options_source="eodhd",
                    eodhd_config=self.eodhd_config
                )
            else:
                # Force EODHD in legacy mode
                if not self.sync_eodhd_client:
                    # Check if this is a mock client (for testing)
                    from unittest.mock import Mock
                    if isinstance(self.eodhd_client, Mock):
                        # For testing - use a minimal mock sync client
                        self.sync_eodhd_client = Mock()
                    else:
                        # Real client - create sync wrapper
                        from src.api.sync_eodhd_client import SyncEODHDClient
                        self.sync_eodhd_client = SyncEODHDClient(
                            api_token=self.eodhd_client.api_token,
                            base_url=self.eodhd_client.base_url,
                            timeout=self.eodhd_client.timeout.total,
                            max_retries=self.eodhd_client.max_retries,
                            retry_backoff=self.eodhd_client.retry_backoff
                        )
                
                self.options_analyzer = OptionsAnalyzer(
                    data_provider=None,  # Use legacy mode
                    eodhd_client=self.sync_eodhd_client,
                    api_client=self.api_client,  # Pass both clients for better compatibility
                    options_source="eodhd",
                    eodhd_config=self.eodhd_config
                )
            
            self.logger.info(f"Options analyzer initialized with legacy source='{options_source}'")
    
    def _initialize_enhanced_workflow(self, config: ScanConfiguration) -> bool:
        """
        Initialize enhanced workflow components for AI analysis.
        
        Args:
            config: Scan configuration
            
        Returns:
            True if enhanced workflow is available and initialized
        """
        if not config.claude_analysis_enabled and not config.enhanced_data_collection_enabled:
            self.logger.info("Enhanced workflow disabled by configuration")
            return False
        
        # Initialize enhanced EODHD provider if data collection is enabled
        if config.enhanced_data_collection_enabled and self.use_provider_factory:
            try:
                # Check if EODHD provider is available
                eodhd_provider = self.provider_factory.get_provider("get_fundamental_data", preferred_provider=ProviderType.EODHD)
                if eodhd_provider and hasattr(eodhd_provider, 'config'):
                    self.enhanced_eodhd_provider = SyncEnhancedEODHDProvider(
                        provider_type=ProviderType.EODHD,
                        config=eodhd_provider.config
                    )
                    self.logger.info("Enhanced EODHD provider initialized successfully")
                else:
                    self.logger.warning("Enhanced EODHD provider not available - EODHD API key may be missing")
                    config.enhanced_data_collection_enabled = False
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize enhanced EODHD provider: {e}")
                config.enhanced_data_collection_enabled = False
        
        # Initialize Claude AI client if analysis is enabled
        if config.claude_analysis_enabled:
            try:
                import os
                claude_api_key = os.getenv('CLAUDE_API_KEY')
                if claude_api_key and claude_api_key.strip() and claude_api_key != "your_claude_api_key_here":
                    self.claude_client = ClaudeClient(api_key=claude_api_key)
                    self.claude_integration_manager = ClaudeIntegrationManager(settings=config)
                    self.logger.info("Claude AI client initialized successfully")
                else:
                    self.logger.warning("Claude AI analysis disabled - CLAUDE_API_KEY not configured")
                    config.claude_analysis_enabled = False
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize Claude AI client: {e}")
                config.claude_analysis_enabled = False
        
        # Return True if at least one enhanced component is available
        enhanced_available = (
            (config.enhanced_data_collection_enabled and self.enhanced_eodhd_provider is not None) or
            (config.claude_analysis_enabled and self.claude_client is not None)
        )
        
        if enhanced_available:
            self.logger.info("Enhanced workflow initialized and ready")
        else:
            self.logger.info("Enhanced workflow not available - continuing with standard workflow")
        
        return enhanced_available
    
    def _perform_enhanced_analysis(
        self,
        pmcc_opportunities: List[PMCCCandidate], 
        config: ScanConfiguration, 
        results: ScanResults
    ) -> List[PMCCCandidate]:
        """
        Perform enhanced analysis using AI and comprehensive data collection.
        
        Args:
            pmcc_opportunities: List of PMCC opportunities from traditional analysis
            config: Scan configuration
            results: Scan results for tracking
            
        Returns:
            Enhanced and filtered list of top opportunities
        """
        import asyncio
        from datetime import date
        
        self.logger.info(f"Starting enhanced analysis for {len(pmcc_opportunities)} opportunities")
        
        # Step 5a: Enhanced Data Collection
        enhanced_stock_data = []
        if config.enhanced_data_collection_enabled and self.enhanced_eodhd_provider:
            print(f"📊 Collecting enhanced data for {len(pmcc_opportunities)} stocks...")
            self.logger.info(f"Starting enhanced data collection for {len(pmcc_opportunities)} opportunities")
            
            collection_start_time = datetime.now()
            successful_collections = 0
            failed_collections = 0
            
            for opportunity in pmcc_opportunities:
                try:
                    # Use synchronous comprehensive enhanced data collection method
                    enhanced_data_response = self.enhanced_eodhd_provider.get_comprehensive_enhanced_data(opportunity.symbol)
                    
                    if enhanced_data_response.is_success and enhanced_data_response.data:
                        # Update the stock price with the current price from PMCC scan
                        enhanced_data = enhanced_data_response.data
                        if enhanced_data.get('live_price') and hasattr(opportunity, 'underlying_price') and opportunity.underlying_price:
                            # Update the live price with the current price from PMCC scan
                            if isinstance(enhanced_data['live_price'], list) and enhanced_data['live_price']:
                                enhanced_data['live_price'][0]['close'] = opportunity.underlying_price
                                enhanced_data['live_price'][0]['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            self.logger.debug(f"Updated {opportunity.symbol} price to current scan price: ${opportunity.underlying_price}")
                        
                        # Add the options chain data from the PMCC analysis if available
                        if hasattr(opportunity, 'analysis') and opportunity.analysis:
                            # Create an OptionChain from the PMCC analysis
                            from src.models.api_models import OptionChain
                            
                            contracts = []
                            if opportunity.analysis.long_call:
                                contracts.append(opportunity.analysis.long_call)
                            if opportunity.analysis.short_call:
                                contracts.append(opportunity.analysis.short_call)
                            
                            if contracts:
                                options_chain = OptionChain(
                                    underlying=opportunity.symbol,
                                    underlying_price=opportunity.underlying_price,
                                    contracts=contracts,
                                    updated=datetime.now()
                                )
                                enhanced_data['options_chain'] = options_chain
                                self.logger.debug(f"Added options chain data for {opportunity.symbol} with {len(contracts)} contracts")
                        
                        enhanced_stock_data.append(enhanced_data)
                        successful_collections += 1
                        # Calculate completeness score from dictionary data
                        completeness_keys = ['live_price', 'fundamentals', 'earnings', 'news', 'technical_indicators', 'sentiment', 'historical_prices', 'economic_events']
                        available_keys = sum(1 for key in completeness_keys if enhanced_data.get(key))
                        completeness_score = (available_keys / len(completeness_keys)) * 100
                        self.logger.debug(f"Enhanced data collected for {opportunity.symbol} "
                                        f"(completeness: {completeness_score:.1f}%)")
                    else:
                        failed_collections += 1
                        self.logger.warning(f"No enhanced data available for {opportunity.symbol}")
                        # Create minimal enhanced data from existing PMCC data for fallback
                        if hasattr(opportunity, 'analysis') and opportunity.analysis.underlying:
                            # Create comprehensive enhanced data from PMCC analysis
                            from src.models.api_models import OptionChain
                            
                            # Use the current stock price from PMCC scan
                            current_quote = opportunity.analysis.underlying
                            current_quote.last = opportunity.underlying_price
                            current_quote.updated = datetime.now()
                            
                        else:
                            # Complete fallback - just track the failure
                            pass
                        
                except Exception as e:
                    failed_collections += 1
                    self.logger.warning(f"Error collecting enhanced data for {opportunity.symbol}: {e}")
                    continue
            
            collection_duration = (datetime.now() - collection_start_time).total_seconds()
            success_rate = (successful_collections / len(pmcc_opportunities)) * 100 if pmcc_opportunities else 0
            
            self.logger.info(f"Enhanced data collection completed in {collection_duration:.2f} seconds. "
                           f"Success: {successful_collections}, Failed: {failed_collections} "
                           f"(Success rate: {success_rate:.1f}%)")
            
            print(f"✅ Enhanced data collected for {len(enhanced_stock_data)} stocks "
                  f"({success_rate:.1f}% success rate)")
        
        # Step 5b: Individual Claude AI Analysis
        enhanced_opportunities = []
        if config.claude_analysis_enabled and self.claude_client and enhanced_stock_data:
            print(f"🧠 Analyzing {len(enhanced_stock_data)} opportunities individually with Claude AI...")
            self.logger.info(f"Starting individual Claude AI analysis for {len(enhanced_stock_data)} opportunities")
            
            try:
                claude_start_time = datetime.now()
                
                # Create market context
                market_context = {
                    'analysis_date': date.today().isoformat(),
                    'total_opportunities': len(enhanced_stock_data),
                    'market_sentiment': 'neutral',  # Could be enhanced with market data
                    'volatility_regime': 'normal'   # Could be enhanced with VIX data
                }
                
                successful_analyses = 0
                failed_analyses = 0
                
                # Analyze each opportunity individually with complete data package
                for i, enhanced_data in enumerate(enhanced_stock_data, 1):
                    # Extract symbol from comprehensive data structure
                    symbol = 'Unknown'
                    if isinstance(enhanced_data, dict):
                        # Try to get symbol from live_price data
                        if enhanced_data.get('live_price'):
                            live_price = enhanced_data['live_price']
                            if isinstance(live_price, dict):
                                # Find first symbol key (format: SYMBOL.US)
                                for key in live_price.keys():
                                    if '.US' in key:
                                        symbol = key.replace('.US', '')
                                        break
                            elif isinstance(live_price, list) and len(live_price) > 0:
                                code = live_price[0].get('code', '')
                                symbol = code.replace('.US', '') if code else 'Unknown'
                        # Fallback: try to infer from PMCC opportunities by index
                        if symbol == 'Unknown' and i <= len(pmcc_opportunities):
                            symbol = pmcc_opportunities[i-1].symbol
                    else:
                        # Legacy format - try to get symbol from live_price data
                        if enhanced_data.get('live_price') and isinstance(enhanced_data['live_price'], list) and enhanced_data['live_price']:
                            live_price = enhanced_data['live_price'][0]
                            code = live_price.get('code', '')
                            symbol = code.replace('.US', '') if code else 'Unknown'
                        else:
                            symbol = 'Unknown'
                    
                    try:
                        self.logger.info(f"Analyzing opportunity {i}/{len(enhanced_stock_data)}: {symbol}")
                        print(f"  Analyzing {symbol} ({i}/{len(enhanced_stock_data)})...")
                        
                        # Find the corresponding PMCC opportunity
                        corresponding_opportunity = None
                        for opp in pmcc_opportunities:
                            if opp.symbol == symbol:
                                corresponding_opportunity = opp
                                break
                        
                        if not corresponding_opportunity:
                            self.logger.warning(f"No PMCC opportunity found for {symbol}")
                            failed_analyses += 1
                            continue
                        
                        # Prepare opportunity data for Claude with complete PMCC details
                        opportunity_data = {
                            'symbol': symbol,
                            'underlying_price': float(corresponding_opportunity.underlying_price),
                            'strategy_details': {
                                'net_debit': float(getattr(corresponding_opportunity.analysis, 'net_debit', 0)),
                                'credit_received': 0,  # PMCC is a net debit strategy
                                'max_profit': float(getattr(corresponding_opportunity.analysis, 'max_profit', 0)),
                                'max_loss': float(getattr(corresponding_opportunity.analysis, 'max_loss', 0)),
                                'breakeven_price': float(getattr(corresponding_opportunity.analysis, 'breakeven', 0)),
                                'risk_reward_ratio': float(getattr(corresponding_opportunity.analysis, 'risk_reward_ratio', 0))
                            },
                            'leaps_option': self._extract_option_data(corresponding_opportunity.analysis.long_call) if corresponding_opportunity.analysis.long_call else {},
                            'short_option': self._extract_option_data(corresponding_opportunity.analysis.short_call) if corresponding_opportunity.analysis.short_call else {},
                            'pmcc_score': float(corresponding_opportunity.total_score),
                            'liquidity_score': float(corresponding_opportunity.liquidity_score)
                        }
                        
                        # Prepare enhanced stock data for Claude
                        # DEBUG: Check what enhanced_data is
                        self.logger.debug(f"Enhanced data type for {symbol}: {type(enhanced_data)}")
                        if isinstance(enhanced_data, dict):
                            self.logger.debug(f"  Enhanced data keys: {list(enhanced_data.keys())}")
                        elif isinstance(enhanced_data, str):
                            self.logger.debug(f"  Enhanced data string: {enhanced_data[:100]}...")
                        
                        try:
                            enhanced_stock_dict = self._enhanced_stock_data_to_dict(enhanced_data)
                        except Exception as conv_e:
                            self.logger.error(f"Error converting enhanced data for {symbol}: {conv_e}")
                            self.logger.error(f"Enhanced data type was: {type(enhanced_data)}")
                            print(f"Error converting enhanced data for {symbol}: {conv_e}")
                            print(f"Enhanced data type was: {type(enhanced_data)}")
                            # Add traceback for debugging
                            import traceback
                            traceback.print_exc()
                            continue
                        
                        # DEBUG LOGGING: Log data sent to Claude
                        self.logger.debug(f"Claude request data for {symbol}:")
                        self.logger.debug(f"  Opportunity data keys: {list(opportunity_data.keys())}")
                        self.logger.debug(f"  Enhanced stock data type: {type(enhanced_stock_dict)}")
                        if isinstance(enhanced_stock_dict, dict):
                            self.logger.debug(f"  Enhanced stock data keys: {list(enhanced_stock_dict.keys())}")
                        elif isinstance(enhanced_stock_dict, str):
                            self.logger.debug(f"  Enhanced stock data string: {enhanced_stock_dict[:100]}...")
                        self.logger.debug(f"  Market context: {market_context}")
                        
                        # Run individual Claude analysis
                        claude_response = asyncio.run(
                            self.claude_client.analyze_single_opportunity(
                                opportunity_data,
                                enhanced_stock_dict,
                                market_context
                            )
                        )
                        
                        if claude_response.is_success and claude_response.data:
                            claude_result = claude_response.data
                            
                            # DEBUG LOGGING: Log Claude response
                            self.logger.debug(f"Claude response for {symbol}:")
                            self.logger.debug(f"  Response data: {claude_result}")
                            
                            # PERSISTENCE: Save Claude request/response for debugging
                            try:
                                import os
                                import json
                                debug_dir = os.path.join("data", "claude_submissions")
                                os.makedirs(debug_dir, exist_ok=True)
                                
                                # Extract the debug prompt if available
                                full_prompt = claude_result.pop('_debug_prompt', None)
                                
                                debug_data = {
                                    'timestamp': datetime.now().isoformat(),
                                    'symbol': symbol,
                                    'full_claude_prompt': full_prompt,  # The complete prompt sent to Claude
                                    'request_data': {
                                        'opportunity_data': opportunity_data,
                                        'enhanced_stock_dict': enhanced_stock_dict,
                                        'market_context': market_context
                                    },
                                    'response_data': claude_result
                                }
                                
                                debug_file = os.path.join(debug_dir, f"claude_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                                with open(debug_file, 'w') as f:
                                    json.dump(debug_data, f, indent=2, default=str)
                                
                                self.logger.debug(f"Saved Claude debug data to {debug_file}")
                            except Exception as debug_e:
                                self.logger.warning(f"Failed to save Claude debug data for {symbol}: {debug_e}")
                            
                            # Add Claude insights to the original opportunity with timestamp
                            corresponding_opportunity.ai_insights = claude_result
                            corresponding_opportunity.claude_score = claude_result.get('pmcc_score', 0)
                            
                            # Calculate combined score using configurable weights from settings
                            settings = get_settings()
                            traditional_weight = settings.scan.traditional_pmcc_weight
                            ai_weight = settings.scan.ai_analysis_weight
                            
                            corresponding_opportunity.combined_score = (
                                float(corresponding_opportunity.total_score) * traditional_weight + 
                                claude_result.get('pmcc_score', 0) * ai_weight
                            )
                            corresponding_opportunity.ai_analysis_timestamp = datetime.now()
                            corresponding_opportunity.claude_reasoning = claude_result.get('analysis_summary', '')
                            corresponding_opportunity.ai_recommendation = claude_result.get('recommendation', 'neutral')
                            corresponding_opportunity.claude_confidence = claude_result.get('confidence_level', claude_result.get('confidence_score', 0))
                            
                            # Enhanced debug logging for scoring calculation
                            self.logger.info(f"{symbol} scoring details: "
                                           f"Traditional={corresponding_opportunity.total_score:.1f} (weight={traditional_weight}), "
                                           f"Claude={claude_result.get('pmcc_score', 0)} (weight={ai_weight}), "
                                           f"Combined={corresponding_opportunity.combined_score:.1f}, "
                                           f"Confidence={corresponding_opportunity.claude_confidence}")
                            
                            enhanced_opportunities.append(corresponding_opportunity)
                            successful_analyses += 1
                            
                            self.logger.debug(f"{symbol}: PMCC={corresponding_opportunity.total_score:.1f}, "
                                           f"Claude={claude_result.get('pmcc_score', 0):.1f}, "
                                           f"Combined={corresponding_opportunity.combined_score:.1f}")
                            
                            # Add 60-second delay to respect Claude API rate limits
                            # (40K input tokens/min, 8K output tokens/min)
                            if i < len(enhanced_stock_data):  # Don't delay after the last analysis
                                self.logger.info("Waiting 60 seconds before next Claude API call to respect rate limits...")
                                import time
                                time.sleep(60)
                        else:
                            self.logger.warning(f"Claude analysis failed for {symbol}")
                            failed_analyses += 1
                            # Still add the opportunity without Claude insights
                            enhanced_opportunities.append(corresponding_opportunity)
                        
                    except Exception as e:
                        self.logger.error(f"Error analyzing {symbol} with Claude: {e}")
                        failed_analyses += 1
                        # Add the opportunity without Claude insights on error
                        if corresponding_opportunity:
                            enhanced_opportunities.append(corresponding_opportunity)
                        continue
                
                claude_duration = (datetime.now() - claude_start_time).total_seconds()
                success_rate = (successful_analyses / len(enhanced_stock_data)) * 100 if enhanced_stock_data else 0
                
                self.logger.info(f"Individual Claude AI analysis completed in {claude_duration:.2f} seconds. "
                               f"Success: {successful_analyses}, Failed: {failed_analyses} "
                               f"(Success rate: {success_rate:.1f}%)")
                
                print(f"✅ Individual Claude AI analysis completed: {successful_analyses} successful, "
                      f"{failed_analyses} failed ({success_rate:.1f}% success rate)")
                    
            except Exception as e:
                self.logger.error(f"Claude AI analysis error: {e}", exc_info=True)
                results.errors.append(f"Claude AI analysis error: {str(e)}")
                # Fallback to original opportunities
                enhanced_opportunities = pmcc_opportunities
        else:
            if not config.claude_analysis_enabled:
                self.logger.info("Claude AI analysis disabled by configuration")
            elif not self.claude_client:
                self.logger.warning("Claude AI client not initialized")
            elif not enhanced_stock_data:
                self.logger.warning("No enhanced stock data available for Claude analysis")
        
        # Step 5c: Integration and Top N Selection
        filtered_opportunities = []  # Initialize here for proper scope
        
        if enhanced_opportunities:
            print(f"🔄 Selecting top opportunities from AI-enhanced analysis...")
            self.logger.info(f"Selecting top opportunities from {len(enhanced_opportunities)} AI-enhanced opportunities")
            
            integration_start_time = datetime.now()
            
            try:
                # First, filter to ONLY include successfully AI-analyzed opportunities
                # Debug: Log what we're checking
                for opp in enhanced_opportunities:
                    self.logger.debug(f"Checking {opp.symbol}: has claude_score={hasattr(opp, 'claude_score')}, "
                                     f"claude_score value={getattr(opp, 'claude_score', 'N/A')}, "
                                     f"is not None={getattr(opp, 'claude_score', None) is not None}")
                
                ai_analyzed_opportunities = [
                    opp for opp in enhanced_opportunities 
                    if hasattr(opp, 'claude_score') and opp.claude_score is not None and opp.claude_score > 0
                ]
                
                self.logger.info(f"Found {len(ai_analyzed_opportunities)} successfully AI-analyzed opportunities out of {len(enhanced_opportunities)} total")
                
                if not ai_analyzed_opportunities:
                    self.logger.warning("No opportunities were successfully analyzed by Claude AI")
                    return []  # Return empty list if no AI analysis succeeded
                
                # Sort by combined score
                def get_sort_key(opp):
                    if hasattr(opp, 'combined_score') and opp.combined_score is not None:
                        return float(opp.combined_score)
                    return float(opp.total_score)
                
                sorted_opportunities = sorted(ai_analyzed_opportunities, key=get_sort_key, reverse=True)
                
                # Take top N opportunities
                top_opportunities = sorted_opportunities[:config.top_n_opportunities]
                
                # Filter by AI criteria (confidence and score thresholds)
                for opp in top_opportunities:
                    # We already know these have claude_score, so just check thresholds
                    score = getattr(opp, 'combined_score', None) or float(opp.total_score)
                    confidence = getattr(opp, 'claude_confidence', 0)
                    
                    if score >= config.min_combined_score and confidence >= config.min_claude_confidence:
                        filtered_opportunities.append(opp)
                        self.logger.info(f"✅ Selected {opp.symbol}: score={score:.1f}, confidence={confidence:.1f}")
                    else:
                        self.logger.info(f"❌ Rejected {opp.symbol}: score={score:.1f} (min: {config.min_combined_score}), "
                                        f"confidence={confidence:.1f} (min: {config.min_claude_confidence})")
                
                integration_duration = (datetime.now() - integration_start_time).total_seconds()
                
                # Calculate statistics
                def get_display_score(opp):
                    return getattr(opp, 'combined_score', None) or float(opp.total_score)
                
                avg_score = sum(get_display_score(opp) for opp in filtered_opportunities) / len(filtered_opportunities) if filtered_opportunities else 0
                ai_analyzed_count = len(filtered_opportunities)  # All are AI analyzed by definition now
                high_confidence_count = sum(1 for opp in filtered_opportunities if hasattr(opp, 'claude_confidence') and opp.claude_confidence and opp.claude_confidence >= 75)
                
                self.logger.info(f"Top N selection completed in {integration_duration:.2f} seconds. "
                               f"Selected {len(filtered_opportunities)} opportunities "
                               f"(Avg score: {avg_score:.1f}, "
                               f"AI analyzed: {ai_analyzed_count}, "
                               f"High confidence: {high_confidence_count})")
                
                print(f"✅ Top N selection complete: Selected {len(filtered_opportunities)} opportunities "
                      f"(Avg score: {avg_score:.1f}, AI analyzed: {ai_analyzed_count})")
                
                self.logger.info(f"Enhanced analysis completed: {len(filtered_opportunities)} top opportunities selected")
                return filtered_opportunities
                
            except Exception as e:
                self.logger.error(f"Selection error: {e}", exc_info=True)
                results.errors.append(f"Selection error: {str(e)}")
                return []  # Return empty list on error
        else:
            self.logger.info("No enhanced opportunities available")
            return []  # Return empty list if no enhanced opportunities
        
        # This line should never be reached, but just in case
        return filtered_opportunities
    
    def _extract_option_data(self, option_contract) -> Dict[str, Any]:
        """Extract option data from option contract for Claude analysis."""
        if not option_contract:
            return {}
        
        return {
            'option_symbol': getattr(option_contract, 'option_symbol', ''),
            'strike': float(getattr(option_contract, 'strike', 0)),
            'expiration': getattr(option_contract, 'expiration', '').isoformat() if hasattr(getattr(option_contract, 'expiration', ''), 'isoformat') else str(getattr(option_contract, 'expiration', '')),
            'dte': getattr(option_contract, 'dte', 0),
            'bid': float(getattr(option_contract, 'bid', 0)) if getattr(option_contract, 'bid', None) is not None else 0,
            'ask': float(getattr(option_contract, 'ask', 0)) if getattr(option_contract, 'ask', None) is not None else 0,
            'mid': float(getattr(option_contract, 'mid', 0)) if getattr(option_contract, 'mid', None) is not None else 0,
            'last': float(getattr(option_contract, 'last', 0)) if getattr(option_contract, 'last', None) is not None else 0,
            'volume': getattr(option_contract, 'volume', 0),
            'open_interest': getattr(option_contract, 'open_interest', 0),
            'delta': float(getattr(option_contract, 'delta', 0)) if getattr(option_contract, 'delta', None) is not None else 0,
            'gamma': float(getattr(option_contract, 'gamma', 0)) if getattr(option_contract, 'gamma', None) is not None else 0,
            'theta': float(getattr(option_contract, 'theta', 0)) if getattr(option_contract, 'theta', None) is not None else 0,
            'vega': float(getattr(option_contract, 'vega', 0)) if getattr(option_contract, 'vega', None) is not None else 0,
            'iv': float(getattr(option_contract, 'iv', 0)) if getattr(option_contract, 'iv', None) is not None else 0
        }
    
    def _enhanced_stock_data_to_dict(self, comprehensive_data) -> Dict[str, Any]:
        """Convert comprehensive enhanced data to dictionary for Claude analysis."""
        result = {}
        
        # Handle case where data is the comprehensive dictionary format (from get_comprehensive_enhanced_data)
        if isinstance(comprehensive_data, dict):
            enhanced_data = comprehensive_data
        else:
            # Handle legacy EnhancedStockData object format or other object types
            # If it's an object with a model_dump method (Pydantic), convert it
            if hasattr(comprehensive_data, 'model_dump'):
                enhanced_data = comprehensive_data.model_dump()
                comprehensive_data = enhanced_data
            elif hasattr(comprehensive_data, '__dict__'):
                # Convert object to dict
                enhanced_data = vars(comprehensive_data)
                comprehensive_data = enhanced_data
            else:
                # Unable to convert
                self.logger.error(f"Unable to convert enhanced data of type: {type(comprehensive_data)}")
                enhanced_data = {}
                comprehensive_data = {}
        
        # Debug: Check what we actually have
        self.logger.debug(f"enhanced_data type: {type(enhanced_data)}, keys: {list(enhanced_data.keys()) if isinstance(enhanced_data, dict) else 'N/A'}")
        
        # Extract quote data - check multiple potential sources
        if comprehensive_data and 'live_price' in comprehensive_data and comprehensive_data['live_price']:
            # Use live price data if available
            live_price = comprehensive_data['live_price']
            if isinstance(live_price, list) and len(live_price) > 0:
                price_data = live_price[0]
                result['quote'] = {
                    'symbol': price_data.get('code', '').replace('.US', ''),
                    'last': float(price_data.get('close', price_data.get('price', 0))),
                    'change': float(price_data.get('change', 0)),
                    'change_percent': float(price_data.get('change_percent', price_data.get('change_p', 0))),
                    'volume': int(price_data.get('volume', 0)),
                    'market_cap': 0,  # Will be filled from fundamentals
                    'high': float(price_data.get('high', 0)),
                    'low': float(price_data.get('low', 0)),
                    'open': float(price_data.get('open', 0)),
                    'previous_close': float(price_data.get('previous_close', 0))
                }
            elif isinstance(live_price, dict):
                # Handle single dict response (EODHD format)
                if 'code' in live_price:
                    # Direct EODHD live price format
                    result['quote'] = {
                        'symbol': live_price.get('code', '').replace('.US', ''),
                        'last': float(live_price.get('close', 0)),
                        'change': float(live_price.get('change', 0)),
                        'change_percent': float(live_price.get('change_p', 0)),
                        'volume': int(live_price.get('volume', 0)),
                        'market_cap': 0,  # Will be filled from fundamentals
                        'high': float(live_price.get('high', 0)),
                        'low': float(live_price.get('low', 0)),
                        'open': float(live_price.get('open', 0)),
                        'previous_close': float(live_price.get('previousClose', 0))
                    }
                else:
                    # Handle nested dict format
                    first_symbol = list(live_price.keys())[0] if live_price else None
                    if first_symbol:
                        price_data = live_price[first_symbol]
                        result['quote'] = {
                            'symbol': first_symbol.replace('.US', ''),
                            'last': float(price_data.get('close', price_data.get('price', 0))),
                            'change': float(price_data.get('change', 0)),
                            'change_percent': float(price_data.get('change_percent', price_data.get('change_p', 0))),
                            'volume': int(price_data.get('volume', 0)),
                            'market_cap': 0,  # Will be filled from fundamentals
                            'high': float(price_data.get('high', 0)),
                            'low': float(price_data.get('low', 0)),
                            'open': float(price_data.get('open', 0)),
                            'previous_close': float(price_data.get('previous_close', 0))
                        }
        elif comprehensive_data and 'historical_prices' in comprehensive_data and comprehensive_data['historical_prices'] is not None:
            # Fallback to historical prices for current data
            hist_prices = comprehensive_data['historical_prices']
            if hasattr(hist_prices, 'iloc') and not hist_prices.empty:
                # DataFrame format
                latest = hist_prices.iloc[-1]
                result['quote'] = {
                    'symbol': str(latest.get('symbol', '')).replace('.US', '') if 'symbol' in latest else '',
                    'last': float(latest.get('adjusted_close', latest.get('close', 0))),
                    'change': 0,  # Calculate if previous data available
                    'change_percent': 0,
                    'volume': int(latest.get('volume', 0)),
                    'market_cap': 0,  # Will be filled from fundamentals
                    'high': float(latest.get('high', 0)),
                    'low': float(latest.get('low', 0)),
                    'open': float(latest.get('open', 0)),
                    'previous_close': 0
                }
                # Calculate change if we have multiple days
                if len(hist_prices) > 1:
                    prev = hist_prices.iloc[-2]
                    prev_close = float(prev.get('adjusted_close', prev.get('close', 0)))
                    current_price = result['quote']['last']
                    if prev_close > 0:
                        result['quote']['change'] = current_price - prev_close
                        result['quote']['change_percent'] = ((current_price - prev_close) / prev_close) * 100
                        result['quote']['previous_close'] = prev_close
        elif enhanced_data and enhanced_data.get('live_price'):
            # Dictionary format fallback - use live_price data
            live_price_data = enhanced_data['live_price']
            if isinstance(live_price_data, list) and live_price_data:
                price_info = live_price_data[0]
                result['quote'] = {
                    'symbol': price_info.get('code', '').replace('.US', ''),
                    'last': float(price_info.get('close', 0)),
                    'change': float(price_info.get('change', 0)),
                    'change_percent': float(price_info.get('change_p', 0)),
                    'volume': price_info.get('volume', 0),
                    'market_cap': 0  # Not available in live price data
                }
        
        # Comprehensive fundamental data from filtered EODHD response
        if comprehensive_data and 'fundamentals' in comprehensive_data and comprehensive_data['fundamentals']:
            fund = comprehensive_data['fundamentals']
            
            # DEBUG: Check fundamental data type and structure
            self.logger.debug(f"Fundamentals data type: {type(fund)}")
            
            # Handle case where fundamentals is a FundamentalMetrics object
            from src.models.api_models import FundamentalMetrics
            if isinstance(fund, FundamentalMetrics):
                # Convert FundamentalMetrics object to dict format expected by example
                fund_dict = {
                    'company_info': {
                        'name': '',  # Not available in FundamentalMetrics
                        'sector': '',  # Not available in FundamentalMetrics
                        'industry': '',  # Not available in FundamentalMetrics
                        'market_cap_mln': float(fund.market_capitalization) / 1000000 if fund.market_capitalization else None,
                        'employees': None,  # Not available in FundamentalMetrics
                        'description': ''  # Not available in FundamentalMetrics
                    },
                    'financial_health': {
                        'eps_ttm': float(fund.earnings_per_share) if fund.earnings_per_share else None,
                        'profit_margin': float(fund.profit_margin) if fund.profit_margin else None,
                        'operating_margin': float(fund.operating_margin) if fund.operating_margin else None,
                        'roe': float(fund.roe) if fund.roe else None,
                        'roa': float(fund.roa) if fund.roa else None,
                        'revenue_growth_yoy': float(fund.revenue_growth_rate) if fund.revenue_growth_rate else None,
                        'earnings_growth_yoy': float(fund.earnings_growth_rate) if fund.earnings_growth_rate else None,
                        'eps_estimate_current_year': None,  # Not in FundamentalMetrics
                        'eps_estimate_next_year': None,  # Not in FundamentalMetrics
                        'dividend_yield': None,  # Not in FundamentalMetrics
                        'dividend_per_share': None,  # Not in FundamentalMetrics
                        'revenue_ttm': None,  # Not in FundamentalMetrics
                        'revenue_per_share': float(fund.revenue_per_share) if fund.revenue_per_share else None,
                        'most_recent_quarter': None  # Not in FundamentalMetrics
                    },
                    'valuation_metrics': {
                        'pe_ratio': float(fund.pe_ratio) if fund.pe_ratio else None,
                        'forward_pe': None,  # Not in FundamentalMetrics
                        'price_to_sales': float(fund.ps_ratio) if fund.ps_ratio else None,
                        'price_to_book': float(fund.pb_ratio) if fund.pb_ratio else None,
                        'enterprise_value': float(fund.enterprise_value) if fund.enterprise_value else None,
                        'ev_to_revenue': float(fund.ev_to_revenue) if fund.ev_to_revenue else None,
                        'ev_to_ebitda': float(fund.ev_to_ebitda) if fund.ev_to_ebitda else None
                    },
                    'stock_technicals': {
                        'beta': None,  # Not in FundamentalMetrics
                        '52_week_high': None,  # Not in FundamentalMetrics
                        '52_week_low': None,  # Not in FundamentalMetrics
                        '50_day_ma': None,  # Not in FundamentalMetrics
                        '200_day_ma': None,  # Not in FundamentalMetrics
                        'short_interest': None,  # Not in FundamentalMetrics
                        'short_ratio': None  # Not in FundamentalMetrics
                    },
                    'dividend_info': {},  # Not in FundamentalMetrics
                    'analyst_sentiment': {},  # Not in FundamentalMetrics
                    'ownership_structure': {
                        'shares_outstanding': fund.shares_outstanding,
                        'percent_institutions': float(fund.institutional_ownership) if fund.institutional_ownership else None,
                        'percent_insiders': float(fund.insider_ownership) if fund.insider_ownership else None,
                        'shares_float': fund.float_shares
                    },
                    'balance_sheet': {},  # Not in FundamentalMetrics
                    'income_statement': {},  # Not in FundamentalMetrics
                    'cash_flow': {}  # Not in FundamentalMetrics
                }
                fund = fund_dict
            elif isinstance(fund, str) or not isinstance(fund, dict):
                # Skip fundamentals processing if it's not a dictionary
                self.logger.warning(f"Fundamentals data is not a dictionary (type: {type(fund)}), skipping fundamentals processing")
                fund = {}
            
            # Extract from filtered comprehensive data structure
            company_info = fund.get('company_info', {})
            financial_health = fund.get('financial_health', {})
            valuation_metrics = fund.get('valuation_metrics', {})
            stock_technicals = fund.get('stock_technicals', {})
            dividend_info = fund.get('dividend_info', {})
            analyst_sentiment = fund.get('analyst_sentiment', {})
            ownership_structure = fund.get('ownership_structure', {})
            balance_sheet = fund.get('balance_sheet', {})
            income_statement = fund.get('income_statement', {})
            cash_flow = fund.get('cash_flow', {})
            
            result['fundamentals'] = {
                # Company basics
                'company_name': company_info.get('name', ''),
                'sector': company_info.get('sector', ''),
                'industry': company_info.get('industry', ''),
                'market_capitalization': (company_info.get('market_cap_mln', 0) or 0) * 1000000,
                'employees': company_info.get('employees', 0),
                'description': company_info.get('description', ''),
                
                # Valuation metrics
                'pe_ratio': valuation_metrics.get('pe_ratio') or 0,
                'forward_pe': valuation_metrics.get('forward_pe') or 0,
                'price_to_sales': valuation_metrics.get('price_to_sales') or 0,
                'price_to_book': valuation_metrics.get('price_to_book') or 0,
                'enterprise_value': valuation_metrics.get('enterprise_value') or 0,
                'ev_to_revenue': valuation_metrics.get('ev_to_revenue') or 0,
                'ev_to_ebitda': valuation_metrics.get('ev_to_ebitda') or 0,
                
                # Technical/Risk metrics
                'beta': stock_technicals.get('beta') or 0,
                '52_week_high': stock_technicals.get('52_week_high') or 0,
                '52_week_low': stock_technicals.get('52_week_low') or 0,
                'fifty_day_ma': stock_technicals.get('50_day_ma') or 0,
                'two_hundred_day_ma': stock_technicals.get('200_day_ma') or 0,
                'short_interest': stock_technicals.get('short_interest') or 0,
                'short_ratio': stock_technicals.get('short_ratio') or 0,
                
                # Profitability metrics
                'eps_ttm': financial_health.get('eps_ttm') or 0,
                'profit_margin': financial_health.get('profit_margin') or 0,
                'operating_margin': financial_health.get('operating_margin') or 0,
                'roe': financial_health.get('roe') or 0,
                'roa': financial_health.get('roa') or 0,
                'revenue_ttm': financial_health.get('revenue_ttm') or 0,
                'revenue_per_share': financial_health.get('revenue_per_share') or 0,
                
                # Growth metrics
                'revenue_growth_yoy': financial_health.get('revenue_growth_yoy') or 0,
                'earnings_growth_yoy': financial_health.get('earnings_growth_yoy') or 0,
                'eps_estimate_current_year': financial_health.get('eps_estimate_current_year') or 0,
                'eps_estimate_next_year': financial_health.get('eps_estimate_next_year') or 0,
                
                # Dividend information (critical for PMCC)
                'dividend_yield': financial_health.get('dividend_yield') or dividend_info.get('forward_dividend_yield') or 0,
                'dividend_per_share': financial_health.get('dividend_per_share') or dividend_info.get('forward_dividend_rate') or 0,
                'payout_ratio': dividend_info.get('payout_ratio') or 0,
                'dividend_date': dividend_info.get('dividend_date'),
                'ex_dividend_date': dividend_info.get('ex_dividend_date'),
                
                # Analyst sentiment
                'analyst_rating': analyst_sentiment.get('avg_rating'),  # 1=Strong Buy, 5=Strong Sell
                'target_price': analyst_sentiment.get('target_price') or 0,
                'strong_buy_count': analyst_sentiment.get('strong_buy') or 0,
                'buy_count': analyst_sentiment.get('buy') or 0,
                'hold_count': analyst_sentiment.get('hold') or 0,
                'sell_count': analyst_sentiment.get('sell') or 0,
                'strong_sell_count': analyst_sentiment.get('strong_sell') or 0,
                
                # Ownership structure
                'shares_outstanding': ownership_structure.get('shares_outstanding') or 0,
                'percent_institutions': ownership_structure.get('percent_institutions') or 0,
                'percent_insiders': ownership_structure.get('percent_insiders') or 0,
                'shares_float': ownership_structure.get('shares_float') or 0,
                
                # Balance sheet strength
                'total_assets_mln': balance_sheet.get('total_assets') or 0,
                'total_debt_mln': balance_sheet.get('total_debt') or 0,
                'cash_and_equivalents_mln': balance_sheet.get('cash_and_equivalents') or 0,
                'net_debt_mln': balance_sheet.get('net_debt') or 0,
                'working_capital_mln': balance_sheet.get('working_capital') or 0,
                'shareholders_equity_mln': balance_sheet.get('shareholders_equity') or 0,
                'debt_to_equity': balance_sheet.get('debt_to_equity') or 0,
                
                # Income statement
                'total_revenue_mln': income_statement.get('total_revenue') or 0,
                'gross_profit_mln': income_statement.get('gross_profit') or 0,
                'operating_income_mln': income_statement.get('operating_income') or 0,
                'net_income_mln': income_statement.get('net_income') or 0,
                'ebitda_mln': income_statement.get('ebitda') or 0,
                'gross_margin': income_statement.get('gross_margin') or 0,
                'net_margin': income_statement.get('net_margin') or 0,
                
                # Cash flow (comprehensive)
                'operating_cash_flow_mln': cash_flow.get('operating_cash_flow') or 0,
                'free_cash_flow_mln': cash_flow.get('free_cash_flow') or 0,
                'capex_mln': cash_flow.get('capex') or cash_flow.get('capital_expenditures') or 0,
                'net_income_cf_mln': cash_flow.get('net_income') or 0,  # Net income from cash flow statement
                'cash_change_mln': cash_flow.get('cash_change') or cash_flow.get('change_in_cash') or 0,
                'dividends_paid_mln': cash_flow.get('dividends_paid') or 0
            }
            
            # Enhanced balance sheet data extraction for Claude
            result['balance_sheet'] = {
                'total_assets': balance_sheet.get('total_assets') or 0,
                'total_debt': balance_sheet.get('total_debt') or 0, 
                'cash_and_equivalents': balance_sheet.get('cash_and_equivalents') or 0,
                'net_debt': balance_sheet.get('net_debt') or 0,
                'working_capital': balance_sheet.get('working_capital') or 0,
                'shareholders_equity': balance_sheet.get('shareholders_equity') or 0,
                'debt_to_equity': balance_sheet.get('debt_to_equity') or 0
            }
            
            # Enhanced cash flow data extraction for Claude
            result['cash_flow'] = {
                'operating_cash_flow': cash_flow.get('operating_cash_flow') or 0,
                'free_cash_flow': cash_flow.get('free_cash_flow') or 0,
                'capex': cash_flow.get('capex') or cash_flow.get('capital_expenditures') or 0,
                'net_income': cash_flow.get('net_income') or 0,
                'cash_change': cash_flow.get('cash_change') or cash_flow.get('change_in_cash') or 0,
                'dividends_paid': cash_flow.get('dividends_paid') or 0
            }
            
            # Enhanced income statement data extraction for Claude
            result['income_statement'] = {
                'total_revenue': income_statement.get('total_revenue') or 0,
                'gross_profit': income_statement.get('gross_profit') or 0,
                'operating_income': income_statement.get('operating_income') or 0,
                'net_income': income_statement.get('net_income') or 0,
                'ebitda': income_statement.get('ebitda') or 0,
                'gross_margin': income_statement.get('gross_margin') or 0,
                'operating_margin': income_statement.get('operating_margin') or 0,
                'net_margin': income_statement.get('net_margin') or 0,
                'quarter_date': income_statement.get('quarter_date', '')
            }
            
            # Enhanced analyst sentiment data extraction for Claude
            result['analyst_sentiment'] = {
                'avg_rating': analyst_sentiment.get('avg_rating') or 0,
                'target_price': analyst_sentiment.get('target_price') or 0,
                'strong_buy': analyst_sentiment.get('strong_buy') or 0,
                'buy': analyst_sentiment.get('buy') or 0,
                'hold': analyst_sentiment.get('hold') or 0,
                'sell': analyst_sentiment.get('sell') or 0,
                'strong_sell': analyst_sentiment.get('strong_sell') or 0,
                'total_analysts': analyst_sentiment.get('total_analysts') or 0,
                'price_target_high': analyst_sentiment.get('price_target_high') or 0,
                'price_target_low': analyst_sentiment.get('price_target_low') or 0
            }
            
            # Update market cap in quote if available
            if result.get('quote') and result['fundamentals']['market_capitalization'] > 0:
                result['quote']['market_cap'] = result['fundamentals']['market_capitalization']
                
        elif enhanced_data and hasattr(enhanced_data, 'fundamentals') and enhanced_data.fundamentals:
            # Legacy format fallback
            fund = enhanced_data.fundamentals
            result['fundamentals'] = {
                'market_capitalization': float(fund.market_capitalization) if fund.market_capitalization else 0,
                'pe_ratio': float(fund.pe_ratio) if fund.pe_ratio else 0,
                'roe': float(fund.roe) if fund.roe else 0,
                'roa': float(fund.roa) if fund.roa else 0,
                'profit_margin': float(fund.profit_margin) if fund.profit_margin else 0,
                'debt_to_equity': float(fund.debt_to_equity) if fund.debt_to_equity else 0
            }
        
        # Technical indicators from comprehensive data
        if comprehensive_data and 'technical_indicators' in comprehensive_data and comprehensive_data['technical_indicators']:
            tech_data = comprehensive_data['technical_indicators']
            result['technical_indicators'] = {}
            
            # Validate that tech_data is actually a dictionary
            if not isinstance(tech_data, dict):
                self.logger.warning(f"Technical indicators data is not a dict: {type(tech_data)}")
                tech_data = {}
            
            # Process each indicator type
            for indicator_name, indicator_data in tech_data.items():
                try:
                    # DEBUG: Log each indicator data for troubleshooting
                    self.logger.debug(f"Processing indicator {indicator_name}: type={type(indicator_data)}, value={str(indicator_data)[:100]}")
                    
                    # Handle different data formats with validation
                    if indicator_data is None:
                        self.logger.debug(f"Technical indicator {indicator_name} is None")
                        continue
                    elif isinstance(indicator_data, str):
                        self.logger.warning(f"Technical indicator {indicator_name} is string format, skipping: {indicator_data[:50]}...")
                        continue
                    elif isinstance(indicator_data, list) and len(indicator_data) > 0:
                        # Get the most recent value (first item due to 'd' order)
                        self.logger.debug(f"Indicator {indicator_name} has {len(indicator_data)} items, first item type: {type(indicator_data[0])}")
                        latest = indicator_data[0] if isinstance(indicator_data[0], dict) else indicator_data[-1]
                        self.logger.debug(f"Latest value for {indicator_name}: type={type(latest)}, value={latest}")
                        
                        # Extra validation before using 'latest'
                        if isinstance(latest, str):
                            self.logger.error(f"ERROR: latest is a string for {indicator_name}: '{latest}'")
                            print(f"🚨 DEBUG: Found string 'latest' for {indicator_name}: '{latest[:100]}...'")
                            continue
                        
                        # Check if latest is actually a dict
                        if not isinstance(latest, dict):
                            self.logger.warning(f"Technical indicator {indicator_name} latest value is not a dict: {type(latest)}, value: {latest}")
                            continue
                    elif isinstance(indicator_data, dict):
                        # Single dictionary result
                        latest = indicator_data
                    else:
                        self.logger.warning(f"Technical indicator {indicator_name} has unexpected format: {type(indicator_data)}")
                        continue
                    
                    # Process validated dictionary data
                    if indicator_name == 'rsi':
                        rsi_value = latest.get('rsi', 0)
                        result['technical_indicators']['rsi_14d'] = float(rsi_value) if rsi_value and str(rsi_value).replace('.', '').isdigit() else 0
                    elif indicator_name == 'volatility':
                        vol_value = latest.get('volatility', 0)
                        result['technical_indicators']['volatility_30d'] = float(vol_value) if vol_value and str(vol_value).replace('.', '').isdigit() else 0
                    elif indicator_name == 'atr':
                        atr_value = latest.get('atr', 0)
                        result['technical_indicators']['atr'] = float(atr_value) if atr_value and str(atr_value).replace('.', '').isdigit() else 0
                    elif indicator_name == 'beta':
                        beta_value = latest.get('beta', 0)
                        result['technical_indicators']['beta'] = float(beta_value) if beta_value and str(beta_value).replace('.', '').replace('-', '').isdigit() else 0
                    
                    # Add date context if available
                    latest_date = latest.get('date')
                    if latest_date:
                        result['technical_indicators'][f'{indicator_name}_date'] = latest_date
                        
                except Exception as e:
                    self.logger.error(f"Error processing technical indicator {indicator_name}: {e}")
                    continue
                        
            # Fill in from fundamentals if technical indicators are missing
            if result.get('fundamentals') and isinstance(result['fundamentals'], dict):
                if not result['technical_indicators'].get('beta') and result['fundamentals'].get('beta'):
                    result['technical_indicators']['beta'] = result['fundamentals']['beta']
                    
        elif enhanced_data and hasattr(enhanced_data, 'technical_indicators') and enhanced_data.technical_indicators:
            # Legacy format fallback
            tech = enhanced_data.technical_indicators
            result['technical_indicators'] = {
                'beta': float(tech.beta) if tech.beta else 0,
                'rsi_14d': float(tech.rsi_14d) if hasattr(tech, 'rsi_14d') and tech.rsi_14d else 0,
                'volatility_30d': float(tech.volatility_30d) if hasattr(tech, 'volatility_30d') and tech.volatility_30d else 0
            }
        
        # Recent news for market sentiment context - FULL ARTICLES for Claude AI
        if comprehensive_data and 'news' in comprehensive_data and comprehensive_data['news']:
            news_data = comprehensive_data['news']
            result['recent_news'] = []
            
            news_list = news_data if isinstance(news_data, list) else [news_data]
            for news_item in news_list[:5]:  # Limit to 5 most recent
                if isinstance(news_item, dict):
                    # DO NOT include sentiment ratings - let Claude judge sentiment
                    # Include FULL news content for Claude analysis
                    news_entry = {
                        'date': news_item.get('date', ''),
                        'title': news_item.get('title', ''),  # No truncation of title
                        'content': news_item.get('content', ''),  # FULL CONTENT - no truncation
                        'source': news_item.get('source', '')
                        # Explicitly excluded: sentiment data - let Claude assess
                    }
                    
                    # Only add non-empty news items
                    if news_entry['title'] or news_entry['content']:
                        result['recent_news'].append(news_entry)
        
        # Earnings and calendar data (include historical for pattern analysis)
        if comprehensive_data and 'earnings' in comprehensive_data and comprehensive_data['earnings']:
            earnings_data = comprehensive_data['earnings']
            result['earnings_calendar'] = []
            
            if isinstance(earnings_data, dict):
                # Handle dict format from EODHD API
                earnings_list = earnings_data.get('earnings', []) if 'earnings' in earnings_data else [earnings_data]
            else:
                earnings_list = earnings_data if isinstance(earnings_data, list) else [earnings_data]
            
            # Include ALL earnings (historical + future) for Claude to analyze patterns
            # Sort by report_date if available, otherwise by date
            from datetime import datetime
            
            sorted_earnings = []
            for earnings in earnings_list:
                if isinstance(earnings, dict):
                    # Parse dates for sorting
                    report_date_str = earnings.get('report_date', '')
                    date_str = earnings.get('date', '')
                    
                    # Use report_date for sorting if available
                    sort_date_str = report_date_str if report_date_str else date_str
                    if sort_date_str:
                        try:
                            sort_date = datetime.strptime(sort_date_str, '%Y-%m-%d')
                            earnings['_sort_date'] = sort_date
                            sorted_earnings.append(earnings)
                        except:
                            pass
            
            # Sort by date (newest first)
            sorted_earnings.sort(key=lambda x: x.get('_sort_date', datetime.min), reverse=True)
            
            # Include last 12 months of history + all future earnings
            today = datetime.now()
            one_year_ago = today.replace(year=today.year - 1)
            
            for earnings in sorted_earnings:
                if isinstance(earnings, dict):
                    # Include if future or within last 12 months
                    sort_date = earnings.get('_sort_date')
                    if sort_date and (sort_date > today or sort_date > one_year_ago):
                        entry = {
                            'date': earnings.get('date', ''),  # Quarter end date
                            'report_date': earnings.get('report_date', ''),  # Actual announcement date
                            'eps_estimate': earnings.get('estimate'),  # EODHD uses 'estimate'
                            'eps_actual': earnings.get('actual'),      # EODHD uses 'actual'
                            'time': earnings.get('before_after_market', ''),  # EODHD field
                            'currency': earnings.get('currency', 'USD'),
                            'difference': earnings.get('difference'),  # EPS surprise amount
                            'percent': earnings.get('percent')  # EPS surprise percentage
                        }
                        
                        # Add parsed dates for easy use
                        if earnings.get('date'):
                            entry['parsed_date'] = earnings.get('date')
                        if earnings.get('report_date') and earnings.get('date') != earnings.get('report_date'):
                            entry['quarter_date'] = earnings.get('date')
                        
                        result['earnings_calendar'].append(entry)
        
        # Economic events for macro context
        if comprehensive_data and 'economic_events' in comprehensive_data and comprehensive_data['economic_events']:
            econ_data = comprehensive_data['economic_events']
            result['economic_context'] = []
            
            econ_list = econ_data if isinstance(econ_data, list) else [econ_data]
            for event in econ_list[:5]:  # Limit to 5 key economic events
                if isinstance(event, dict):
                    result['economic_context'].append({
                        'date': event.get('date', ''),
                        'event': event.get('type', ''),  # EODHD uses 'type' not 'event'
                        'country': event.get('country', ''),
                        'actual': event.get('actual'),
                        'estimate': event.get('estimate'),
                        'previous': event.get('previous'),
                        'impact': 'medium'  # EODHD doesn't provide impact level
                    })
        
        # Market sentiment analysis
        if comprehensive_data and 'sentiment' in comprehensive_data and comprehensive_data['sentiment']:
            sentiment_data = comprehensive_data['sentiment']
            if isinstance(sentiment_data, dict):
                # Handle EODHD sentiment format: {ticker: [sentiment_data]}
                # Get the first key (ticker) from the sentiment dict
                ticker_key = list(sentiment_data.keys())[0] if sentiment_data else None
                if ticker_key and isinstance(sentiment_data[ticker_key], list) and len(sentiment_data[ticker_key]) > 0:
                    # Get the most recent sentiment data
                    latest_sentiment = sentiment_data[ticker_key][0]
                    if isinstance(latest_sentiment, dict):
                        # Calculate overall sentiment from normalized score
                        normalized_score = float(latest_sentiment.get('normalized', 0))
                        overall_sentiment = 'neutral'
                        if normalized_score > 0.5:
                            overall_sentiment = 'bullish'
                        elif normalized_score < -0.5:
                            overall_sentiment = 'bearish'
                        
                        result['market_sentiment'] = {
                            'overall_sentiment': overall_sentiment,
                            'sentiment_score': normalized_score,
                            'bullish_percent': 0,  # Not provided in EODHD data
                            'bearish_percent': 0,  # Not provided in EODHD data
                            'buzz': int(latest_sentiment.get('count', 0)),
                            'last_updated': latest_sentiment.get('date', '')
                        }
                else:
                    # Fallback format handling
                    result['market_sentiment'] = {
                        'overall_sentiment': sentiment_data.get('sentiment', 'neutral'),
                        'sentiment_score': float(sentiment_data.get('sentiment_score', 0)) if sentiment_data.get('sentiment_score') else 0,
                        'bullish_percent': float(sentiment_data.get('bullish_percent', 0)) if sentiment_data.get('bullish_percent') else 0,
                        'bearish_percent': float(sentiment_data.get('bearish_percent', 0)) if sentiment_data.get('bearish_percent') else 0,
                        'buzz': sentiment_data.get('buzz', 0),
                        'last_updated': sentiment_data.get('date', '')
                    }
        
        # Historical prices (last 30 days) for trend analysis and Claude context
        if comprehensive_data and 'historical_prices' in comprehensive_data and comprehensive_data['historical_prices'] is not None:
            hist_data = comprehensive_data['historical_prices']
            if hasattr(hist_data, 'iloc') and not hist_data.empty and len(hist_data) >= 5:
                # Calculate key price levels and trends
                prices = hist_data['adjusted_close'].values if 'adjusted_close' in hist_data.columns else hist_data['close'].values
                volumes = hist_data['volume'].values if 'volume' in hist_data.columns else [0] * len(prices)
                
                result['price_analysis'] = {
                    'thirty_day_high': float(max(prices)) if len(prices) > 0 else 0,
                    'thirty_day_low': float(min(prices)) if len(prices) > 0 else 0,
                    'thirty_day_avg': float(sum(prices) / len(prices)) if len(prices) > 0 else 0,
                    'avg_volume_30d': float(sum(volumes) / len(volumes)) if len(volumes) > 0 else 0,
                    'price_trend': 'bullish' if len(prices) >= 2 and prices[-1] > prices[0] else 'bearish' if len(prices) >= 2 else 'neutral',
                    'volatility_30d': float(hist_data['close'].std()) if 'close' in hist_data.columns else 0
                }
                
                # Include detailed historical prices for Claude analysis (last 30 days max)
                historical_prices = []
                # Limit to last 30 days and convert DataFrame to list of dicts
                for idx in range(min(30, len(hist_data))):
                    row = hist_data.iloc[-(idx+1)]  # Start from most recent
                    price_entry = {
                        'date': str(row.name) if hasattr(row, 'name') else str(row.get('date', '')),
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('adjusted_close', row.get('close', 0))),
                        'volume': int(row.get('volume', 0))
                    }
                    # Only include entries with meaningful data
                    if price_entry['close'] > 0:
                        historical_prices.append(price_entry)
                
                if historical_prices:
                    result['historical_prices'] = historical_prices
        
        # Legacy calendar events handling for backward compatibility
        if enhanced_data and hasattr(enhanced_data, 'calendar_events') and enhanced_data.calendar_events:
            result['calendar_events'] = {
                'next_earnings_date': None,
                'next_ex_dividend_date': None,
                'dividend_yield': None,
                'upcoming_events': []
            }
            
            for event in enhanced_data.calendar_events[:10]:  # Limit to 10 most recent
                event_dict = {
                    'event_type': event.event_type,
                    'date': event.date.isoformat() if hasattr(event.date, 'isoformat') else str(event.date),
                    'announcement_time': event.announcement_time,
                }
                result['calendar_events']['upcoming_events'].append(event_dict)
        
        # Apply data filtering - remove null/empty fields before final package
        result = self._filter_null_empty_fields(result)
        
        # Data completeness and freshness indicators
        data_completeness = {
            'has_quote_data': bool(result.get('quote')),
            'has_fundamental_data': bool(result.get('fundamentals')),
            'has_balance_sheet_data': bool(result.get('balance_sheet')),
            'has_cash_flow_data': bool(result.get('cash_flow')),
            'has_historical_prices': bool(result.get('historical_prices')),
            'has_analyst_sentiment': bool(result.get('analyst_sentiment')),
            'has_technical_indicators': bool(result.get('technical_indicators')),
            'has_recent_news': bool(result.get('recent_news')),
            'has_earnings_calendar': bool(result.get('earnings_calendar')),
            'has_economic_context': bool(result.get('economic_context')),
            'has_market_sentiment': bool(result.get('market_sentiment')),
            'has_price_analysis': bool(result.get('price_analysis')),
            'data_timestamp': datetime.now().isoformat(),
            'comprehensive_data_available': bool(comprehensive_data)
        }
        
        # Calculate completeness score
        total_categories = 12  # quote, fundamentals, balance_sheet, cash_flow, historical_prices, analyst_sentiment, technical, news, earnings, economic, sentiment, price_analysis
        available_categories = sum([
            data_completeness['has_quote_data'],
            data_completeness['has_fundamental_data'],
            data_completeness['has_balance_sheet_data'],
            data_completeness['has_cash_flow_data'],
            data_completeness['has_historical_prices'],
            data_completeness['has_analyst_sentiment'],
            data_completeness['has_technical_indicators'],
            data_completeness['has_recent_news'],
            data_completeness['has_earnings_calendar'],
            data_completeness['has_economic_context'],
            data_completeness['has_market_sentiment'],
            data_completeness['has_price_analysis']
        ])
        
        completeness_score = (available_categories / total_categories) * 100
        data_completeness['completeness_score'] = round(completeness_score, 1)
        
        result['data_completeness'] = data_completeness
        
        # Legacy compatibility fields
        if enhanced_data and hasattr(enhanced_data, 'risk_metrics') and enhanced_data.risk_metrics:
            risk = enhanced_data.risk_metrics
            result['risk_metrics'] = {
                'institutional_ownership': float(risk.institutional_ownership) if risk.institutional_ownership else 0,
                'analyst_rating_avg': float(risk.analyst_rating_avg) if risk.analyst_rating_avg else 0,
                'price_target_avg': float(risk.price_target_avg) if risk.price_target_avg else 0
            }
        
        # Options chain (if available from legacy format)
        if enhanced_data and hasattr(enhanced_data, 'options_chain') and enhanced_data.options_chain:
            result['options_chain'] = {
                'underlying': enhanced_data.options_chain.underlying,
                'underlying_price': float(enhanced_data.options_chain.underlying_price),
                'contract_count': len(enhanced_data.options_chain.contracts) if enhanced_data.options_chain.contracts else 0
            }
        
        # Add comprehensive data debug info
        if comprehensive_data:
            result['debug_info'] = {
                'comprehensive_data_keys': list(comprehensive_data.keys()),
                'data_sources_available': {
                    'economic_events': bool(comprehensive_data.get('economic_events')),
                    'news': bool(comprehensive_data.get('news')),
                    'fundamentals': bool(comprehensive_data.get('fundamentals')),
                    'balance_sheet': bool(comprehensive_data.get('fundamentals', {}).get('balance_sheet') if isinstance(comprehensive_data.get('fundamentals'), dict) else False),
                    'cash_flow': bool(comprehensive_data.get('fundamentals', {}).get('cash_flow') if isinstance(comprehensive_data.get('fundamentals'), dict) else False),
                    'analyst_sentiment': bool(comprehensive_data.get('fundamentals', {}).get('analyst_sentiment') if isinstance(comprehensive_data.get('fundamentals'), dict) else False),
                    'live_price': bool(comprehensive_data.get('live_price')),
                    'earnings': bool(comprehensive_data.get('earnings')),
                    'historical_prices': comprehensive_data.get('historical_prices') is not None and (not hasattr(comprehensive_data.get('historical_prices'), 'empty') or not comprehensive_data.get('historical_prices').empty),
                    'sentiment': bool(comprehensive_data.get('sentiment')),
                    'technical_indicators': bool(comprehensive_data.get('technical_indicators'))
                }
            }
        
        return result
    
    def _filter_null_empty_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out null, empty, or meaningless fields from data before sending to Claude.
        
        This ensures Claude receives only meaningful data for analysis and prevents
        token waste on empty fields.
        
        Args:
            data: Dictionary of data to filter
            
        Returns:
            Filtered dictionary with null/empty fields removed
        """
        # Critical sections that should be preserved even if they contain zeros
        PRESERVE_SECTIONS = {'balance_sheet', 'cash_flow', 'income_statement', 'historical_prices', 'analyst_sentiment'}
        
        def is_meaningful_value(value, key=None, parent_key=None):
            """Check if a value is meaningful (not null, empty, or meaningless)."""
            import pandas as pd
            
            if value is None:
                return False
            if isinstance(value, str):
                # Remove empty strings and meaningless values
                if not value.strip() or value.lower() in ['n/a', 'none', 'unknown', 'null', '0', '0.0']:
                    return False
            elif isinstance(value, pd.DataFrame):
                # Handle pandas DataFrames - check if empty
                return not value.empty
            elif isinstance(value, (list, dict)):
                # Remove empty collections
                if len(value) == 0:
                    return False
            elif isinstance(value, (int, float)):
                # For critical financial sections, preserve zero values
                if parent_key in PRESERVE_SECTIONS:
                    return True  # Keep zeros in financial data
                # Remove all zero values per user requirement
                if value == 0 or value == 0.0:
                    return False
            return True
        
        def filter_dict(d, parent_key=None):
            """Recursively filter dictionary."""
            import pandas as pd
            
            if not isinstance(d, dict):
                return d
            
            filtered = {}
            for key, value in d.items():
                # Special handling for DataFrames - skip filtering
                if isinstance(value, pd.DataFrame):
                    if not value.empty:
                        filtered[key] = value
                    continue
                
                # Special handling for news items - remove sentiment
                if key in ['recent_news', 'news'] and isinstance(value, list):
                    filtered_news = []
                    for news_item in value:
                        if isinstance(news_item, dict):
                            # Remove sentiment from news
                            news_copy = {k: v for k, v in news_item.items() if k != 'sentiment'}
                            filtered_news_item = filter_dict(news_copy, key)
                            if filtered_news_item:
                                filtered_news.append(filtered_news_item)
                    if filtered_news:
                        filtered[key] = filtered_news
                elif isinstance(value, dict):
                    # Pass the current key as parent_key for nested dicts
                    filtered_sub = filter_dict(value, key)
                    # For preserved sections, keep even if empty after filtering
                    if filtered_sub or key in PRESERVE_SECTIONS:
                        filtered[key] = filtered_sub
                elif isinstance(value, list):
                    filtered_list = []
                    for item in value:
                        if isinstance(item, dict):
                            filtered_item = filter_dict(item, key)
                            if filtered_item:
                                filtered_list.append(filtered_item)
                        elif is_meaningful_value(item, None, key):
                            filtered_list.append(item)
                    if filtered_list:
                        filtered[key] = filtered_list
                elif is_meaningful_value(value, key, parent_key):
                    filtered[key] = value
            
            return filtered
        
        return filter_dict(data, None)
    
    def scan(self, config: Optional[ScanConfiguration] = None) -> ScanResults:
        """
        Perform a complete PMCC scan.
        
        Args:
            config: Scan configuration (uses defaults if None)
            
        Returns:
            ScanResults with all discovered opportunities
        """
        if config is None:
            config = ScanConfiguration()
        
        # Generate unique scan ID
        scan_id = f"pmcc_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize results
        results = ScanResults(
            scan_id=scan_id,
            started_at=datetime.now(),
            configuration=config
        )
        
        # Initialize provider usage tracking for this scan
        self.current_scan_usage = {}
        self.current_operation_routing = {
            'screen_stocks': [],
            'get_stock_quote': [],
            'get_options_chain': []
        }
        
        self.logger.info(f"Starting PMCC scan {scan_id} with provider factory: {self.use_provider_factory}")
        
        try:
            # Initialize options analyzer based on configuration
            self._initialize_options_analyzer(config)
            
            # Step 1: Screen stocks
            print("\n" + "=" * 80)
            print("🔍 STEP 1: SCREENING STOCKS")
            print("=" * 80)
            self.logger.info("Step 1: Screening stocks...")
            screening_results = self._screen_stocks(config, results)
            results.screening_results = screening_results
            
            if not screening_results:
                self.logger.warning("No stocks passed screening criteria")
                results.completed_at = datetime.now()
                return results
            
            # Step 2: Analyze options for each stock
            print("\n" + "=" * 80)
            print(f"📊 STEP 2: ANALYZING OPTIONS (using {config.options_source})")
            print("=" * 80)
            self.logger.info(f"Step 2: Analyzing options using {config.options_source}...")
            all_opportunities = self._analyze_options(screening_results, config, results)
            
            if not all_opportunities:
                self.logger.warning("No PMCC opportunities found")
                results.completed_at = datetime.now()
                return results
            
            # Step 3: Calculate comprehensive risk for top opportunities
            print("\n" + "=" * 80)
            print("🎯 STEP 3: CALCULATING RISK METRICS")
            print("=" * 80)
            self.logger.info("Step 3: Calculating risk metrics...")
            scored_opportunities = self._calculate_risk_metrics(all_opportunities, config, results)
            
            # Step 4: Rank and filter final results
            print("\n" + "=" * 80)
            print("🏆 STEP 4: RANKING TOP OPPORTUNITIES")
            print("=" * 80)
            self.logger.info("Step 4: Ranking opportunities...")
            final_opportunities = self._rank_and_filter(scored_opportunities, config)
            
            # Initialize enhanced workflow if configured
            enhanced_available = self._initialize_enhanced_workflow(config)
            
            # Step 5: Enhanced AI Analysis (Phase 3)
            if enhanced_available and final_opportunities:
                print("\n" + "=" * 80)
                print("🧠 STEP 5: AI-ENHANCED ANALYSIS")
                print("=" * 80)
                self.logger.info(
                    f"Step 5: Performing AI-enhanced analysis on {len(final_opportunities)} opportunities"
                    f" (Enhanced data collection: {config.enhanced_data_collection_enabled}, "
                    f"Claude AI: {config.claude_analysis_enabled})"
                )
                
                try:
                    enhanced_start_time = datetime.now()
                    final_opportunities = self._perform_enhanced_analysis(
                        final_opportunities, config, results
                    )
                    enhanced_duration = (datetime.now() - enhanced_start_time).total_seconds()
                    
                    self.logger.info(
                        f"Enhanced analysis completed in {enhanced_duration:.2f} seconds. "
                        f"Selected {len(final_opportunities)} top opportunities from AI analysis."
                    )
                    
                except Exception as e:
                    self.logger.error(f"Enhanced analysis failed: {e}", exc_info=True)
                    results.errors.append(f"Enhanced analysis error: {str(e)}")
                    # Continue with standard results if enhanced analysis fails
            else:
                if not enhanced_available:
                    self.logger.info("Enhanced workflow not available - skipping AI analysis")
                if not final_opportunities:
                    self.logger.info("No opportunities available for enhanced analysis")
            
            results.top_opportunities = final_opportunities
            results.opportunities_found = len(all_opportunities)
            
            # Complete scan
            results.completed_at = datetime.now()
            duration = (results.completed_at - results.started_at).total_seconds()
            results.total_duration_seconds = duration
            
            # Add provider usage statistics to results
            results.provider_usage = self.current_scan_usage.copy()
            results.operation_routing = self.current_operation_routing.copy()
            
            # Log provider usage summary
            self._log_provider_usage_summary()
            
            # Auto-export results in both formats with historical preservation
            try:
                json_file = self.export_results(results, format="json")
                csv_file = self.export_results(results, format="csv")
                self.logger.info(f"Results exported to {json_file} and {csv_file}")
            except Exception as e:
                self.logger.warning(f"Error auto-exporting results: {e}")
            
            self.logger.info(
                f"Scan completed: {len(final_opportunities)} opportunities found "
                f"in {duration:.1f} seconds"
            )
            
        except Exception as e:
            self.logger.error(f"Error during scan: {e}")
            results.errors.append(f"Scan error: {str(e)}")
            results.completed_at = datetime.now()
            
            # Still add provider usage statistics even on error
            results.provider_usage = self.current_scan_usage.copy()
            results.operation_routing = self.current_operation_routing.copy()
        
        return results
    
    def scan_symbol(self, symbol: str, config: Optional[ScanConfiguration] = None) -> List[PMCCCandidate]:
        """
        Scan a specific symbol for PMCC opportunities.
        
        Args:
            symbol: Stock symbol to analyze
            config: Scan configuration
            
        Returns:
            List of PMCCCandidate objects for the symbol
        """
        if config is None:
            config = ScanConfiguration()
        
        self.logger.info(f"Scanning {symbol} for PMCC opportunities")
        
        try:
            if self.use_provider_factory:
                return self._scan_symbol_with_provider_factory(symbol, config)
            else:
                return self._scan_symbol_legacy(symbol, config)
                
        except Exception as e:
            self.logger.error(f"Error scanning {symbol}: {e}")
            return []
    
    def _scan_symbol_with_provider_factory(self, symbol: str, config: ScanConfiguration) -> List[PMCCCandidate]:
        """Scan symbol using provider factory."""
        import time
        
        # Get quote provider (prefer MarketData for quotes)
        quote_provider = self.provider_factory.get_provider(
            "get_stock_quote",
            preferred_provider=ProviderType.MARKETDATA
        )
        
        if not quote_provider:
            self.logger.error(f"No provider available for stock quotes")
            return []
        
        # Get current quote
        start_time = time.time()
        quote_response = quote_provider.get_stock_quote(symbol)
        quote_time = (time.time() - start_time) * 1000
        
        if not quote_response.is_success:
            self.logger.warning(f"Could not get quote for {symbol} from {quote_provider.provider_type.value}: {quote_response.error}")
            self._track_provider_usage(quote_provider.provider_type, "get_stock_quote", quote_time, False)
            return []
        
        quote = quote_response.data
        self._track_provider_usage(quote_provider.provider_type, "get_stock_quote", quote_time, True, credits_used=1)
        
        # Initialize options analyzer if needed
        if not self.options_analyzer:
            self.logger.info(f"Initializing options analyzer for {symbol} with config.options_source={config.options_source}")
            self._initialize_options_analyzer(config)
        
        # Find PMCC opportunities and get complete option chain
        result = self.options_analyzer.find_pmcc_opportunities(
            symbol, config.leaps_criteria, config.short_criteria, 
            return_option_chain=True
        )
        if isinstance(result, tuple):
            opportunities, option_chain = result
            # Save the complete option chain for AI analysis
            if option_chain and results:
                results.analyzed_option_chains[symbol] = option_chain
        else:
            # Backward compatibility if option chain not returned
            opportunities = result
            option_chain = None
        
        # Convert to PMCCCandidate objects
        candidates = []
        for opp in opportunities:
            try:
                # Create PMCCAnalysis
                analysis = PMCCAnalysis(
                    long_call=opp.leaps_contract,
                    short_call=opp.short_contract,
                    underlying=quote,
                    net_debit=opp.net_debit,
                    credit_received=opp.short_contract.bid,
                    analyzed_at=datetime.now()
                )
                
                # Calculate risk metrics
                analysis.risk_metrics = analysis.calculate_risk_metrics()
                analysis.liquidity_score = analysis.calculate_liquidity_score()
                
                # Create candidate
                candidate = PMCCCandidate(
                    symbol=symbol,
                    underlying_price=quote.last or quote.mid or Decimal('0'),
                    analysis=analysis,
                    liquidity_score=opp.liquidity_score,
                    total_score=opp.total_score,
                    complete_option_chain=option_chain,  # Include complete option chain for AI analysis
                    discovered_at=datetime.now()
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.warning(f"Error creating candidate for {symbol}: {e}")
                continue
        
        # Sort by total score
        candidates.sort(key=lambda x: x.total_score or Decimal('0'), reverse=True)
        
        self.logger.info(f"Found {len(candidates)} PMCC candidates for {symbol}")
        return candidates
    
    async def scan_symbols(self, symbols: List[str], config: Optional[ScanConfiguration] = None, max_opportunities: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scan multiple symbols for PMCC opportunities with enhanced workflow support.
        
        This method scans a list of symbols and returns PMCC analysis results.
        It supports both the traditional PMCC analysis workflow and the enhanced
        AI-powered workflow when enabled.
        
        Args:
            symbols: List of stock symbols to analyze
            config: Scan configuration (uses defaults if None)
            max_opportunities: Maximum number of opportunities to return
            
        Returns:
            List of dictionaries containing PMCC opportunity analysis results
        """
        if config is None:
            config = ScanConfiguration()
        
        if max_opportunities is not None:
            config.max_opportunities = max_opportunities
            
        self.logger.info(f"Starting scan_symbols for {len(symbols)} symbols: {symbols}")
        
        all_results = []
        
        try:
            # Process each symbol
            for symbol in symbols:
                self.logger.info(f"Scanning symbol: {symbol}")
                
                # Get PMCC candidates for this symbol
                candidates = self.scan_symbol(symbol, config)
                
                # Convert PMCCCandidate objects to dictionaries for AI processing
                for candidate in candidates:
                    try:
                        result_dict = {
                            'symbol': candidate.symbol,
                            'underlying_price': float(candidate.underlying_price),
                            'pmcc_score': float(candidate.total_score or 0),
                            'liquidity_score': float(candidate.liquidity_score or 0),
                            'discovered_at': candidate.discovered_at.isoformat(),
                            
                            # Analysis data
                            'analysis': {
                                'net_debit': float(candidate.analysis.net_debit),
                                'credit_received': float(candidate.analysis.credit_received),
                                'analyzed_at': candidate.analysis.analyzed_at.isoformat(),
                                'liquidity_score': float(candidate.analysis.liquidity_score or 0),
                                
                                # Long call details
                                'long_call': {
                                    'symbol': candidate.analysis.long_call.symbol,
                                    'strike': float(candidate.analysis.long_call.strike),
                                    'expiration': candidate.analysis.long_call.expiration.isoformat(),
                                    'bid': float(candidate.analysis.long_call.bid or 0),
                                    'ask': float(candidate.analysis.long_call.ask or 0),
                                    'last': float(candidate.analysis.long_call.last or 0),
                                    'delta': float(candidate.analysis.long_call.delta or 0),
                                    'gamma': float(candidate.analysis.long_call.gamma or 0),
                                    'theta': float(candidate.analysis.long_call.theta or 0),
                                    'vega': float(candidate.analysis.long_call.vega or 0)
                                },
                                
                                # Short call details
                                'short_call': {
                                    'symbol': candidate.analysis.short_call.symbol,
                                    'strike': float(candidate.analysis.short_call.strike),
                                    'expiration': candidate.analysis.short_call.expiration.isoformat(),
                                    'bid': float(candidate.analysis.short_call.bid or 0),
                                    'ask': float(candidate.analysis.short_call.ask or 0),
                                    'last': float(candidate.analysis.short_call.last or 0),
                                    'delta': float(candidate.analysis.short_call.delta or 0),
                                    'gamma': float(candidate.analysis.short_call.gamma or 0),
                                    'theta': float(candidate.analysis.short_call.theta or 0),
                                    'vega': float(candidate.analysis.short_call.vega or 0)
                                },
                                
                                # Risk metrics
                                'risk_metrics': {}
                            }
                        }
                        
                        # Add risk metrics if available
                        if candidate.analysis.risk_metrics:
                            result_dict['analysis']['risk_metrics'] = {
                                'max_profit': float(candidate.analysis.risk_metrics.max_profit or 0),
                                'max_loss': float(candidate.analysis.risk_metrics.max_loss or 0),
                                'breakeven_points': [float(bp) for bp in candidate.analysis.risk_metrics.breakeven_points] if candidate.analysis.risk_metrics.breakeven_points else [],
                                'profit_at_expiry': float(candidate.analysis.risk_metrics.profit_at_expiry or 0),
                                'time_decay_risk': float(candidate.analysis.risk_metrics.time_decay_risk or 0)
                            }
                        
                        all_results.append(result_dict)
                        
                    except Exception as e:
                        self.logger.warning(f"Error converting candidate for {symbol}: {e}")
                        continue
            
            # Sort by PMCC score
            all_results.sort(key=lambda x: x.get('pmcc_score', 0), reverse=True)
            
            # Apply max opportunities limit
            if config.max_opportunities:
                all_results = all_results[:config.max_opportunities]
            
            # Enhanced workflow: If enabled, collect enhanced data and perform AI analysis
            if config.claude_analysis_enabled and config.enhanced_data_collection_enabled:
                self.logger.info("Enhanced AI analysis enabled - performing enhanced workflow")
                
                # Initialize enhanced workflow if needed
                enhanced_enabled = self._initialize_enhanced_workflow(config)
                
                if enhanced_enabled:
                    try:
                        # Perform enhanced analysis on results
                        all_results = await self._perform_enhanced_analysis_async(all_results, symbols, config)
                    except Exception as e:
                        self.logger.warning(f"Enhanced analysis failed, continuing with traditional results: {e}")
            
            self.logger.info(f"scan_symbols completed: {len(all_results)} opportunities found")
            return all_results
            
        except Exception as e:
            self.logger.error(f"Error in scan_symbols: {e}")
            return []
    
    async def _perform_enhanced_analysis_async(self, results: List[Dict[str, Any]], symbols: List[str], config: ScanConfiguration) -> List[Dict[str, Any]]:
        """
        Perform enhanced analysis asynchronously for scan_symbols.
        
        This is a wrapper around the existing _perform_enhanced_analysis method
        to support async operation for scan_symbols.
        """
        try:
            # Convert back to PMCCCandidate format for enhanced analysis
            candidates = []
            for result in results:
                # Create a mock PMCCCandidate from result dict for enhanced analysis
                # This is a simplified version - in practice we might want to preserve full objects
                mock_candidate = type('MockPMCCCandidate', (), {
                    'symbol': result['symbol'],
                    'total_score': Decimal(str(result['pmcc_score'])),
                    'liquidity_score': Decimal(str(result['liquidity_score'])),
                    'underlying_price': Decimal(str(result['underlying_price']))
                })()
                candidates.append(mock_candidate)
            
            # Create a mock ScanResults object for the enhanced analysis
            # Import ScanResults if needed
            from src.analysis.scanner import ScanResults
            mock_scan_results = ScanResults()
            mock_scan_results.top_opportunities = candidates
            
            # Perform enhanced analysis using existing method
            enhanced_results = self._perform_enhanced_analysis(candidates, config, mock_scan_results)
            
            # If enhanced analysis was successful, merge the results
            if enhanced_results and len(enhanced_results) > 0:
                # For now, return the enhanced results as-is
                # In a full implementation, we'd merge with original results
                return results  # Returning original format for compatibility
            else:
                self.logger.warning("Enhanced analysis returned empty results, using traditional results")
                return results
                
        except Exception as e:
            self.logger.error(f"Error in enhanced analysis: {e}")
            return results
    
    def _scan_symbol_legacy(self, symbol: str, config: ScanConfiguration) -> List[PMCCCandidate]:
        """Legacy symbol scanning method."""
        # Initialize sync EODHD client if needed
        if not self.sync_eodhd_client:
            from src.api.sync_eodhd_client import SyncEODHDClient
            self.sync_eodhd_client = SyncEODHDClient(
                api_token=self.eodhd_client.api_token,
                base_url=self.eodhd_client.base_url,
                timeout=self.eodhd_client.timeout.total,
                max_retries=self.eodhd_client.max_retries,
                retry_backoff=self.eodhd_client.retry_backoff
            )
        
        # Initialize options analyzer if needed
        if not self.options_analyzer:
            # Check if this is a mock client (for testing)
            from unittest.mock import Mock
            if isinstance(self.eodhd_client, Mock):
                sync_client = Mock()
            else:
                sync_client = self.sync_eodhd_client
                
            self.options_analyzer = OptionsAnalyzer(
                data_provider=None,  # Use legacy mode
                eodhd_client=sync_client,
                api_client=self.api_client,
                options_source="eodhd"
            )
        
        # Get current quote from EODHD
        quote_response = self.sync_eodhd_client.get_stock_quote(symbol)
        if not quote_response.is_success:
            self.logger.warning(f"Could not get EODHD quote for {symbol}")
            return []
        
        quote = quote_response.data  # Already in StockQuote format from EODHD client
        
        # Find PMCC opportunities and get complete option chain
        result = self.options_analyzer.find_pmcc_opportunities(
            symbol, config.leaps_criteria, config.short_criteria, 
            return_option_chain=True
        )
        if isinstance(result, tuple):
            opportunities, option_chain = result
            # Save the complete option chain for AI analysis
            if option_chain and results:
                results.analyzed_option_chains[symbol] = option_chain
        else:
            # Backward compatibility if option chain not returned
            opportunities = result
            option_chain = None
        
        # Convert to PMCCCandidate objects
        candidates = []
        for opp in opportunities:
            try:
                # Create PMCCAnalysis
                analysis = PMCCAnalysis(
                    long_call=opp.leaps_contract,
                    short_call=opp.short_contract,
                    underlying=quote,
                    net_debit=opp.net_debit,
                    credit_received=opp.short_contract.bid,
                    analyzed_at=datetime.now()
                )
                
                # Calculate risk metrics
                analysis.risk_metrics = analysis.calculate_risk_metrics()
                analysis.liquidity_score = analysis.calculate_liquidity_score()
                
                # Create candidate
                candidate = PMCCCandidate(
                    symbol=symbol,
                    underlying_price=quote.last or quote.mid or Decimal('0'),
                    analysis=analysis,
                    liquidity_score=opp.liquidity_score,
                    total_score=opp.total_score,
                    complete_option_chain=option_chain,  # Include complete option chain for AI analysis
                    discovered_at=datetime.now()
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.warning(f"Error calculating metrics for {symbol}: {e}")
                continue
        
        # Sort by total score
        candidates.sort(key=lambda x: x.total_score or Decimal('0'), reverse=True)
        
        return candidates
    
    def _screen_stocks(self, config: ScanConfiguration, results: ScanResults) -> List[StockScreenResult]:
        """Screen stocks using provider factory with automatic failover."""
        
        try:
            if self.use_provider_factory:
                return self._screen_stocks_with_provider_factory(config, results)
            else:
                return self._screen_stocks_legacy(config, results)
                
        except Exception as e:
            error_msg = f"Error screening stocks: {e}"
            self.logger.error(error_msg)
            results.errors.append(error_msg)
            return []
    
    def _screen_stocks_with_provider_factory(self, config: ScanConfiguration, results: ScanResults) -> List[StockScreenResult]:
        """Screen stocks using provider factory."""
        import time
        
        # Check for custom symbols first
        if config.custom_symbols:
            print(f"\n🎯 Using custom symbols: {', '.join(config.custom_symbols)}")
            print("Skipping stock screening - validating custom symbols directly")
            self.logger.info(f"Using custom symbols: {config.custom_symbols}")
            screening_results = self._validate_custom_symbols(config.custom_symbols, results)
            results.stocks_screened = len(config.custom_symbols)
            print(f"✅ Validated {len(screening_results)} custom symbols")
            return screening_results
        
        # Use EODHD for screening (native screener API)
        screening_provider = self.provider_factory.get_provider(
            "screen_stocks", 
            preferred_provider=ProviderType.EODHD
        )
        
        if not screening_provider:
            raise ValueError("No provider available for stock screening")
        
        self.logger.info(f"Using {screening_provider.provider_type.value} for stock screening")
        self.logger.info(f"Provider class: {type(screening_provider).__name__}")
        self.logger.info(f"Config universe: {config.universe}, max_stocks_to_screen: {config.max_stocks_to_screen}")
        
        # Convert screening criteria to provider format
        # Note: ScreeningCriteria has market cap in millions, but ProviderScreeningCriteria expects USD
        provider_criteria = ProviderScreeningCriteria(
            min_market_cap=config.screening_criteria.min_market_cap * 1000000 if config.screening_criteria and config.screening_criteria.min_market_cap else None,
            max_market_cap=config.screening_criteria.max_market_cap * 1000000 if config.screening_criteria and config.screening_criteria.max_market_cap else None,
            min_price=config.screening_criteria.min_price if config.screening_criteria else None,
            max_price=config.screening_criteria.max_price if config.screening_criteria else None,
            min_volume=config.screening_criteria.min_daily_volume if config.screening_criteria else None,
            limit=config.max_stocks_to_screen,  # Pass the limit for pagination
            has_options=True,
            exclude_etfs=True
        )
        
        self.logger.info(f"Screening criteria: min_market_cap={provider_criteria.min_market_cap}, "
                        f"max_market_cap={provider_criteria.max_market_cap}, "
                        f"min_price={provider_criteria.min_price}, "
                        f"max_price={provider_criteria.max_price}, "
                        f"min_volume={provider_criteria.min_volume}")
        
        # Track operation start
        start_time = time.time()
        
        try:
            # Use provider's screening capability
            screen_response = screening_provider.screen_stocks(provider_criteria)
            
            if screen_response.is_success and screen_response.data:
                # Convert provider response to StockScreenResult format
                screening_results = self._convert_screening_response(screen_response.data)
                results.stocks_screened = len(screening_results)
                # Apply max stocks limit
                if len(screening_results) > config.max_stocks_to_screen:
                    screening_results = screening_results[:config.max_stocks_to_screen]
                    results.stocks_screened = config.max_stocks_to_screen
            else:
                self.logger.error(f"Screening failed: {screen_response.error}")
                return []
            
            # Track provider usage
            operation_time = (time.time() - start_time) * 1000
            self._track_provider_usage(
                screening_provider.provider_type, 
                "screen_stocks", 
                operation_time, 
                True, 
                credits_used=5  # EODHD screening typically uses 5 credits
            )
            
            results.stocks_passed_screening = len(screening_results)
            
            self.logger.info(
                f"Screened {results.stocks_screened} stocks using {screening_provider.provider_type.value}, "
                f"{results.stocks_passed_screening} passed criteria (took {operation_time:.1f}ms)"
            )
            
            return screening_results
            
        except Exception as e:
            # Track failed operation
            operation_time = (time.time() - start_time) * 1000
            self._track_provider_usage(
                screening_provider.provider_type, 
                "screen_stocks", 
                operation_time, 
                False
            )
            raise e
    
    def _screen_stocks_legacy(self, config: ScanConfiguration, results: ScanResults) -> List[StockScreenResult]:
        """Legacy stock screening method."""
        # Determine quote source for hybrid flow
        quote_source = "eodhd" if config.use_hybrid_flow else "marketdata"
        self.logger.info(f"Using legacy screening with {quote_source} for stock quotes/volume validation")
        
        if config.custom_symbols:
            # Use custom symbol list
            screening_results = self.stock_screener.screen_symbols(
                config.custom_symbols, config.screening_criteria, quote_source
            )
            results.stocks_screened = len(config.custom_symbols)
        else:
            # Get initial symbols from universe
            self.logger.info(f"Getting universe symbols with max_stocks_to_screen={config.max_stocks_to_screen}")
            initial_symbols = self.stock_screener._get_universe_symbols(
                config.universe, 
                config.screening_criteria,
                config.max_stocks_to_screen
            )
            self.logger.info(f"Initial universe '{config.universe}' returned {len(initial_symbols)} symbols")
            
            # Now screen those symbols
            screening_results = self.stock_screener.screen_symbols(
                initial_symbols[:config.max_stocks_to_screen], config.screening_criteria, quote_source
            )
            results.stocks_screened = min(len(initial_symbols), config.max_stocks_to_screen)
        
        results.stocks_passed_screening = len(screening_results)
        
        self.logger.info(
            f"Screened {results.stocks_screened} stocks, "
            f"{results.stocks_passed_screening} passed criteria"
        )
        
        return screening_results
    
    def _analyze_options(self, screening_results: List[StockScreenResult],
                        config: ScanConfiguration, results: ScanResults) -> List[PMCCOpportunity]:
        """Analyze options for screened stocks with provider tracking and progress updates."""
        
        all_opportunities = []
        total_stocks = len(screening_results)
        
        # Log the complete list of stocks to be analyzed
        print(f"\n📦 Storing {total_stocks} stocks for options analysis")
        stock_symbols = [stock.symbol for stock in screening_results]
        print(f"Stock list preview: {', '.join(stock_symbols[:10])}{'...' if len(stock_symbols) > 10 else ''}")
        print("-" * 60)
        self.logger.info(f"Storing {total_stocks} stocks for options analysis")
        
        # Process stocks one at a time with progress tracking
        for idx, stock_result in enumerate(screening_results, 1):
            try:
                symbol = stock_result.symbol
                progress_pct = (idx / total_stocks) * 100
                print(f"\n[{idx}/{total_stocks}] ({progress_pct:.1f}%) 🔍 Getting option chain for {symbol}...")
                self.logger.debug(f"Analyzing options for {symbol}")
                
                # Track which provider will be used for options analysis
                if self.use_provider_factory and hasattr(self.options_analyzer, 'data_provider'):
                    provider_type = getattr(self.options_analyzer.data_provider, 'provider_type', 'unknown')
                    self.current_operation_routing['get_options_chain'].append((symbol, provider_type, True))
                
                # Find PMCC opportunities and get complete option chain
                result = self.options_analyzer.find_pmcc_opportunities(
                    symbol, config.leaps_criteria, config.short_criteria,
                    return_option_chain=True
                )
                if isinstance(result, tuple):
                    opportunities, option_chain = result
                    # Save the complete option chain for AI analysis
                    if option_chain:
                        results.analyzed_option_chains[symbol] = option_chain
                else:
                    # Backward compatibility if option chain not returned
                    opportunities = result
                
                if opportunities:
                    all_opportunities.extend(opportunities)
                    print(f"   ✅ Found {len(opportunities)} PMCC opportunities for {symbol}")
                    self.logger.info(f"Found {len(opportunities)} PMCC opportunities for {symbol}")
                else:
                    print(f"   ❌ No PMCC opportunities found for {symbol}")
                    self.logger.debug(f"No PMCC opportunities found for {symbol}")
                
                results.options_analyzed += 1
                
                # Track successful options analysis
                if self.use_provider_factory and hasattr(self.options_analyzer, 'data_provider'):
                    provider_type = getattr(self.options_analyzer.data_provider, 'provider_type', 'unknown')
                    if isinstance(provider_type, ProviderType):
                        self._track_provider_usage(
                            provider_type, 
                            "get_options_chain", 
                            0,  # Latency tracked within analyzer
                            True, 
                            credits_used=1
                        )
                
                # Progress update every 10 stocks or at milestones
                if idx % 10 == 0 or idx in [25, 50, 100, 200, 500]:
                    print("-" * 60)
                    print(
                        f"📊 Progress Update: {idx}/{total_stocks} stocks analyzed, "
                        f"{len(all_opportunities)} total opportunities found so far"
                    )
                    print("-" * 60)
                
            except Exception as e:
                error_type = type(e).__name__
                warning_msg = f"Error analyzing options for {stock_result.symbol}: {error_type}: {e}"
                self.logger.warning(warning_msg)
                results.warnings.append(warning_msg)
                
                # Track failed options analysis
                if self.use_provider_factory and hasattr(self.options_analyzer, 'data_provider'):
                    provider_type = getattr(self.options_analyzer.data_provider, 'provider_type', 'unknown')
                    if isinstance(provider_type, ProviderType):
                        self.current_operation_routing['get_options_chain'].append((stock_result.symbol, provider_type, False))
                        self._track_provider_usage(
                            provider_type, 
                            "get_options_chain", 
                            0, 
                            False
                        )
                
                # Implement recovery strategies based on error type
                if "rate limit" in str(e).lower():
                    self.logger.warning(f"Rate limit hit at stock {idx}/{total_stocks}. Consider implementing backoff.")
                    # Could add a small delay here if needed
                    # await asyncio.sleep(1.0)
                elif "timeout" in str(e).lower():
                    self.logger.warning(f"Timeout for {symbol}. Network may be slow.")
                elif "404" in str(e) or "not found" in str(e).lower():
                    self.logger.debug(f"Options data not available for {symbol}")
                else:
                    self.logger.debug(f"Unexpected error for {symbol}: {e}")
                
                # Continue processing remaining stocks
                continue
        
        # Final summary
        print("\n" + "=" * 60)
        print("🏁 Options Analysis Complete!")
        print("=" * 60)
        print(f"  📊 Total stocks analyzed: {results.options_analyzed}/{total_stocks}")
        print(f"  ✅ Successful analyses: {results.options_analyzed - len([w for w in results.warnings if 'Error analyzing options' in w])}")
        print(f"  ❌ Failed analyses: {len([w for w in results.warnings if 'Error analyzing options' in w])}")
        print(f"  🎯 Total opportunities found: {len(all_opportunities)}")
        print("=" * 60)
        self.logger.info(f"Found {len(all_opportunities)} total opportunities")
        
        # Export complete option chain data for all symbols with PMCC opportunities
        if results.analyzed_option_chains:
            try:
                print("\n📁 Exporting complete option chain data...")
                option_chains_file = self.export_complete_option_chains(results)
                results.warnings.append(f"Complete option chains exported: {option_chains_file}")
            except Exception as e:
                self.logger.warning(f"Failed to export complete option chains: {e}")
                results.warnings.append(f"Failed to export complete option chains: {e}")
        
        return all_opportunities
    
    def _calculate_risk_metrics(self, opportunities: List[PMCCOpportunity],
                               config: ScanConfiguration, results: ScanResults) -> List[PMCCCandidate]:
        """Calculate comprehensive risk metrics for opportunities."""
        
        candidates = []
        
        for opp in opportunities:
            try:
                # Create PMCCAnalysis object
                analysis = PMCCAnalysis(
                    long_call=opp.leaps_contract,
                    short_call=opp.short_contract,
                    underlying=opp.underlying_quote,
                    net_debit=opp.net_debit,
                    credit_received=opp.short_contract.bid,
                    analyzed_at=datetime.now()
                )
                
                # Calculate basic risk metrics
                analysis.risk_metrics = RiskMetrics(
                    max_loss=opp.max_loss,
                    max_profit=opp.max_profit,
                    breakeven=opp.breakeven,
                    probability_of_profit=opp.probability_score,
                    net_delta=None,  # Would be calculated from Greeks
                    net_gamma=None,
                    net_theta=None,
                    net_vega=None,
                    risk_reward_ratio=opp.risk_reward_ratio
                )
                
                analysis.liquidity_score = opp.liquidity_score
                
                # Calculate comprehensive risk if requested
                if config.perform_scenario_analysis:
                    try:
                        comprehensive_risk = self.risk_calculator.calculate_comprehensive_risk(
                            analysis, config.account_size, config.risk_free_rate
                        )
                        # Store additional risk metrics (could extend PMCCAnalysis)
                    except Exception as e:
                        self.logger.warning(f"Error calculating comprehensive risk: {e}")
                
                # Create candidate
                candidate = PMCCCandidate(
                    symbol=opp.underlying_quote.symbol,
                    underlying_price=opp.underlying_quote.last or opp.underlying_quote.mid or Decimal('0'),
                    analysis=analysis,
                    liquidity_score=opp.liquidity_score,
                    total_score=opp.total_score,
                    discovered_at=datetime.now()
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                warning_msg = f"Error calculating risk for opportunity: {e}"
                self.logger.warning(warning_msg)
                results.warnings.append(warning_msg)
                continue
        
        return candidates
    
    def _rank_and_filter(self, candidates: List[PMCCCandidate],
                        config: ScanConfiguration) -> List[PMCCCandidate]:
        """Rank candidates and filter by minimum score, keeping only best per symbol."""
        
        # Filter by minimum score
        filtered = [
            c for c in candidates 
            if c.total_score and c.total_score >= config.min_total_score
        ]
        
        # Sort by total score (highest first)
        filtered.sort(key=lambda x: x.total_score or Decimal('0'), reverse=True)
        
        # Keep only the best opportunity per symbol if configured
        if config.best_per_symbol_only:
            best_per_symbol = {}
            for candidate in filtered:
                if candidate.symbol not in best_per_symbol:
                    best_per_symbol[candidate.symbol] = candidate
            
            # Get the filtered list and re-sort by score
            unique_filtered = list(best_per_symbol.values())
            unique_filtered.sort(key=lambda x: x.total_score or Decimal('0'), reverse=True)
            
            # Log how many opportunities were filtered out
            duplicates_removed = len(filtered) - len(unique_filtered)
            if duplicates_removed > 0:
                self.logger.info(f"Filtered out {duplicates_removed} duplicate opportunities (keeping best per symbol)")
                print(f"\n🎯 Filtered to best opportunity per stock: {len(unique_filtered)} unique stocks (removed {duplicates_removed} duplicates)")
            
            filtered = unique_filtered
        
        # Add ranking
        for i, candidate in enumerate(filtered):
            candidate.rank = i + 1
        
        # Return top N opportunities
        return filtered[:config.max_opportunities]
    
    def export_results(self, results: ScanResults, format: str = "json", 
                      filename: Optional[str] = None, output_dir: str = "data") -> str:
        """
        Export scan results to file with historical preservation.
        
        Args:
            results: Scan results to export
            format: Export format ("json", "csv")
            filename: Optional filename (auto-generated if None)
            output_dir: Directory to save files (default: "data")
            
        Returns:
            Path to exported file
        """
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pmcc_scan_{timestamp}.{format}"
        
        # Full path to output file
        filepath = os.path.join(output_dir, filename)
        
        try:
            if format.lower() == "json":
                with open(filepath, 'w') as f:
                    json.dump(results.to_dict(), f, indent=2, default=str)
            
            elif format.lower() == "csv":
                self._export_to_csv(results, filepath)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Results exported to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            raise
    
    def export_complete_option_chains(self, results: ScanResults, output_dir: str = "data") -> str:
        """
        Export complete option chain data for all identified PMCC opportunities.
        
        This saves the raw option chain data before any filtering or scoring is applied,
        capturing all contract details for identified PMCC opportunities.
        
        Args:
            results: Scan results containing option chain data
            output_dir: Directory to save the file (default: "data")
            
        Returns:
            Path to exported option chains file
        """
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"option_chains_complete_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Build complete option chain data dictionary
        complete_data = {
            'scan_metadata': {
                'scan_id': results.scan_id,
                'timestamp': timestamp,
                'exported_at': datetime.now().isoformat(),
                'symbols_with_pmcc_opportunities': list(results.analyzed_option_chains.keys()),
                'total_symbols': len(results.analyzed_option_chains),
                'note': 'Raw option chain data for all identified PMCC opportunities before filtering'
            },
            'option_chains': {}
        }
        
        try:
            # Export complete option chain data for each symbol
            for symbol, option_chain in results.analyzed_option_chains.items():
                if option_chain and option_chain.contracts:
                    complete_data['option_chains'][symbol] = {
                        'underlying': option_chain.underlying,
                        'underlying_price': float(option_chain.underlying_price) if option_chain.underlying_price else None,
                        'updated': option_chain.updated.isoformat() if option_chain.updated else None,
                        'total_contracts': len(option_chain.contracts),
                        'contracts': []
                    }
                    
                    # Export all contract details
                    for contract in option_chain.contracts:
                        contract_data = {
                            'option_symbol': contract.option_symbol,
                            'underlying': contract.underlying,
                            'expiration': contract.expiration.isoformat() if contract.expiration else None,
                            'strike': float(contract.strike) if contract.strike else None,
                            'side': contract.side.value if contract.side else None,
                            'bid': float(contract.bid) if contract.bid else None,
                            'ask': float(contract.ask) if contract.ask else None,
                            'last': float(contract.last) if contract.last else None,
                            'volume': contract.volume,
                            'open_interest': contract.open_interest,
                            'is_leaps': contract.is_leaps,
                            'days_to_expiration': contract.dte,
                            'mid_price': float(contract.mid) if contract.mid else None,
                            'bid_ask_spread': float(contract.spread) if contract.spread else None,
                            'spread_percentage': float(contract.spread_percentage) if contract.spread_percentage else None,
                            # Greeks data
                            'delta': float(contract.delta) if contract.delta else None,
                            'gamma': float(contract.gamma) if contract.gamma else None,
                            'theta': float(contract.theta) if contract.theta else None,
                            'vega': float(contract.vega) if contract.vega else None,
                            'iv': float(contract.iv) if contract.iv else None,
                            # Additional metadata
                            'updated': contract.updated.isoformat() if contract.updated else None
                        }
                        complete_data['option_chains'][symbol]['contracts'].append(contract_data)
                    
                    # Sort contracts by expiration and strike for easier analysis
                    complete_data['option_chains'][symbol]['contracts'].sort(
                        key=lambda x: (x['expiration'] or '', x['strike'] or 0, x['side'] or '')
                    )
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(complete_data, f, indent=2, default=str)
            
            self.logger.info(f"Complete option chains exported to {filepath}")
            self.logger.info(f"Exported {len(complete_data['option_chains'])} symbols with option chains")
            
            # Print summary
            total_contracts = sum(len(chain['contracts']) for chain in complete_data['option_chains'].values())
            print(f"   📊 Complete option chains saved: {filepath}")
            print(f"   📈 Total symbols: {len(complete_data['option_chains'])}")
            print(f"   📋 Total contracts: {total_contracts}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting complete option chains: {e}")
            raise
    
    def _export_to_csv(self, results: ScanResults, filepath: str) -> None:
        """
        Export scan results to comprehensive CSV format with historical preservation.
        
        Args:
            results: Scan results to export
            filepath: Full path to output CSV file
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # Define comprehensive CSV schema
            fieldnames = [
                # Scan metadata
                'scan_timestamp',
                'scan_id', 
                'scan_duration_seconds',
                'total_stocks_screened',
                'stocks_passed_screening',
                'total_opportunities_found',
                'success_rate',
                'opportunity_rate',
                
                # Opportunity ranking
                'rank',
                'symbol',
                'underlying_price',
                'total_score',
                'liquidity_score',
                'volatility_score',
                'technical_score',
                'fundamental_score',
                
                # LEAPS (Long Call) details
                'long_option_symbol',
                'long_strike',
                'long_expiration',
                'long_dte',
                'long_bid',
                'long_ask',
                'long_mid',
                'long_delta',
                'long_gamma',
                'long_theta',
                'long_vega',
                'long_implied_volatility',
                'long_volume',
                'long_open_interest',
                
                # Short Call details
                'short_option_symbol',
                'short_strike',
                'short_expiration',
                'short_dte',
                'short_bid',
                'short_ask',
                'short_mid',
                'short_delta',
                'short_gamma',
                'short_theta',
                'short_vega',
                'short_implied_volatility',
                'short_volume',
                'short_open_interest',
                
                # PMCC Position metrics
                'net_debit',
                'credit_received',
                'max_profit',
                'max_loss',
                'breakeven',
                'risk_reward_ratio',
                'strike_width',
                'net_delta',
                'net_gamma',
                'net_theta',
                'net_vega',
                
                # Risk and probability metrics
                'probability_of_profit',
                'capital_at_risk_pct',
                'iv_rank',
                
                # Position validation
                'is_valid_pmcc',
                'is_profitable',
                'days_to_short_expiration',
                'days_to_long_expiration',
                
                # Discovery metadata
                'discovered_at',
                'analyzed_at',
                
                # Provider information
                'screening_provider',
                'quote_provider', 
                'options_provider',
                'provider_success_rates',
                'total_provider_latency_ms',
                'total_credits_used'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # If no opportunities found, write a row with scan metadata only
            if not results.top_opportunities:
                scan_row = self._create_scan_metadata_row(results)
                writer.writerow(scan_row)
                return
            
            # Write rows for each opportunity
            for opportunity in results.top_opportunities:
                row = self._create_opportunity_csv_row(results, opportunity)
                writer.writerow(row)
    
    def _create_scan_metadata_row(self, results: ScanResults) -> Dict[str, Any]:
        """Create CSV row with scan metadata only (for scans with no opportunities)."""
        return {
            'scan_timestamp': results.started_at.isoformat() if results.started_at else None,
            'scan_id': results.scan_id,
            'scan_duration_seconds': results.total_duration_seconds,
            'total_stocks_screened': results.stocks_screened,
            'stocks_passed_screening': results.stocks_passed_screening,
            'total_opportunities_found': results.opportunities_found,
            'success_rate': round(results.success_rate, 4) if results.success_rate else None,
            'opportunity_rate': round(results.opportunity_rate, 4) if results.opportunity_rate else None,
            
            # All other fields will be None/empty for metadata-only rows
            'rank': None,
            'symbol': None,
            # ... (all other fields default to None)
        }
    
    def _create_opportunity_csv_row(self, results: ScanResults, opportunity: "PMCCCandidate") -> Dict[str, Any]:
        """Create comprehensive CSV row for a PMCC opportunity."""
        analysis = opportunity.analysis
        long_call = analysis.long_call
        short_call = analysis.short_call
        risk_metrics = analysis.risk_metrics
        
        # Helper function to safely convert Decimal to float
        def safe_float(value) -> Optional[float]:
            if value is None:
                return None
            if isinstance(value, Decimal):
                return float(value)
            return float(value) if value is not None else None
        
        # Helper function to safely get mid price
        def get_mid_price(contract) -> Optional[float]:
            if contract.bid is not None and contract.ask is not None:
                return safe_float((contract.bid + contract.ask) / 2)
            return None
        
        row = {
            # Scan metadata (repeated for each row for data analysis)
            'scan_timestamp': results.started_at.isoformat() if results.started_at else None,
            'scan_id': results.scan_id,
            'scan_duration_seconds': results.total_duration_seconds,
            'total_stocks_screened': results.stocks_screened,
            'stocks_passed_screening': results.stocks_passed_screening,
            'total_opportunities_found': results.opportunities_found,
            'success_rate': round(results.success_rate, 4) if results.success_rate else None,
            'opportunity_rate': round(results.opportunity_rate, 4) if results.opportunity_rate else None,
            
            # Opportunity ranking
            'rank': opportunity.rank,
            'symbol': opportunity.symbol,
            'underlying_price': safe_float(opportunity.underlying_price),
            'total_score': safe_float(opportunity.total_score),
            'liquidity_score': safe_float(opportunity.liquidity_score),
            'volatility_score': safe_float(opportunity.volatility_score),
            'technical_score': safe_float(opportunity.technical_score),
            'fundamental_score': safe_float(opportunity.fundamental_score),
            
            # LEAPS (Long Call) details
            'long_option_symbol': long_call.option_symbol,
            'long_strike': safe_float(long_call.strike),
            'long_expiration': long_call.expiration.isoformat() if long_call.expiration else None,
            'long_dte': long_call.dte,
            'long_bid': safe_float(long_call.bid),
            'long_ask': safe_float(long_call.ask),
            'long_mid': get_mid_price(long_call),
            'long_delta': safe_float(long_call.delta),
            'long_gamma': safe_float(long_call.gamma),
            'long_theta': safe_float(long_call.theta),
            'long_vega': safe_float(long_call.vega),
            'long_implied_volatility': safe_float(long_call.iv),
            'long_volume': long_call.volume,
            'long_open_interest': long_call.open_interest,
            
            # Short Call details
            'short_option_symbol': short_call.option_symbol,
            'short_strike': safe_float(short_call.strike),
            'short_expiration': short_call.expiration.isoformat() if short_call.expiration else None,
            'short_dte': short_call.dte,
            'short_bid': safe_float(short_call.bid),
            'short_ask': safe_float(short_call.ask),
            'short_mid': get_mid_price(short_call),
            'short_delta': safe_float(short_call.delta),
            'short_gamma': safe_float(short_call.gamma),
            'short_theta': safe_float(short_call.theta),
            'short_vega': safe_float(short_call.vega),
            'short_implied_volatility': safe_float(short_call.iv),
            'short_volume': short_call.volume,
            'short_open_interest': short_call.open_interest,
            
            # PMCC Position metrics
            'net_debit': safe_float(analysis.net_debit),
            'credit_received': safe_float(analysis.credit_received),
            'max_profit': safe_float(risk_metrics.max_profit) if risk_metrics else None,
            'max_loss': safe_float(risk_metrics.max_loss) if risk_metrics else None,
            'breakeven': safe_float(risk_metrics.breakeven) if risk_metrics else None,
            'risk_reward_ratio': safe_float(risk_metrics.risk_reward_ratio) if risk_metrics else None,
            'strike_width': safe_float(analysis.strike_width),
            'net_delta': safe_float(risk_metrics.net_delta) if risk_metrics else None,
            'net_gamma': safe_float(risk_metrics.net_gamma) if risk_metrics else None,
            'net_theta': safe_float(risk_metrics.net_theta) if risk_metrics else None,
            'net_vega': safe_float(risk_metrics.net_vega) if risk_metrics else None,
            
            # Risk and probability metrics
            'probability_of_profit': safe_float(risk_metrics.probability_of_profit) if risk_metrics else None,
            'capital_at_risk_pct': safe_float(risk_metrics.capital_at_risk) if risk_metrics else None,
            'iv_rank': safe_float(analysis.iv_rank),
            
            # Position validation
            'is_valid_pmcc': analysis.is_valid_pmcc,
            'is_profitable': opportunity.is_profitable,
            'days_to_short_expiration': analysis.days_to_short_expiration,
            'days_to_long_expiration': analysis.days_to_long_expiration,
            
            # Discovery metadata
            'discovered_at': opportunity.discovered_at.isoformat() if opportunity.discovered_at else None,
            'analyzed_at': analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
            
            # Provider information
            'screening_provider': self._get_operation_provider(results, 'screen_stocks', opportunity.symbol),
            'quote_provider': self._get_operation_provider(results, 'get_stock_quote', opportunity.symbol),
            'options_provider': self._get_operation_provider(results, 'get_options_chain', opportunity.symbol),
            'provider_success_rates': self._get_provider_success_rates_summary(results),
            'total_provider_latency_ms': sum(stats.total_latency_ms for stats in results.provider_usage.values()) if results.provider_usage else None,
            'total_credits_used': sum(stats.credits_used for stats in results.provider_usage.values()) if results.provider_usage else None
        }
        
        return row
    
    def export_historical_csv(self, results: ScanResults, include_sub_scores: bool = True,
                             output_dir: str = "data") -> str:
        """
        Export comprehensive CSV with detailed scoring breakdown for historical analysis.
        
        Args:
            results: Scan results to export
            include_sub_scores: Include detailed sub-score breakdowns
            output_dir: Directory to save files
            
        Returns:
            Path to exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pmcc_scan_detailed_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True)
        
        # Extended fieldnames for detailed analysis - start with basic CSV fields
        # Get basic fieldnames from _export_to_csv method
        basic_fieldnames = [
            # Scan metadata
            'scan_timestamp',
            'scan_id', 
            'scan_duration_seconds',
            'total_stocks_screened',
            'stocks_passed_screening',
            'total_opportunities_found',
            'success_rate',
            'opportunity_rate',
            
            # Opportunity ranking
            'rank',
            'symbol',
            'underlying_price',
            'total_score',
            'liquidity_score',
            'volatility_score',
            'technical_score',
            'fundamental_score',
            
            # LEAPS (Long Call) details
            'long_option_symbol',
            'long_strike',
            'long_expiration',
            'long_dte',
            'long_bid',
            'long_ask',
            'long_mid',
            'long_delta',
            'long_gamma',
            'long_theta',
            'long_vega',
            'long_implied_volatility',
            'long_volume',
            'long_open_interest',
            
            # Short Call details
            'short_option_symbol',
            'short_strike',
            'short_expiration',
            'short_dte',
            'short_bid',
            'short_ask',
            'short_mid',
            'short_delta',
            'short_gamma',
            'short_theta',
            'short_vega',
            'short_implied_volatility',
            'short_volume',
            'short_open_interest',
            
            # PMCC Position metrics
            'net_debit',
            'credit_received',
            'max_profit',
            'max_loss',
            'breakeven',
            'risk_reward_ratio',
            'strike_width',
            'net_delta',
            'net_gamma',
            'net_theta',
            'net_vega',
            
            # Risk and probability metrics
            'probability_of_profit',
            'capital_at_risk_pct',
            'iv_rank',
            
            # Position validation
            'is_valid_pmcc',
            'is_profitable',
            'days_to_short_expiration',
            'days_to_long_expiration',
            
            # Discovery metadata
            'discovered_at',
            'analyzed_at'
        ]
        
        extended_fieldnames = basic_fieldnames.copy()
        
        if include_sub_scores:
            extended_fieldnames.extend([
                # Detailed PMCC scoring components
                'setup_quality_score',    # How well the PMCC is structured
                'profit_potential_score', # Expected profit potential
                'risk_management_score',  # Risk characteristics
                'market_timing_score',    # Current market conditions
                'execution_difficulty_score', # How easy to execute/manage
            ])
        
        extended_fieldnames.extend([
            # Position structure
            'long_strike', 'long_expiration', 'long_dte', 'long_delta',
            'short_strike', 'short_expiration', 'short_dte', 'short_delta',
            'strike_width', 'dte_spread',
            
            # Economics
            'net_debit', 'max_profit', 'max_loss', 'breakeven',
            'risk_reward_ratio', 'profit_margin_pct',
            
            # Greeks analysis
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'position_leverage', 'gamma_exposure',
            
            # Liquidity and execution
            'long_bid_ask_spread_pct', 'short_bid_ask_spread_pct',
            'combined_volume', 'combined_open_interest',
            
            # Risk factors
            'early_assignment_risk', 'dividend_risk', 'earnings_risk',
            'time_decay_risk', 'volatility_risk',
            
            # Market context
            'underlying_iv_rank', 'sector_performance', 'market_regime',
            
            # Metadata
            'discovered_at', 'analyzed_at',
            
            # Provider tracking
            'screening_provider', 'quote_provider', 'options_provider',
            'provider_success_rates', 'total_provider_latency_ms', 'total_credits_used'
        ])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=extended_fieldnames)
            writer.writeheader()
            
            if not results.top_opportunities:
                # Write metadata-only row
                scan_row = {field: None for field in extended_fieldnames}
                scan_row.update(self._create_scan_metadata_row(results))
                writer.writerow(scan_row)
                return filepath
            
            # Write detailed rows for each opportunity
            for opportunity in results.top_opportunities:
                row = self._create_detailed_csv_row(results, opportunity, include_sub_scores)
                writer.writerow(row)
        
        self.logger.info(f"Detailed historical CSV exported to {filepath}")
        return filepath
    
    def _create_detailed_csv_row(self, results: ScanResults, opportunity: "PMCCCandidate",
                                include_sub_scores: bool) -> Dict[str, Any]:
        """Create detailed CSV row with comprehensive analysis metrics."""
        # Start with basic opportunity row
        row = self._create_opportunity_csv_row(results, opportunity)
        
        # Add detailed analysis fields
        analysis = opportunity.analysis
        long_call = analysis.long_call
        short_call = analysis.short_call
        
        def safe_float(value) -> Optional[float]:
            if value is None:
                return None
            if isinstance(value, Decimal):
                return float(value)
            return float(value) if value is not None else None
        
        # Additional calculated fields for historical analysis
        additional_fields = {
            # Position structure metrics
            'dte_spread': (long_call.dte or 0) - (short_call.dte or 0),
            'profit_margin_pct': safe_float((analysis.risk_metrics.max_profit / analysis.net_debit * 100) 
                                          if analysis.risk_metrics and analysis.risk_metrics.max_profit 
                                          and analysis.net_debit > 0 else None),
            
            # Enhanced liquidity metrics
            'long_bid_ask_spread_pct': safe_float(
                ((long_call.ask - long_call.bid) / ((long_call.ask + long_call.bid) / 2) * 100)
                if long_call.bid and long_call.ask and (long_call.bid + long_call.ask) > 0 else None
            ),
            'short_bid_ask_spread_pct': safe_float(
                ((short_call.ask - short_call.bid) / ((short_call.ask + short_call.bid) / 2) * 100)
                if short_call.bid and short_call.ask and (short_call.bid + short_call.ask) > 0 else None
            ),
            'combined_volume': (long_call.volume or 0) + (short_call.volume or 0),
            'combined_open_interest': (long_call.open_interest or 0) + (short_call.open_interest or 0),
            
            # Risk assessment flags
            'early_assignment_risk': 'LOW',  # Could be calculated based on ITM amount and time
            'dividend_risk': 'UNKNOWN',      # Would need dividend calendar data
            'earnings_risk': 'UNKNOWN',      # Would need earnings calendar data
            'time_decay_risk': 'MODERATE' if (short_call.dte or 0) < 30 else 'LOW',
            'volatility_risk': 'MODERATE',   # Could be based on IV levels
            
            # Position characteristics
            'position_leverage': safe_float(opportunity.underlying_price / analysis.net_debit) if analysis.net_debit > 0 else None,
            'gamma_exposure': safe_float(analysis.risk_metrics.net_gamma) if analysis.risk_metrics else None,
            
            # Market context (placeholders for future enhancement)
            'underlying_iv_rank': safe_float(analysis.iv_rank),
            'sector_performance': 'UNKNOWN',  # Would need sector data
            'market_regime': 'UNKNOWN',       # Would need market analysis
        }
        
        if include_sub_scores:
            # Calculate detailed sub-scores (simplified for demonstration)
            setup_score = self._calculate_setup_quality_score(opportunity)
            profit_score = self._calculate_profit_potential_score(opportunity)
            risk_score = self._calculate_risk_management_score(opportunity)
            
            additional_fields.update({
                'setup_quality_score': safe_float(setup_score),
                'profit_potential_score': safe_float(profit_score),
                'risk_management_score': safe_float(risk_score),
                'market_timing_score': safe_float(Decimal('50')),  # Placeholder
                'execution_difficulty_score': safe_float(opportunity.liquidity_score),
            })
        
        # Add provider tracking information
        additional_fields.update({
            'screening_provider': self._get_operation_provider(results, 'screen_stocks', opportunity.symbol),
            'quote_provider': self._get_operation_provider(results, 'get_stock_quote', opportunity.symbol), 
            'options_provider': self._get_operation_provider(results, 'get_options_chain', opportunity.symbol),
            'provider_success_rates': self._get_provider_success_rates_summary(results),
            'total_provider_latency_ms': sum(stats.total_latency_ms for stats in results.provider_usage.values()) if results.provider_usage else None,
            'total_credits_used': sum(stats.credits_used for stats in results.provider_usage.values()) if results.provider_usage else None
        })
        
        # Merge additional fields into the row
        row.update(additional_fields)
        
        return row
    
    def _get_operation_provider(self, results: ScanResults, operation: str, symbol: str) -> Optional[str]:
        """Get the provider used for a specific operation on a symbol."""
        if not results.operation_routing or operation not in results.operation_routing:
            return None
        
        for op_symbol, provider_type, success in results.operation_routing[operation]:
            if op_symbol == symbol:
                return provider_type.value if hasattr(provider_type, 'value') else str(provider_type)
        
        return None
    
    def _get_provider_success_rates_summary(self, results: ScanResults) -> str:
        """Get a summary string of provider success rates."""
        if not results.provider_usage:
            return "N/A"
        
        rates = []
        for provider_type, stats in results.provider_usage.items():
            rate_str = f"{provider_type.value}:{stats.success_rate:.1%}"
            rates.append(rate_str)
        
        return "; ".join(rates)
    
    def _calculate_setup_quality_score(self, opportunity: "PMCCCandidate") -> Decimal:
        """Calculate how well the PMCC position is structured."""
        score = Decimal('0')
        factors = 0
        
        analysis = opportunity.analysis
        
        # Delta spread appropriateness (target: long delta 0.7-0.9, short delta 0.15-0.4)
        if analysis.long_call.delta and analysis.short_call.delta:
            long_delta = analysis.long_call.delta
            short_delta = analysis.short_call.delta
            
            if Decimal('0.7') <= long_delta <= Decimal('0.9'):
                score += Decimal('30')
            elif Decimal('0.6') <= long_delta <= Decimal('0.95'):
                score += Decimal('20')
            else:
                score += Decimal('10')
            
            if Decimal('0.15') <= short_delta <= Decimal('0.4'):
                score += Decimal('25')
            elif Decimal('0.1') <= short_delta <= Decimal('0.5'):
                score += Decimal('15')
            else:
                score += Decimal('5')
            
            factors += 1
        
        # Time spread appropriateness (LEAPS should be 6+ months, short should be 30-60 days)
        if analysis.long_call.dte and analysis.short_call.dte:
            long_dte = analysis.long_call.dte
            short_dte = analysis.short_call.dte
            
            if long_dte >= 180:  # 6+ months
                score += Decimal('25')
            elif long_dte >= 120:  # 4+ months
                score += Decimal('15')
            else:
                score += Decimal('5')
            
            if 30 <= short_dte <= 60:  # Ideal short-term range
                score += Decimal('20')
            elif 20 <= short_dte <= 75:  # Acceptable range
                score += Decimal('10')
            else:
                score += Decimal('0')
            
            factors += 1
        
        if factors > 0:
            return score / factors
        return Decimal('50')  # Default neutral score
    
    def _calculate_profit_potential_score(self, opportunity: "PMCCCandidate") -> Decimal:
        """Calculate the profit potential of the PMCC position."""
        if not opportunity.analysis.risk_metrics:
            return Decimal('50')
        
        risk_metrics = opportunity.analysis.risk_metrics
        
        # Risk/reward ratio scoring
        if risk_metrics.risk_reward_ratio:
            ratio = risk_metrics.risk_reward_ratio
            if ratio >= Decimal('2.0'):
                return Decimal('90')
            elif ratio >= Decimal('1.5'):
                return Decimal('80')
            elif ratio >= Decimal('1.2'):
                return Decimal('70')
            elif ratio >= Decimal('1.0'):
                return Decimal('60')
            elif ratio >= Decimal('0.8'):
                return Decimal('50')
            else:
                return Decimal('30')
        
        return Decimal('50')
    
    def _calculate_risk_management_score(self, opportunity: "PMCCCandidate") -> Decimal:
        """Calculate risk management characteristics of the position."""
        score = Decimal('50')  # Start with neutral
        
        analysis = opportunity.analysis
        
        # Position size relative to account (if available)
        if analysis.risk_metrics and analysis.risk_metrics.capital_at_risk:
            risk_pct = analysis.risk_metrics.capital_at_risk
            if risk_pct <= Decimal('2'):  # 2% or less
                score += Decimal('20')
            elif risk_pct <= Decimal('5'):  # 5% or less
                score += Decimal('10')
            elif risk_pct > Decimal('10'):  # More than 10%
                score -= Decimal('20')
        
        # Time decay characteristics
        if analysis.risk_metrics and analysis.risk_metrics.net_theta:
            net_theta = analysis.risk_metrics.net_theta
            if net_theta > 0:  # Positive theta (time decay working for us)
                score += Decimal('15')
            elif net_theta < Decimal('-0.05'):  # Highly negative theta
                score -= Decimal('15')
        
        return max(Decimal('0'), min(Decimal('100'), score))
    
    # Provider abstraction helper methods
    
    def _track_provider_usage(self, provider_type: ProviderType, operation: str, 
                             latency_ms: float, success: bool, credits_used: int = 0):
        """Track provider usage statistics."""
        if provider_type not in self.current_scan_usage:
            self.current_scan_usage[provider_type] = ProviderUsageStats(provider_type)
        
        stats = self.current_scan_usage[provider_type]
        stats.operations_count += 1
        stats.total_latency_ms += latency_ms
        stats.credits_used += credits_used
        
        if success:
            stats.success_count += 1
        else:
            stats.error_count += 1
    
    def _validate_custom_symbols(self, symbols: List[str], results: ScanResults) -> List[StockScreenResult]:
        """Validate custom symbols using available providers."""
        validated_results = []
        
        # Get quote provider (prefer MarketData for real-time quotes)
        quote_provider = None
        if self.use_provider_factory:
            quote_provider = self.provider_factory.get_provider(
                "get_stock_quote",
                preferred_provider=ProviderType.MARKETDATA
            )
        
        for symbol in symbols:
            try:
                if quote_provider:
                    import time
                    start_time = time.time()
                    
                    quote_response = quote_provider.get_stock_quote(symbol)
                    operation_time = (time.time() - start_time) * 1000
                    
                    if quote_response.is_success and quote_response.data:
                        # Create StockScreenResult from quote
                        validated_results.append(StockScreenResult(
                            symbol=symbol,
                            quote=quote_response.data,
                            market_cap=None,  # Not available in quote
                            screening_score=Decimal('100')  # Custom symbols automatically pass
                        ))
                        
                        # Track successful quote fetch
                        self.current_operation_routing['get_stock_quote'].append((symbol, quote_provider.provider_type, True))
                        self._track_provider_usage(
                            quote_provider.provider_type,
                            "get_stock_quote",
                            operation_time,
                            True,
                            credits_used=1
                        )
                    else:
                        self.logger.warning(f"Could not validate symbol {symbol}: {quote_response.error}")
                        self.current_operation_routing['get_stock_quote'].append((symbol, quote_provider.provider_type, False))
                        self._track_provider_usage(
                            quote_provider.provider_type,
                            "get_stock_quote",
                            operation_time,
                            False
                        )
                else:
                    # Fallback: assume symbol is valid (legacy behavior)
                    validated_results.append(StockScreenResult(
                        symbol=symbol,
                        company_name=symbol,
                        last_price=Decimal('100'),  # Placeholder
                        volume=1000000,  # Placeholder
                        market_cap=None,
                        passed_screening=True,
                        screening_scores={}
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Error validating symbol {symbol}: {e}")
                continue
        
        return validated_results
    
    def _convert_screening_response(self, screening_data) -> List[StockScreenResult]:
        """Convert provider screening response to StockScreenResult format."""
        results = []
        
        # Handle different response formats from different providers
        if hasattr(screening_data, 'results') and isinstance(screening_data.results, list):
            # EODHD format with results attribute
            for item in screening_data.results:
                try:
                    # Handle EODHDScreenerResult objects
                    if hasattr(item, 'code'):
                        # Create a StockQuote from the screener data
                        quote = StockQuote(
                            symbol=item.code,
                            last=getattr(item, 'adjusted_close', None),
                            volume=getattr(item, 'volume', 0) or getattr(item, 'avgvol_1d', 0),
                            updated=datetime.now()
                        )
                        result = StockScreenResult(
                            symbol=item.code,
                            quote=quote,
                            market_cap=getattr(item, 'market_capitalization', None),
                            screening_score=Decimal('100')  # Passed screening
                        )
                    else:
                        # Handle dict format
                        quote = StockQuote(
                            symbol=item.get('code', ''),
                            last=Decimal(str(item.get('adjusted_close', 0))),
                            volume=item.get('volume', 0) or item.get('avgvol_1d', 0),
                            updated=datetime.now()
                        )
                        result = StockScreenResult(
                            symbol=item.get('code', ''),
                            quote=quote,
                            market_cap=Decimal(str(item.get('market_capitalization', 0))),
                            screening_score=Decimal('100')  # Passed screening
                        )
                    results.append(result)
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Error parsing screening item: {e}")
                    continue
        elif isinstance(screening_data, list):
            # Direct list format
            for item in screening_data:
                if isinstance(item, dict):
                    try:
                        result = StockScreenResult(
                            symbol=item.get('symbol', item.get('code', '')),
                            company_name=item.get('name', ''),
                            last_price=Decimal(str(item.get('price', item.get('close', 0)))),
                            volume=item.get('volume', 0),
                            market_cap=Decimal(str(item.get('market_cap', item.get('market_capitalization', 0)))),
                            passed_screening=True,
                            screening_scores={}
                        )
                        results.append(result)
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Error parsing screening item: {e}")
                        continue
        
        return results
    
    def _log_provider_usage_summary(self):
        """Log summary of provider usage during the scan."""
        if not self.current_scan_usage:
            return
        
        self.logger.info("Provider Usage Summary:")
        for provider_type, stats in self.current_scan_usage.items():
            self.logger.info(
                f"  {provider_type.value}: {stats.operations_count} ops, "
                f"{stats.success_rate:.1%} success rate, "
                f"{stats.average_latency_ms:.1f}ms avg latency, "
                f"{stats.credits_used} credits used"
            )
    
    @classmethod
    def create_with_provider_factory(cls, 
                                   settings: Optional[Settings] = None) -> 'PMCCScanner':
        """Create scanner instance with provider factory setup."""
        # Initialize provider configuration manager with full Settings object
        config_manager = ProviderConfigurationManager(settings)
        
        # Validate configuration
        issues = config_manager.validate_configuration()
        if issues:
            logger = logging.getLogger(cls.__name__)
            for issue in issues:
                logger.warning(f"Configuration issue: {issue}")
        
        # Create provider factory
        # Get fallback strategy from settings if available
        fallback_strategy = FallbackStrategy.OPERATION_SPECIFIC
        if settings and hasattr(settings, 'providers') and settings.providers:
            fallback_strategy = settings.providers.fallback_strategy
        
        provider_factory = SyncDataProviderFactory(
            fallback_strategy=fallback_strategy
        )
        
        # Register providers
        provider_configs = config_manager.get_provider_configs()
        for config in provider_configs:
            provider_factory.register_provider(config)
        
        # Create scanner instance
        return cls(
            provider_factory=provider_factory,
            provider_config_manager=config_manager
        )
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get current status of all providers."""
        if self.use_provider_factory:
            return {
                "factory_status": self.provider_factory.get_provider_status() if hasattr(self.provider_factory, 'get_provider_status') else {},
                "config_summary": self.provider_config_manager.get_provider_summary(),
                "current_scan_usage": {
                    provider.value: {
                        "operations": stats.operations_count,
                        "success_rate": stats.success_rate,
                        "avg_latency_ms": stats.average_latency_ms,
                        "credits_used": stats.credits_used
                    } for provider, stats in self.current_scan_usage.items()
                }
            }
        else:
            return {
                "mode": "legacy",
                "eodhd_available": self.eodhd_client is not None,
                "marketdata_available": self.api_client is not None
            }
    
    def get_scan_summary(self, results: ScanResults) -> Dict[str, Any]:
        """Generate a summary of scan results."""
        
        summary = {
            'scan_id': results.scan_id,
            'duration_seconds': results.total_duration_seconds,
            'statistics': {
                'stocks_screened': results.stocks_screened,
                'stocks_passed': results.stocks_passed_screening,
                'opportunities_found': results.opportunities_found,
                'success_rate': f"{results.success_rate:.1%}",
                'opportunity_rate': f"{results.opportunity_rate:.1%}"
            },
            'provider_usage': {
                provider.value: {
                    'operations': stats.operations_count,
                    'success_rate': f"{stats.success_rate:.1%}",
                    'avg_latency_ms': round(stats.average_latency_ms, 1),
                    'credits_used': stats.credits_used
                } for provider, stats in results.provider_usage.items()
            } if results.provider_usage else {}
        }
        
        if results.top_opportunities:
            # Top opportunity summary
            top_opp = results.top_opportunities[0]
            summary['top_opportunity'] = {
                'symbol': top_opp.symbol,
                'score': float(top_opp.total_score or 0),
                'max_profit': float(top_opp.analysis.risk_metrics.max_profit or 0) if top_opp.analysis.risk_metrics else 0,
                'risk_reward_ratio': float(getattr(top_opp, 'risk_reward_ratio', 0) or 0)
            }
            
            # Score distribution
            scores = [float(opp.total_score or 0) for opp in results.top_opportunities]
            summary['score_distribution'] = {
                'highest': max(scores) if scores else 0,
                'lowest': min(scores) if scores else 0,
                'average': sum(scores) / len(scores) if scores else 0
            }
        
        # Error summary
        if results.errors:
            summary['errors'] = len(results.errors)
        if results.warnings:
            summary['warnings'] = len(results.warnings)
        
        # Add operation routing summary if available
        if results.operation_routing:
            summary['operation_routing'] = {
                operation: {
                    'total_operations': len(ops),
                    'success_rate': f"{sum(1 for _, _, success in ops if success) / len(ops):.1%}" if ops else "0%",
                    'providers_used': list(set(provider.value for _, provider, _ in ops))
                } for operation, ops in results.operation_routing.items()
            }
        
        return summary