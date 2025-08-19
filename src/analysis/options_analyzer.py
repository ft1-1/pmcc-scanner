"""
Options analyzer for PMCC strategy implementation.

Analyzes option chains to identify optimal LEAPS and short call combinations
for Poor Man's Covered Call strategies.
"""

import logging
import asyncio
from typing import List, Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
import math

try:
    from src.models.api_models import OptionChain, OptionContract, OptionSide, StockQuote
    from src.models.pmcc_models import PMCCAnalysis, RiskMetrics
    from src.api.data_provider import DataProvider, SyncDataProvider
    from src.analysis.pmcc_analysis_reporter import PMCCAnalysisReporter
    from src.config.settings import AnalysisVerbosity
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.api_models import OptionChain, OptionContract, OptionSide, StockQuote
    from models.pmcc_models import PMCCAnalysis, RiskMetrics
    from api.data_provider import DataProvider, SyncDataProvider
    from analysis.pmcc_analysis_reporter import PMCCAnalysisReporter
    from config.settings import AnalysisVerbosity


logger = logging.getLogger(__name__)


@dataclass
class LEAPSCriteria:
    """Criteria for selecting LEAPS contracts."""
    min_dte: int = 270  # 9 months minimum
    max_dte: int = 730  # 24 months maximum
    min_delta: Decimal = Decimal('0.75')  # Deep ITM requirement
    max_delta: Decimal = Decimal('0.90')  # Not too deep to maintain some time value
    max_bid_ask_spread_pct: Decimal = Decimal('5.0')  # 5% max spread
    min_open_interest: int = 100  # Updated default to 100
    min_volume: int = 1  # Minimum daily volume
    moneyness: str = "ITM"  # Only ITM LEAPS
    max_premium_pct: Decimal = Decimal('0.20')  # Maximum premium as % of stock price (20% default)
    max_extrinsic_pct: Decimal = Decimal('0.15')  # Maximum extrinsic value as % of option price (15% default)


@dataclass
class ShortCallCriteria:
    """Criteria for selecting short call contracts."""
    min_dte: int = 21  # 3 weeks minimum
    max_dte: int = 45  # ~6 weeks maximum 
    min_delta: Decimal = Decimal('0.20')  # OTM but not too far
    max_delta: Decimal = Decimal('0.35')  # Reasonable probability of profit
    max_bid_ask_spread_pct: Decimal = Decimal('5.0')  # 5% max spread (updated from 10%)
    min_open_interest: int = 200  # Updated default to 200
    min_volume: int = 10  # Added minimum volume requirement
    prefer_weekly: bool = True  # Prefer weekly expirations for flexibility
    moneyness: str = "OTM"  # Only OTM calls
    min_premium_coverage_ratio: Decimal = Decimal('0.50')  # Min ratio of short premium to LEAPS extrinsic


@dataclass
class PMCCOpportunity:
    """Represents a PMCC opportunity with scoring."""
    leaps_contract: OptionContract
    short_contract: OptionContract
    underlying_quote: StockQuote
    net_debit: Decimal
    max_profit: Decimal
    max_loss: Decimal
    breakeven: Decimal
    roi_potential: Decimal  # Return on investment %
    risk_reward_ratio: Decimal
    probability_score: Decimal  # 0-100 probability score
    liquidity_score: Decimal  # 0-100 liquidity score
    total_score: Decimal  # 0-100 composite score
    analyzed_at: datetime


class OptionsAnalyzer:
    """Analyzes options for PMCC opportunities with comprehensive quantitative reporting."""
    
    def __init__(self, 
                 data_provider: Union[DataProvider, SyncDataProvider],
                 verbosity: AnalysisVerbosity = AnalysisVerbosity.NORMAL,
                 config: Optional[Dict[str, Any]] = None,
                 # Legacy parameters for backward compatibility
                 client_or_eodhd_client=None,
                 api_client=None,
                 options_source: str = "auto",
                 eodhd_client=None,
                 eodhd_config=None):
        """
        Initialize OptionsAnalyzer with a data provider.
        
        Args:
            data_provider: DataProvider or SyncDataProvider instance for market data
            verbosity: Analysis verbosity level for detailed reporting
            config: Configuration dictionary for analysis parameters
            
        Legacy Args (for backward compatibility):
            client_or_eodhd_client: Legacy parameter, use data_provider instead
            api_client: Legacy parameter, use data_provider instead
            options_source: Legacy parameter, provider type is auto-detected
            eodhd_client: Legacy parameter, use data_provider instead
            eodhd_config: Legacy parameter, use config instead
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.verbosity = verbosity
        self.config = config or {}
        
        # Handle backward compatibility
        if data_provider is None:
            self.logger.warning("Using legacy initialization pattern. Please update to use DataProvider.")
            
            # Try to use legacy parameters
            if eodhd_client is not None:
                if client_or_eodhd_client is not None:
                    self.logger.warning("Both client_or_eodhd_client and eodhd_client provided. Using eodhd_client.")
                client_or_eodhd_client = eodhd_client
            
            if client_or_eodhd_client:
                # Create a wrapper for legacy clients
                self.data_provider = self._create_legacy_provider_wrapper(client_or_eodhd_client)
                if eodhd_config:
                    self.config.update(eodhd_config)
            else:
                raise ValueError("Either data_provider or legacy client must be provided")
        else:
            self.data_provider = data_provider
        
        # Initialize comprehensive analysis reporter
        self.analysis_reporter = PMCCAnalysisReporter(verbosity=verbosity)
        
        # Determine provider type for optimization
        if hasattr(self.data_provider, 'provider_type'):
            self.provider_type = self.data_provider.provider_type
        else:
            self.provider_type = None
        
        self.logger.info(f"OptionsAnalyzer initialized with provider type: {self.provider_type}, verbosity: {verbosity.value}")
    
    def _execute_provider_method(self, method_name: str, *args, **kwargs):
        """
        Execute a provider method with proper error handling and async support.
        
        Args:
            method_name: Name of the method to call on the provider
            *args, **kwargs: Arguments to pass to the method
            
        Returns:
            Method result or None if failed
        """
        try:
            if not hasattr(self.data_provider, method_name):
                self.logger.error(f"Provider does not support method: {method_name}")
                return None
            
            method = getattr(self.data_provider, method_name)
            result = method(*args, **kwargs)
            
            # Handle async responses
            if hasattr(result, '__await__'):
                result = asyncio.run(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing {method_name} on provider: {e}")
            return None
    
    def _create_legacy_provider_wrapper(self, legacy_client):
        """
        Create a wrapper for legacy clients to maintain backward compatibility.
        
        Args:
            legacy_client: Legacy EODHD or MarketData client
            
        Returns:
            Wrapper that implements basic DataProvider interface
        """
        # This is a simple wrapper - in production you'd want a more complete implementation
        class LegacyProviderWrapper:
            def __init__(self, client):
                self.client = client
                self.provider_type = "legacy"
            
            def get_stock_quote(self, symbol: str):
                """Get stock quote using legacy client."""
                if hasattr(self.client, 'get_quote'):
                    return self.client.get_quote(symbol)
                elif hasattr(self.client, 'get_stock_quote_eod'):
                    return asyncio.run(self.client.get_stock_quote_eod(symbol))
                else:
                    raise NotImplementedError("Legacy client doesn't support quote fetching")
            
            def get_options_chain(self, symbol: str, expiration_from=None, expiration_to=None):
                """Get options chain using legacy client."""
                # Skip get_pmcc_options_comprehensive to avoid EODHD-specific calls
                if hasattr(self.client, 'get_option_chain_eodhd'):
                    return asyncio.run(self.client.get_option_chain_eodhd(symbol))
                elif hasattr(self.client, 'get_option_chain'):
                    return asyncio.run(self.client.get_option_chain(symbol))
                else:
                    raise NotImplementedError("Legacy client doesn't support options chain fetching")
        
        return LegacyProviderWrapper(legacy_client)
    
    def set_verbosity(self, verbosity: AnalysisVerbosity) -> None:
        """
        Set analysis verbosity level.
        
        Args:
            verbosity: New verbosity level
        """
        self.verbosity = verbosity
        self.analysis_reporter.verbosity = verbosity
        self.logger.info(f"Analysis verbosity set to: {verbosity.value}")
    
    def find_pmcc_opportunities(self, symbol: str,
                               leaps_criteria: Optional[LEAPSCriteria] = None,
                               short_criteria: Optional[ShortCallCriteria] = None,
                               max_opportunities: int = 10,
                               return_option_chain: bool = False) -> Union[List[PMCCOpportunity], Tuple[List[PMCCOpportunity], Optional['OptionChain']]]:
        """
        Find PMCC opportunities for a given symbol.
        
        Args:
            symbol: Stock symbol to analyze
            leaps_criteria: Criteria for LEAPS selection
            short_criteria: Criteria for short call selection
            max_opportunities: Maximum opportunities to return
            return_option_chain: If True, return tuple of (opportunities, option_chain)
            
        Returns:
            List of PMCCOpportunity objects, sorted by total score
            Or tuple of (opportunities, option_chain) if return_option_chain=True
        """
        print(f"\n🚀 find_pmcc_opportunities called for {symbol}")
        
        if leaps_criteria is None:
            leaps_criteria = LEAPSCriteria()
        if short_criteria is None:
            short_criteria = ShortCallCriteria()
        
        try:
            # Helper function for consistent returns
            def _return_result(opportunities: List[PMCCOpportunity], option_chain: Optional['OptionChain'] = None):
                if return_option_chain:
                    return (opportunities, option_chain)
                return opportunities
            
            # Check if data provider is available
            if not self.data_provider:
                self.logger.error(f"Cannot analyze {symbol}: Data provider not available")
                return _return_result([])
            
            # Get current quote first (needed for EODHD optimization)
            quote = self._get_current_quote(symbol)
            if not quote:
                self.logger.warning(f"Unable to retrieve stock quote for {symbol} - skipping analysis")
                return _return_result([])
            
            # Get option chain with current price for optimization
            current_price = float(quote.last or quote.mid) if (quote.last or quote.mid) else None
            option_chain_result = self._get_option_chain_with_details(symbol, current_price)
            
            if option_chain_result["status"] == "api_error":
                self.logger.error(f"API error retrieving option chain for {symbol}: {option_chain_result['message']}")
                return _return_result([])
            elif option_chain_result["status"] == "no_options":
                self.logger.info(f"{symbol} has no options available for trading")
                return _return_result([])
            elif option_chain_result["status"] == "empty_chain":
                self.logger.info(f"{symbol} option chain is empty or contains no valid contracts")
                return _return_result([])
            elif option_chain_result["status"] == "partial_success":
                # Log partial success but continue with analysis
                api_calls = option_chain_result.get("api_calls", "unknown")
                success_rate = option_chain_result.get("success_rate", 0.0)
                leaps_count = option_chain_result.get("leaps_count", 0)
                short_count = option_chain_result.get("short_count", 0)
                self.logger.warning(f"{symbol} comprehensive fetch partially successful: {success_rate:.1f}% success rate "
                                  f"({api_calls} API calls), found {leaps_count} LEAPS + {short_count} short calls")
                # Continue with analysis despite partial success
            
            option_chain = option_chain_result["data"]
            if not option_chain:
                self.logger.warning(f"Unexpected: option chain data is None for {symbol}")
                return _return_result([])
            
            print(f"   📦 Option chain loaded: {len(option_chain.contracts)} contracts, underlying_price=${option_chain.underlying_price}")
            
            # Generate comprehensive analysis report (only if not QUIET)
            feasibility_report = None
            if self.verbosity != AnalysisVerbosity.QUIET:
                try:
                    feasibility_report = self.analysis_reporter.analyze_option_chain_comprehensive(
                        symbol, option_chain, quote, leaps_criteria, short_criteria
                    )
                    
                    # If no valid combinations, return empty list (report already logged)
                    if not feasibility_report.is_pmcc_feasible:
                        print(f"   ⚠️  Analysis reporter says PMCC not feasible! Skipping early.")
                        print(f"       Feasibility report: is_pmcc_feasible={feasibility_report.is_pmcc_feasible}")
                        # COMMENTING OUT EARLY RETURN TO DEBUG
                        # return _return_result([], option_chain)
                except Exception as e:
                    self.logger.error(f"Error in comprehensive analysis for {symbol}: {e}")
                    # Fallback to basic analysis without the reporter
                    feasibility_report = None
            
            # Find suitable LEAPS and short call contracts using existing methods
            print(f"   🎯 About to filter contracts - quote.last=${quote.last if quote else 'None'}")
            try:
                leaps_candidates = self._filter_leaps_contracts(
                    option_chain, leaps_criteria, quote
                )
            except Exception as e:
                self.logger.error(f"Error filtering LEAPS for {symbol}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                leaps_candidates = []
                
            try:
                short_candidates = self._filter_short_contracts(
                    option_chain, short_criteria, quote
                )
            except Exception as e:
                self.logger.error(f"Error filtering short calls for {symbol}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                short_candidates = []
            
            # Debug: Always print filtering results
            print(f"   📊 Filtering results for {symbol}:")
            print(f"      LEAPS candidates found: {len(leaps_candidates)}")
            print(f"      Short candidates found: {len(short_candidates)}")
            
            if len(leaps_candidates) > 0:
                print(f"      LEAPS contracts that passed filters:")
                for i, leaps in enumerate(leaps_candidates[:3]):  # Show first 3
                    delta_str = f"{leaps.delta:.3f}" if leaps.delta else "N/A"
                    print(f"        #{i+1}: Strike=${leaps.strike}, Delta={delta_str}, "
                          f"DTE={leaps.dte}, OI={leaps.open_interest}, Bid/Ask=${leaps.bid}/${leaps.ask}, "
                          f"Moneyness={leaps.moneyness}")
            else:
                print(f"      ❌ No LEAPS passed filters!")
                
            if len(short_candidates) > 0:
                print(f"      Short calls that passed filters:")
                for i, short in enumerate(short_candidates[:3]):  # Show first 3
                    delta_str = f"{short.delta:.3f}" if short.delta else "N/A"
                    print(f"        #{i+1}: Strike=${short.strike}, Delta={delta_str}, "
                          f"DTE={short.dte}, OI={short.open_interest}, Bid/Ask=${short.bid}/${short.ask}, "
                          f"Moneyness={short.moneyness}")
            else:
                print(f"      ❌ No short calls passed filters!")
            
            # Generate and analyze PMCC combinations
            opportunities = []
            for leaps in leaps_candidates:
                # Calculate LEAPS extrinsic value once per LEAPS contract
                leaps_intrinsic = max(Decimal('0'), quote.last - leaps.strike) if quote.last and leaps.strike else Decimal('0')
                # Use mid price if available, otherwise calculate it
                leaps_mid = leaps.mid if leaps.mid else (leaps.bid + leaps.ask) / Decimal('2') if (leaps.bid and leaps.ask) else None
                leaps_extrinsic = (leaps_mid - leaps_intrinsic) if leaps_mid else Decimal('0')
                
                for short in short_candidates:
                    if self._is_valid_pmcc_combination(leaps, short, quote):
                        # Check premium coverage ratio (only if enabled)
                        if short_criteria.min_premium_coverage_ratio > 0 and leaps_extrinsic > 0 and short.bid:
                            coverage_ratio = short.bid / leaps_extrinsic
                            if coverage_ratio < short_criteria.min_premium_coverage_ratio:
                                if self.verbosity == AnalysisVerbosity.DEBUG:
                                    self.logger.debug(f"PMCC {leaps.strike}/{short.strike} rejected: premium coverage ratio {coverage_ratio:.2f} < {short_criteria.min_premium_coverage_ratio}")
                                continue
                        
                        opportunity = self._analyze_pmcc_combination(
                            leaps, short, quote
                        )
                        if opportunity:
                            opportunities.append(opportunity)
            
            # Sort by total score and return top results
            opportunities.sort(key=lambda x: x.total_score, reverse=True)
            
            if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
                self.logger.info(f"{symbol}: Generated {len(opportunities)} PMCC opportunities, "
                               f"returning top {min(len(opportunities), max_opportunities)}")
            
            # If no opportunities found, log a summary of why
            if len(opportunities) == 0:
                if self.verbosity != AnalysisVerbosity.QUIET:
                    self._log_no_opportunities_summary(symbol, leaps_candidates, short_candidates, 
                                                     option_chain, leaps_criteria, short_criteria)
                else:
                    # Even in quiet mode, print a basic summary for debugging
                    print(f"   ℹ️  Debug: {len(leaps_candidates)} LEAPS candidates, {len(short_candidates)} short candidates found")
            
            return _return_result(opportunities[:max_opportunities], option_chain)
            
        except Exception as e:
            self.logger.error(f"Unexpected error analyzing PMCC opportunities for {symbol}: {e}")
            return _return_result([])
    
    def analyze_specific_pmcc(self, leaps_symbol: str, short_symbol: str) -> Optional[PMCCOpportunity]:
        """
        Analyze a specific PMCC combination using Greeks data from the provider.
        
        Args:
            leaps_symbol: LEAPS option symbol
            short_symbol: Short call option symbol
            
        Returns:
            PMCCOpportunity if valid, None otherwise
        """
        try:
            # Get Greeks for both contracts using provider abstraction
            leaps_response = self._execute_provider_method('get_greeks', leaps_symbol)
            short_response = self._execute_provider_method('get_greeks', short_symbol)
            
            if not leaps_response or not short_response:
                self.logger.warning(f"Could not retrieve Greeks for {leaps_symbol} or {short_symbol}")
                return None
            
            if not (leaps_response.is_success and short_response.is_success):
                self.logger.warning(f"Greeks retrieval failed for PMCC {leaps_symbol}/{short_symbol}")
                return None
            
            leaps_contract = leaps_response.data
            short_contract = short_response.data
            
            if not isinstance(leaps_contract, OptionContract) or not isinstance(short_contract, OptionContract):
                self.logger.error(f"Invalid contract data received for {leaps_symbol}/{short_symbol}")
                return None
            
            # Get underlying quote
            underlying_symbol = self._parse_underlying_from_option_symbol(leaps_symbol)
            if not underlying_symbol:
                self.logger.error(f"Cannot parse underlying from {leaps_symbol}")
                return None
            
            quote = self._get_current_quote(underlying_symbol)
            if not quote:
                self.logger.error(f"Cannot get quote for underlying {underlying_symbol}")
                return None
            
            # Validate and analyze the combination
            if self._is_valid_pmcc_combination(leaps_contract, short_contract, quote):
                return self._analyze_pmcc_combination(leaps_contract, short_contract, quote)
            else:
                self.logger.info(f"Invalid PMCC combination: {leaps_symbol}/{short_symbol}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing specific PMCC {leaps_symbol}/{short_symbol}: {e}")
            return None
    
    def _parse_underlying_from_option_symbol(self, option_symbol: str) -> Optional[str]:
        """
        Parse underlying symbol from option symbol.
        
        Standard option symbol formats:
        - AAPL240119C150000 (AAPL underlying)
        - AAPL_240119C150 (some formats use underscore)
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            Underlying symbol or None if parsing fails
        """
        try:
            # Handle underscore format first
            if '_' in option_symbol:
                return option_symbol.split('_')[0]
            
            # Standard format - find first digit
            for i, char in enumerate(option_symbol):
                if char.isdigit():
                    return option_symbol[:i]
            
            # Fallback - if no digits found, might be non-standard format
            self.logger.warning(f"Could not parse underlying from option symbol: {option_symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing underlying from {option_symbol}: {e}")
            return None
    
    def check_provider_health(self) -> Dict[str, Any]:
        """
        Check the health of the configured data provider.
        
        Returns:
            Dictionary with provider health information
        """
        try:
            health_info = {
                'provider_type': str(self.provider_type),
                'is_healthy': False,
                'supports_quotes': False,
                'supports_options': False,
                'supports_greeks': False,
                'error_message': None
            }
            
            # Check if provider has health_check method
            if hasattr(self.data_provider, 'health_check'):
                health_result = self._execute_provider_method('health_check')
                if health_result:
                    health_info['is_healthy'] = health_result.status.value == 'healthy'
                    health_info['latency_ms'] = getattr(health_result, 'latency_ms', None)
                    health_info['error_message'] = getattr(health_result, 'error_message', None)
            
            # Check supported operations
            if hasattr(self.data_provider, 'supports_operation'):
                health_info['supports_quotes'] = self.data_provider.supports_operation('get_stock_quote')
                health_info['supports_options'] = self.data_provider.supports_operation('get_options_chain')
                health_info['supports_greeks'] = self.data_provider.supports_operation('get_greeks')
            else:
                # Assume basic support for legacy providers
                health_info['supports_quotes'] = hasattr(self.data_provider, 'get_stock_quote')
                health_info['supports_options'] = hasattr(self.data_provider, 'get_options_chain')
                health_info['supports_greeks'] = hasattr(self.data_provider, 'get_greeks')
            
            return health_info
            
        except Exception as e:
            return {
                'provider_type': str(self.provider_type),
                'is_healthy': False,
                'supports_quotes': False,
                'supports_options': False,
                'supports_greeks': False,
                'error_message': f"Health check failed: {str(e)}"
            }
    
    def validate_pmcc_requirements(self, symbol: str) -> Dict[str, Any]:
        """
        Validate that the provider can support PMCC analysis for a symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'symbol': symbol,
            'can_analyze': False,
            'has_quote': False,
            'has_options': False,
            'options_count': 0,
            'leaps_count': 0,
            'short_calls_count': 0,
            'issues': []
        }
        
        try:
            # Check provider health first
            health = self.check_provider_health()
            if not health['is_healthy']:
                validation['issues'].append(f"Provider unhealthy: {health.get('error_message', 'Unknown error')}")
                return validation
            
            # Test quote retrieval
            quote = self._get_current_quote(symbol)
            if quote:
                validation['has_quote'] = True
            else:
                validation['issues'].append(f"Cannot retrieve quote for {symbol}")
            
            # Test options chain retrieval
            chain_result = self._get_option_chain_with_details(symbol)
            if chain_result['status'] == 'success' and chain_result['data']:
                validation['has_options'] = True
                validation['options_count'] = len(chain_result['data'].contracts)
                validation['leaps_count'] = chain_result.get('leaps_count', 0)
                validation['short_calls_count'] = chain_result.get('short_count', 0)
                
                if validation['leaps_count'] == 0:
                    validation['issues'].append(f"No LEAPS candidates found for {symbol}")
                if validation['short_calls_count'] == 0:
                    validation['issues'].append(f"No short call candidates found for {symbol}")
                    
            else:
                validation['issues'].append(f"Cannot retrieve options chain: {chain_result.get('message', 'Unknown error')}")
            
            # Overall assessment
            validation['can_analyze'] = (
                validation['has_quote'] and 
                validation['has_options'] and 
                validation['leaps_count'] > 0 and 
                validation['short_calls_count'] > 0
            )
            
        except Exception as e:
            validation['issues'].append(f"Validation error: {str(e)}")
        
        return validation
    
    def _get_option_chain_with_details(self, symbol: str, current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Get option chain for symbol using the configured data provider with detailed status information.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price (used for optimization)
            
        Returns:
            Dict with keys: 'status', 'data', 'message', 'api_calls', 'success_rate'
            Status values: 'success', 'api_error', 'no_options', 'empty_chain', 'partial_success'
        """
        try:
            # Calculate reasonable date ranges for PMCC strategy
            today = date.today()
            leaps_min_date = today + timedelta(days=270)  # 9 months minimum for LEAPS
            leaps_max_date = today + timedelta(days=730)  # 24 months maximum for LEAPS
            short_min_date = today + timedelta(days=21)   # 3 weeks minimum for short calls
            short_max_date = today + timedelta(days=45)   # 6 weeks maximum for short calls
            
            # Get options chain using provider abstraction
            self.logger.info(f"Data provider type: {type(self.data_provider)}")
            self.logger.info(f"Data provider attributes: {dir(self.data_provider)}")
            
            if hasattr(self.data_provider, 'get_options_chain'):
                # Use full range to get both LEAPS and short options
                self.logger.info(f"Fetching options for {symbol} using provider: {getattr(self.data_provider, 'provider_type', 'unknown')}")
                response = self.data_provider.get_options_chain(
                    symbol, 
                    expiration_from=short_min_date,
                    expiration_to=leaps_max_date
                )
                
                # Handle async response
                if hasattr(response, '__await__'):
                    response = asyncio.run(response)
                    
            else:
                # Legacy provider case
                response = self.data_provider.get_options_chain(symbol)
            
            if not response or not hasattr(response, 'is_success'):
                return {
                    "status": "api_error",
                    "data": None,
                    "message": f"Invalid response from provider for {symbol}",
                    "api_calls": 1,
                    "success_rate": 0.0
                }
            
            if not response.is_success:
                return {
                    "status": "api_error",
                    "data": None,
                    "message": f"Provider API returned error status for {symbol}: {response.error}",
                    "api_calls": 1,
                    "success_rate": 0.0
                }
            
            if not response.data:
                return {
                    "status": "no_options",
                    "data": None,
                    "message": f"No option data returned from provider for {symbol}",
                    "api_calls": 1,
                    "success_rate": 0.0
                }
            
            option_chain = response.data
            
            if not option_chain or not hasattr(option_chain, 'contracts') or not option_chain.contracts:
                return {
                    "status": "empty_chain",
                    "data": None,
                    "message": f"Option chain is empty or contains no contracts for {symbol}",
                    "api_calls": 1,
                    "success_rate": 0.0
                }
            
            # Count LEAPS and short call candidates
            leaps_count = 0
            short_count = 0
            today = date.today()
            
            for contract in option_chain.contracts:
                if contract.side == OptionSide.CALL and contract.dte:
                    if 270 <= contract.dte <= 730:  # LEAPS range
                        leaps_count += 1
                    elif 21 <= contract.dte <= 45:  # Short call range
                        short_count += 1
            
            return {
                "status": "success",
                "data": option_chain,
                "message": f"Successfully retrieved {len(option_chain.contracts)} options for {symbol}",
                "api_calls": 1,
                "success_rate": 100.0,
                "leaps_count": leaps_count,
                "short_count": short_count
            }
                    
        except Exception as e:
            return {
                "status": "api_error",
                "data": None,
                "message": f"Exception retrieving options for {symbol}: {str(e)}",
                "api_calls": 1,
                "success_rate": 0.0
            }

    def _get_option_chain(self, symbol: str, current_price: Optional[float] = None) -> Optional[OptionChain]:
        """
        Get option chain for symbol using the configured data provider (backward compatibility method).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price (used for optimization)
        """
        result = self._get_option_chain_with_details(symbol, current_price)
        # Return data for both success and partial success
        return result["data"] if result["status"] in ["success", "partial_success"] else None
    
    # Provider-specific conversion methods are no longer needed since
    # the provider abstraction handles data format standardization
    
    def _get_current_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote using the configured data provider."""
        try:
            # Handle both sync and async providers
            if hasattr(self.data_provider, 'get_stock_quote'):
                response = self.data_provider.get_stock_quote(symbol)
                # Handle async response
                if hasattr(response, '__await__'):
                    response = asyncio.run(response)
                
                if response.is_success and response.data:
                    return response.data
            else:
                # Legacy wrapper case
                response = self.data_provider.get_stock_quote(symbol)
                if response and hasattr(response, 'is_success') and response.is_success:
                    return response.data
                    
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
        return None
    
    def _filter_leaps_contracts(self, option_chain: OptionChain,
                               criteria: LEAPSCriteria,
                               quote: StockQuote) -> List[OptionContract]:
        """Filter option chain for suitable LEAPS contracts with detailed logging."""
        
        print(f"   🔎 _filter_leaps_contracts called!")
        
        # Start with all call contracts
        calls = option_chain.get_calls()
        candidates = []
        rejection_counts = defaultdict(int)
        
        print(f"   🔍 Filtering LEAPS: {len(calls)} calls, DTE range {criteria.min_dte}-{criteria.max_dte}, verbosity={self.verbosity.value if self.verbosity else 'None'}")
        if self.verbosity == AnalysisVerbosity.DEBUG:
            self.logger.debug(f"Filtering {len(calls)} call contracts for LEAPS (DTE {criteria.min_dte}-{criteria.max_dte})")
        
        # Debug: Show first few contracts being evaluated
        if self.verbosity == AnalysisVerbosity.DEBUG and len(calls) > 0:
            self.logger.debug(f"Sample LEAPS contracts being evaluated:")
            for i, contract in enumerate(calls[:3]):
                self.logger.debug(f"  Contract {i+1}: Strike={contract.strike}, DTE={contract.dte}, "
                                f"Delta={contract.delta}, OI={contract.open_interest}, "
                                f"Bid={contract.bid}, Ask={contract.ask}, Mid={contract.mid}")
        
        for contract in calls:
            # Check days to expiration
            if not contract.dte or contract.dte < criteria.min_dte or contract.dte > criteria.max_dte:
                rejection_counts["dte_out_of_range"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"LEAPS {contract.strike} rejected: DTE {contract.dte} not in range")
                continue
            
            # Check delta requirements
            if not contract.delta or contract.delta < criteria.min_delta or contract.delta > criteria.max_delta:
                rejection_counts["delta_out_of_range"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"LEAPS {contract.strike} rejected: delta {contract.delta} not in range")
                continue
            
            # Check liquidity
            if not self._check_contract_liquidity(contract, criteria.min_open_interest,
                                                criteria.min_volume, criteria.max_bid_ask_spread_pct):
                rejection_counts["liquidity_insufficient"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    spread_pct = ((contract.ask - contract.bid) / contract.mid * Decimal('100')) if (contract.bid and contract.ask and contract.mid and contract.mid > 0) else None
                    spread_str = f"{spread_pct:.2f}" if spread_pct else "N/A"
                    self.logger.debug(f"LEAPS {contract.strike} rejected: liquidity (OI:{contract.open_interest}, Vol:{contract.volume}, Spread:{spread_str}%)")
                continue
            
            # Check moneyness (should be ITM)
            # Calculate moneyness if not set
            if not contract.moneyness and quote.last and contract.strike:
                if quote.last > contract.strike:
                    calculated_moneyness = "ITM"
                elif abs(quote.last - contract.strike) < Decimal('0.50'):
                    calculated_moneyness = "ATM" 
                else:
                    calculated_moneyness = "OTM"
            else:
                calculated_moneyness = contract.moneyness
                
            if calculated_moneyness != criteria.moneyness:
                rejection_counts["not_itm"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"LEAPS {contract.strike} rejected: not ITM (is {calculated_moneyness}, stock=${quote.last}, strike=${contract.strike})")
                continue
            
            # Ensure reasonable pricing
            if not contract.bid or not contract.ask or contract.bid <= 0:
                rejection_counts["invalid_pricing"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"LEAPS {contract.strike} rejected: invalid pricing (bid:{contract.bid}, ask:{contract.ask})")
                continue
            
            # Check premium as percentage of stock price
            if quote.last and contract.ask:
                premium_pct = contract.ask / quote.last
                if premium_pct > criteria.max_premium_pct:
                    rejection_counts["premium_too_expensive"] += 1
                    if self.verbosity == AnalysisVerbosity.DEBUG:
                        self.logger.debug(f"LEAPS {contract.strike} rejected: premium {contract.ask:.2f} is {premium_pct*100:.1f}% of stock price {quote.last:.2f} (max: {criteria.max_premium_pct*100:.0f}%)")
                    continue
            
            # Check extrinsic value as percentage of option price (only if enabled)
            if criteria.max_extrinsic_pct > 0 and quote.last and contract.strike:
                # Use mid price if available, otherwise calculate it
                mid_price = contract.mid if contract.mid else (contract.bid + contract.ask) / Decimal('2') if (contract.bid and contract.ask) else None
                if mid_price and mid_price > 0:
                    intrinsic_value = max(Decimal('0'), quote.last - contract.strike)
                    extrinsic_value = mid_price - intrinsic_value
                    extrinsic_pct = extrinsic_value / mid_price
                    if extrinsic_pct > criteria.max_extrinsic_pct:
                        rejection_counts["extrinsic_too_high"] += 1
                        if self.verbosity == AnalysisVerbosity.DEBUG:
                            self.logger.debug(f"LEAPS {contract.strike} rejected: extrinsic value {extrinsic_value:.2f} is {extrinsic_pct*100:.1f}% of option price {mid_price:.2f} (max: {criteria.max_extrinsic_pct*100:.0f}%)")
                        continue
            
            candidates.append(contract)
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"LEAPS candidate: {contract.strike} delta={contract.delta} DTE={contract.dte}")
        
        # Sort by delta (prefer higher delta for LEAPS)
        candidates.sort(key=lambda x: x.delta or Decimal('0'), reverse=True)
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG] and rejection_counts:
            rejection_summary = ", ".join(f"{reason}: {count}" for reason, count in rejection_counts.items())
            self.logger.info(f"LEAPS filtering: {len(candidates)} candidates from {len(calls)} calls. Rejections: {rejection_summary}")
        
        # Always print summary for debugging
        print(f"   📊 LEAPS filtering summary:")
        print(f"      Total calls evaluated: {len(calls)}")
        print(f"      Candidates found: {len(candidates)}")
        if rejection_counts:
            print(f"      Rejections by reason:")
            for reason, count in rejection_counts.items():
                print(f"         - {reason}: {count}")
        
        print(f"   ✅ LEAPS filter found {len(candidates)} candidates (returning top 10)")
        return candidates[:10]  # Return top 10 candidates
    
    def _filter_short_contracts(self, option_chain: OptionChain,
                               criteria: ShortCallCriteria,
                               quote: StockQuote) -> List[OptionContract]:
        """Filter option chain for suitable short call contracts with detailed logging."""
        
        # Start with all call contracts
        calls = option_chain.get_calls()
        candidates = []
        rejection_counts = defaultdict(int)
        
        if self.verbosity == AnalysisVerbosity.DEBUG:
            self.logger.debug(f"Filtering {len(calls)} call contracts for short calls (DTE {criteria.min_dte}-{criteria.max_dte})")
        
        for contract in calls:
            # Check days to expiration
            if not contract.dte or contract.dte < criteria.min_dte or contract.dte > criteria.max_dte:
                rejection_counts["dte_out_of_range"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"Short call {contract.strike} rejected: DTE {contract.dte} not in range")
                continue
            
            # Check delta requirements
            if not contract.delta or contract.delta < criteria.min_delta or contract.delta > criteria.max_delta:
                rejection_counts["delta_out_of_range"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"Short call {contract.strike} rejected: delta {contract.delta} not in range")
                continue
            
            # Check liquidity
            if not self._check_contract_liquidity(contract, criteria.min_open_interest,
                                                criteria.min_volume, criteria.max_bid_ask_spread_pct):
                rejection_counts["liquidity_insufficient"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    spread_pct = ((contract.ask - contract.bid) / contract.mid * Decimal('100')) if (contract.bid and contract.ask and contract.mid and contract.mid > 0) else None
                    spread_str = f"{spread_pct:.2f}" if spread_pct else "N/A"
                    self.logger.debug(f"Short call {contract.strike} rejected: liquidity (OI:{contract.open_interest}, Vol:{contract.volume}, Spread:{spread_str}%)")
                continue
            
            # Check moneyness (should be OTM)
            # Calculate moneyness if not set
            if not contract.moneyness and quote.last and contract.strike:
                if quote.last > contract.strike:
                    calculated_moneyness = "ITM"
                elif abs(quote.last - contract.strike) < Decimal('0.50'):
                    calculated_moneyness = "ATM"
                else:
                    calculated_moneyness = "OTM"
            else:
                calculated_moneyness = contract.moneyness
                
            if calculated_moneyness != criteria.moneyness:
                rejection_counts["not_otm"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"Short call {contract.strike} rejected: not OTM (is {calculated_moneyness}, stock=${quote.last}, strike=${contract.strike})")
                continue
            
            # Ensure reasonable pricing
            if not contract.bid or not contract.ask or contract.bid <= 0:
                rejection_counts["invalid_pricing"] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"Short call {contract.strike} rejected: invalid pricing (bid:{contract.bid}, ask:{contract.ask})")
                continue
            
            candidates.append(contract)
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"Short call candidate: {contract.strike} delta={contract.delta} DTE={contract.dte} premium={contract.bid}")
        
        # Sort by premium collected (higher is better for shorts)
        candidates.sort(key=lambda x: x.bid or Decimal('0'), reverse=True)
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG] and rejection_counts:
            rejection_summary = ", ".join(f"{reason}: {count}" for reason, count in rejection_counts.items())
            self.logger.info(f"Short call filtering: {len(candidates)} candidates from {len(calls)} calls. Rejections: {rejection_summary}")
        
        # Always print summary for debugging
        if rejection_counts:
            print(f"       → Short calls rejected: {', '.join(f'{reason}={count}' for reason, count in rejection_counts.items())}")
        
        return candidates[:20]  # Return top 20 candidates
    
    def _check_contract_liquidity(self, contract: OptionContract,
                                 min_oi: int, min_volume: int,
                                 max_spread_pct: Decimal) -> bool:
        """Check if contract meets liquidity requirements."""
        
        # Check open interest
        if min_oi > 0:  # Only check if requirement is set
            if not contract.open_interest or contract.open_interest < min_oi:
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"  Liquidity check failed: OI={contract.open_interest} < {min_oi}")
                return False
        
        # Check volume (if min_volume > 0)
        if min_volume > 0:
            if not contract.volume or contract.volume < min_volume:
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"  Liquidity check failed: Volume={contract.volume} < {min_volume}")
                return False
        
        # Check bid-ask spread (if max_spread_pct > 0)
        if max_spread_pct > 0 and contract.bid and contract.ask:
            # Use mid price if available, otherwise calculate it
            mid_price = contract.mid if contract.mid else (contract.bid + contract.ask) / Decimal('2')
            if mid_price > 0:
                spread_pct = (contract.ask - contract.bid) / mid_price * Decimal('100')
                if spread_pct > max_spread_pct * Decimal('100'):
                    if self.verbosity == AnalysisVerbosity.DEBUG:
                        self.logger.debug(f"  Liquidity check failed: Spread={spread_pct:.2f}% > {max_spread_pct * 100:.0f}%")
                    return False
        
        return True
    
    def _is_valid_pmcc_combination(self, leaps: OptionContract,
                                  short: OptionContract,
                                  quote: StockQuote) -> bool:
        """Check if LEAPS and short call form a valid PMCC with detailed logging."""
        
        # Short call strike must be higher than LEAPS strike
        if short.strike <= leaps.strike:
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Short strike not higher than LEAPS strike")
            return False
        
        # Short call must expire before LEAPS
        if short.dte and leaps.dte and short.dte >= leaps.dte:
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Short expires after LEAPS ({short.dte} >= {leaps.dte})")
            return False
        
        # Short call strike should be above current price (OTM)
        if quote.last and short.strike <= quote.last:
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Short strike {short.strike} not OTM (current: {quote.last})")
            return False
        
        # Check that we can collect enough premium to make it worthwhile
        if not leaps.ask or not short.bid:
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Missing pricing data (LEAPS ask: {leaps.ask}, short bid: {short.bid})")
            return False
        
        net_debit = leaps.ask - short.bid
        if net_debit <= 0:  # Should not be a net credit
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Net credit position ({net_debit})")
            return False
        
        # Ensure the position has reasonable profit potential
        strike_width = short.strike - leaps.strike
        max_profit = strike_width - net_debit
        
        if max_profit <= 0:
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: No profit potential (max profit: {max_profit})")
            return False
        
        # Risk-reward should be reasonable (at least 1:3 risk:reward)
        risk_reward_ratio = max_profit / net_debit
        if risk_reward_ratio < Decimal('0.33'):
            if self.verbosity == AnalysisVerbosity.DEBUG:
                self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Poor risk/reward ratio ({risk_reward_ratio:.2f})")
            return False
        
        if self.verbosity == AnalysisVerbosity.DEBUG:
            self.logger.debug(f"PMCC {leaps.strike}/{short.strike}: Valid combination (net_debit: {net_debit}, max_profit: {max_profit}, RR: {risk_reward_ratio:.2f})")
        
        return True
    
    def _analyze_pmcc_combination(self, leaps: OptionContract,
                                 short: OptionContract,
                                 quote: StockQuote) -> Optional[PMCCOpportunity]:
        """Analyze a specific PMCC combination."""
        
        try:
            # Calculate position metrics
            net_debit = leaps.ask - short.bid
            strike_width = short.strike - leaps.strike
            max_profit = strike_width - net_debit
            max_loss = net_debit
            breakeven = leaps.strike + net_debit
            
            # Calculate ROI potential
            roi_potential = (max_profit / net_debit) * 100
            
            # Calculate risk-reward ratio
            risk_reward_ratio = max_profit / max_loss
            
            # Calculate probability score
            probability_score = self._calculate_probability_score(
                leaps, short, quote, breakeven
            )
            
            # Calculate liquidity score
            liquidity_score = self._calculate_liquidity_score(leaps, short)
            
            # Calculate total score
            total_score = self._calculate_total_score(
                roi_potential, risk_reward_ratio, probability_score, liquidity_score
            )
            
            return PMCCOpportunity(
                leaps_contract=leaps,
                short_contract=short,
                underlying_quote=quote,
                net_debit=net_debit,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven=breakeven,
                roi_potential=roi_potential,
                risk_reward_ratio=risk_reward_ratio,
                probability_score=probability_score,
                liquidity_score=liquidity_score,
                total_score=total_score,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing PMCC combination: {e}")
            return None
    
    def _calculate_probability_score(self, leaps: OptionContract,
                                   short: OptionContract,
                                   quote: StockQuote,
                                   breakeven: Decimal) -> Decimal:
        """Calculate probability score based on various factors."""
        
        score = Decimal('50')  # Base score
        
        # Factor 1: Distance to breakeven (closer is better)
        if quote.last and breakeven:
            distance_pct = abs(quote.last - breakeven) / quote.last * 100
            if distance_pct <= 5:
                score += Decimal('20')
            elif distance_pct <= 10:
                score += Decimal('10')
            elif distance_pct >= 20:
                score -= Decimal('10')
        
        # Factor 2: Time to short expiration (more time is better)
        if short.dte:
            if short.dte >= 35:
                score += Decimal('15')
            elif short.dte >= 28:
                score += Decimal('10')
            elif short.dte <= 14:
                score -= Decimal('10')
        
        # Factor 3: Delta relationship
        if leaps.delta and short.delta:
            delta_ratio = short.delta / leaps.delta
            # Prefer ratio around 0.3-0.4 (short delta / long delta)
            if Decimal('0.25') <= delta_ratio <= Decimal('0.45'):
                score += Decimal('15')
            elif Decimal('0.15') <= delta_ratio <= Decimal('0.55'):
                score += Decimal('5')
        
        return max(Decimal('0'), min(Decimal('100'), score))
    
    def _calculate_liquidity_score(self, leaps: OptionContract,
                                  short: OptionContract) -> Decimal:
        """Calculate liquidity score for the PMCC combination."""
        
        score = Decimal('0')
        factors = 0
        
        # LEAPS liquidity (60% weight)
        if leaps.bid and leaps.ask and leaps.mid and leaps.mid > 0:
            spread_pct = (leaps.ask - leaps.bid) / leaps.mid * 100
            leaps_score = max(0, 100 - spread_pct * 5)  # Each 1% spread reduces by 5 points
            score += Decimal(str(leaps_score)) * Decimal('0.6')
            factors += 1
        
        # Short call liquidity (40% weight)
        if short.bid and short.ask and short.mid and short.mid > 0:
            spread_pct = (short.ask - short.bid) / short.mid * 100
            short_score = max(0, 100 - spread_pct * 3)  # Less penalty for short spreads
            score += Decimal(str(short_score)) * Decimal('0.4')
            factors += 1
        
        # Adjust for volume and open interest
        if leaps.volume and short.volume:
            total_volume = leaps.volume + short.volume
            if total_volume >= 50:
                score += Decimal('10')
            elif total_volume >= 20:
                score += Decimal('5')
        
        if leaps.open_interest and short.open_interest:
            total_oi = leaps.open_interest + short.open_interest
            if total_oi >= 100:
                score += Decimal('10')
            elif total_oi >= 50:
                score += Decimal('5')
        
        return max(Decimal('0'), min(Decimal('100'), score))
    
    def _calculate_total_score(self, roi_potential: Decimal,
                              risk_reward_ratio: Decimal,
                              probability_score: Decimal,
                              liquidity_score: Decimal) -> Decimal:
        """Calculate total weighted score for the opportunity."""
        
        # ROI component (25% weight) - normalize to 0-100 scale
        roi_score = min(100, max(0, roi_potential))  # Cap at 100%
        
        # Risk-reward component (25% weight) - normalize to 0-100 scale
        rr_score = min(100, risk_reward_ratio * 50)  # 2:1 ratio = 100 points
        
        # Probability component (30% weight) - already 0-100
        prob_score = probability_score
        
        # Liquidity component (20% weight) - already 0-100
        liq_score = liquidity_score
        
        total = (
            roi_score * Decimal('0.25') +
            rr_score * Decimal('0.25') + 
            prob_score * Decimal('0.30') +
            liq_score * Decimal('0.20')
        )
        
        return max(Decimal('0'), min(Decimal('100'), total))
    
    def _log_no_opportunities_summary(self, symbol: str, leaps_candidates: List[OptionContract],
                                     short_candidates: List[OptionContract], option_chain: OptionChain,
                                     leaps_criteria: LEAPSCriteria, short_criteria: ShortCallCriteria) -> None:
        """Log a summary of why no PMCC opportunities were found."""
        summary_parts = [f"No PMCC opportunities found for {symbol}."]
        
        # Check if we have any options at all
        if not option_chain or not option_chain.contracts:
            summary_parts.append("Reason: No options data available")
        else:
            total_calls = len(option_chain.get_calls())
            summary_parts.append(f"Total call options: {total_calls}")
            
            # LEAPS analysis
            if len(leaps_candidates) == 0:
                leaps_in_dte_range = sum(1 for c in option_chain.get_calls() 
                                       if c.dte and leaps_criteria.min_dte <= c.dte <= leaps_criteria.max_dte)
                summary_parts.append(f"LEAPS candidates: 0 (found {leaps_in_dte_range} options in DTE range {leaps_criteria.min_dte}-{leaps_criteria.max_dte})")
                
                if leaps_in_dte_range > 0:
                    summary_parts.append(f"  - Check: Min OI={leaps_criteria.min_open_interest}, "
                                       f"Max spread={leaps_criteria.max_bid_ask_spread_pct*100:.0f}%, "
                                       f"Delta range={leaps_criteria.min_delta}-{leaps_criteria.max_delta}")
            else:
                summary_parts.append(f"LEAPS candidates: {len(leaps_candidates)}")
            
            # Short call analysis
            if len(short_candidates) == 0:
                short_in_dte_range = sum(1 for c in option_chain.get_calls()
                                       if c.dte and short_criteria.min_dte <= c.dte <= short_criteria.max_dte)
                summary_parts.append(f"Short call candidates: 0 (found {short_in_dte_range} options in DTE range {short_criteria.min_dte}-{short_criteria.max_dte})")
                
                if short_in_dte_range > 0:
                    summary_parts.append(f"  - Check: Min OI={short_criteria.min_open_interest}, "
                                       f"Min volume={short_criteria.min_volume}, "
                                       f"Max spread={short_criteria.max_bid_ask_spread_pct*100:.0f}%")
            else:
                summary_parts.append(f"Short call candidates: {len(short_candidates)}")
            
            # If we have both but no valid combinations
            if len(leaps_candidates) > 0 and len(short_candidates) > 0:
                summary_parts.append("Reason: No valid PMCC combinations found (check strike relationships and premium coverage)")
        
        # Log the complete summary
        summary_message = " ".join(summary_parts)
        self.logger.info(summary_message)
        
        # Also print to console for visibility
        if self.verbosity != AnalysisVerbosity.QUIET:
            print(f"   ℹ️  {summary_message}")
    
    def get_pmcc_analysis(self, leaps: OptionContract, short: OptionContract,
                         quote: StockQuote) -> Optional[PMCCAnalysis]:
        """Create PMCCAnalysis object from contracts."""
        
        if not self._is_valid_pmcc_combination(leaps, short, quote):
            return None
        
        net_debit = leaps.ask - short.bid
        
        analysis = PMCCAnalysis(
            long_call=leaps,
            short_call=short,
            underlying=quote,
            net_debit=net_debit,
            credit_received=short.bid,
            analyzed_at=datetime.now()
        )
        
        # Calculate risk metrics
        try:
            analysis.risk_metrics = analysis.calculate_risk_metrics()
            analysis.liquidity_score = analysis.calculate_liquidity_score()
        except Exception as e:
            self.logger.error(f"Error calculating analysis metrics: {e}")
        
        return analysis