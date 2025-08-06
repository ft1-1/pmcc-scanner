"""
Main PMCC Scanner orchestrator.

Coordinates the entire PMCC scanning workflow from stock screening
to final opportunity ranking and reporting.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
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
    from src.models.api_models import StockQuote, OptionContract
    from src.api.provider_factory import SyncDataProviderFactory, FallbackStrategy
    from src.api.data_provider import ProviderType, ScreeningCriteria as ProviderScreeningCriteria
    from src.config.provider_config import ProviderConfigurationManager, DataProviderSettings
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
    from models.api_models import StockQuote, OptionContract
    from api.provider_factory import SyncDataProviderFactory, FallbackStrategy
    from api.data_provider import ProviderType, ScreeningCriteria as ProviderScreeningCriteria
    from config.provider_config import ProviderConfigurationManager, DataProviderSettings
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
    scan_id: str
    started_at: datetime
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
            'errors': self.errors,
            'warnings': self.warnings
        }


class PMCCScanner:
    """Main PMCC scanner that orchestrates the entire workflow with provider abstraction."""
    
    def __init__(self, 
                 provider_factory: Optional[SyncDataProviderFactory] = None,
                 provider_config_manager: Optional[ProviderConfigurationManager] = None,
                 # Legacy parameters for backward compatibility
                 eodhd_client: Optional[EODHDClient] = None,
                 api_client: Optional[MarketDataClient] = None,
                 eodhd_config=None):
        """
        Initialize scanner with provider factory for automatic failover.
        
        Args:
            provider_factory: Data provider factory for automatic failover (preferred)
            provider_config_manager: Provider configuration manager (preferred)
            eodhd_client: Legacy EODHD client (for backward compatibility)
            api_client: Legacy MarketData client (for backward compatibility)
            eodhd_config: Legacy EODHD configuration (for backward compatibility)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize provider system
        if provider_factory is not None:
            self.provider_factory = provider_factory
            self.provider_config_manager = provider_config_manager or ProviderConfigurationManager()
            self.use_provider_factory = True
            self.logger.info("PMCCScanner initialized with provider factory")
        else:
            # Legacy initialization
            self.logger.warning("Using legacy initialization. Consider updating to use provider factory.")
            self._initialize_legacy_mode(eodhd_client, api_client, eodhd_config)
            self.use_provider_factory = False
        
        # Initialize components
        self.risk_calculator = RiskCalculator()
        self.options_analyzer = None
        
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
        
        if not self.eodhd_client:
            raise ValueError("EODHD client is required in legacy mode")
        
        if api_client:
            self.logger.warning("MarketData client passed but may not be used effectively in legacy mode.")
        
        # Initialize stock screener with legacy clients
        self.stock_screener = StockScreener(None, eodhd_client)
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
                    from src.api.sync_eodhd_client import SyncEODHDClient
                    self.sync_eodhd_client = SyncEODHDClient(
                        api_token=self.eodhd_client.api_token,
                        base_url=self.eodhd_client.base_url,
                        timeout=self.eodhd_client.timeout.total,
                        max_retries=self.eodhd_client.max_retries,
                        retry_backoff=self.eodhd_client.retry_backoff
                    )
                
                self.options_analyzer = OptionsAnalyzer(
                    eodhd_client=self.sync_eodhd_client,
                    api_client=None,
                    options_source="eodhd",
                    eodhd_config=self.eodhd_config
                )
            else:
                # Force EODHD in legacy mode
                if not self.sync_eodhd_client:
                    from src.api.sync_eodhd_client import SyncEODHDClient
                    self.sync_eodhd_client = SyncEODHDClient(
                        api_token=self.eodhd_client.api_token,
                        base_url=self.eodhd_client.base_url,
                        timeout=self.eodhd_client.timeout.total,
                        max_retries=self.eodhd_client.max_retries,
                        retry_backoff=self.eodhd_client.retry_backoff
                    )
                
                self.options_analyzer = OptionsAnalyzer(
                    eodhd_client=self.sync_eodhd_client,
                    api_client=None,
                    options_source="eodhd",
                    eodhd_config=self.eodhd_config
                )
            
            self.logger.info(f"Options analyzer initialized with legacy source='{options_source}'")
    
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
        
        # Find PMCC opportunities
        opportunities = self.options_analyzer.find_pmcc_opportunities(
            symbol, config.leaps_criteria, config.short_criteria
        )
        
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
            self.options_analyzer = OptionsAnalyzer(
                eodhd_client=self.sync_eodhd_client,
                api_client=None,
                options_source="eodhd"
            )
        
        # Get current quote from EODHD
        quote_response = self.sync_eodhd_client.get_stock_quote(symbol)
        if not quote_response.is_success:
            self.logger.warning(f"Could not get EODHD quote for {symbol}")
            return []
        
        quote = quote_response.data  # Already in StockQuote format from EODHD client
        
        # Find PMCC opportunities
        opportunities = self.options_analyzer.find_pmcc_opportunities(
            symbol, config.leaps_criteria, config.short_criteria
        )
        
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
        
        # Convert screening criteria to provider format
        # Note: ScreeningCriteria has market cap in millions, but ProviderScreeningCriteria expects USD
        provider_criteria = ProviderScreeningCriteria(
            min_market_cap=config.screening_criteria.min_market_cap * 1000000 if config.screening_criteria and config.screening_criteria.min_market_cap else None,
            max_market_cap=config.screening_criteria.max_market_cap * 1000000 if config.screening_criteria and config.screening_criteria.max_market_cap else None,
            min_price=config.screening_criteria.min_price if config.screening_criteria else None,
            max_price=config.screening_criteria.max_price if config.screening_criteria else None,
            min_volume=config.screening_criteria.min_daily_volume if config.screening_criteria else None,
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
            initial_symbols = self.stock_screener._get_universe_symbols(config.universe, config.screening_criteria)
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
                
                opportunities = self.options_analyzer.find_pmcc_opportunities(
                    symbol, config.leaps_criteria, config.short_criteria
                )
                
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
                                   provider_settings: Optional[DataProviderSettings] = None) -> 'PMCCScanner':
        """Create scanner instance with provider factory setup."""
        # Initialize provider configuration manager
        config_manager = ProviderConfigurationManager(provider_settings)
        
        # Validate configuration
        issues = config_manager.validate_configuration()
        if issues:
            logger = logging.getLogger(cls.__name__)
            for issue in issues:
                logger.warning(f"Configuration issue: {issue}")
        
        # Create provider factory
        provider_factory = SyncDataProviderFactory(
            fallback_strategy=provider_settings.fallback_strategy if provider_settings else FallbackStrategy.OPERATION_SPECIFIC
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