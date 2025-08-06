"""
PMCC Analysis Reporter for detailed quantitative analysis and feasibility reporting.

Provides comprehensive analysis summaries, market condition context, and detailed
logging for PMCC option screening to help users understand why stocks pass or fail.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from enum import Enum
import statistics
from collections import defaultdict, Counter

try:
    from src.models.api_models import OptionChain, OptionContract, StockQuote
    from src.config.settings import AnalysisVerbosity
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.api_models import OptionChain, OptionContract, StockQuote
    from config.settings import AnalysisVerbosity


@dataclass
class OptionMetrics:
    """Statistical metrics for option contracts."""
    count: int = 0
    strike_range: Tuple[Optional[Decimal], Optional[Decimal]] = (None, None)
    delta_range: Tuple[Optional[Decimal], Optional[Decimal]] = (None, None)
    dte_range: Tuple[Optional[int], Optional[int]] = (None, None)
    avg_bid_ask_spread_pct: Optional[Decimal] = None
    avg_volume: Optional[float] = None
    avg_open_interest: Optional[float] = None
    total_volume: int = 0
    total_open_interest: int = 0


@dataclass
class LiquidityAnalysis:
    """Liquidity analysis for option contracts."""
    contracts_with_volume: int = 0
    contracts_with_oi: int = 0
    tight_spreads_count: int = 0  # < 5% spread
    wide_spreads_count: int = 0   # > 10% spread
    avg_spread_pct: Optional[Decimal] = None
    median_volume: Optional[float] = None
    median_open_interest: Optional[float] = None


@dataclass
class PMCCFeasibilityReport:
    """Comprehensive PMCC feasibility report for a single stock."""
    symbol: str
    analysis_timestamp: datetime
    current_price: Optional[Decimal]
    market_cap: Optional[Decimal] = None
    avg_volume: Optional[int] = None
    
    # Option chain overview
    total_contracts: int = 0
    total_calls: int = 0
    total_puts: int = 0
    unique_expirations: int = 0
    unique_strikes: int = 0
    
    # LEAPS analysis
    leaps_metrics: OptionMetrics = field(default_factory=OptionMetrics)
    leaps_liquidity: LiquidityAnalysis = field(default_factory=LiquidityAnalysis)
    leaps_candidates_found: int = 0
    leaps_failure_reasons: Dict[str, int] = field(default_factory=dict)
    
    # Short call analysis
    short_metrics: OptionMetrics = field(default_factory=OptionMetrics)
    short_liquidity: LiquidityAnalysis = field(default_factory=LiquidityAnalysis)
    short_candidates_found: int = 0
    short_failure_reasons: Dict[str, int] = field(default_factory=dict)
    
    # PMCC combination analysis
    valid_combinations: int = 0
    total_combinations_tested: int = 0
    combination_failure_reasons: Dict[str, int] = field(default_factory=dict)
    
    # Market conditions
    implied_volatility_context: Optional[str] = None
    options_pricing_context: Optional[str] = None
    market_structure_issues: List[str] = field(default_factory=list)
    
    # Final assessment
    is_pmcc_feasible: bool = False
    primary_blocking_factor: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


class PMCCAnalysisReporter:
    """Comprehensive PMCC analysis reporter with quantitative insights."""
    
    def __init__(self, verbosity: AnalysisVerbosity = AnalysisVerbosity.NORMAL):
        """
        Initialize the analysis reporter.
        
        Args:
            verbosity: Analysis verbosity level
        """
        self.verbosity = verbosity
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_option_chain_comprehensive(
        self, 
        symbol: str,
        option_chain: OptionChain,
        quote: StockQuote,
        leaps_criteria: Any,
        short_criteria: Any
    ) -> PMCCFeasibilityReport:
        """
        Perform comprehensive analysis of option chain for PMCC feasibility.
        
        Args:
            symbol: Stock symbol
            option_chain: Option chain data
            quote: Current stock quote
            leaps_criteria: LEAPS selection criteria
            short_criteria: Short call selection criteria
            
        Returns:
            Detailed feasibility report
        """
        report = PMCCFeasibilityReport(
            symbol=symbol,
            analysis_timestamp=datetime.now(),
            current_price=quote.last or quote.mid
        )
        
        # Basic option chain metrics
        all_contracts = option_chain.contracts
        calls = option_chain.get_calls()
        puts = option_chain.get_puts()
        
        report.total_contracts = len(all_contracts)
        report.total_calls = len(calls)
        report.total_puts = len(puts)
        report.unique_expirations = len(set(c.expiration for c in all_contracts if c.expiration))
        report.unique_strikes = len(set(c.strike for c in all_contracts if c.strike))
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
            self.logger.info(f"{symbol} option chain overview: {report.total_contracts} total contracts, "
                           f"{report.total_calls} calls, {report.unique_expirations} expirations, "
                           f"{report.unique_strikes} strikes")
        
        # Analyze LEAPS options
        leaps_candidates, leaps_contracts_in_range = self._analyze_leaps_options(
            calls, leaps_criteria, quote, report
        )
        
        # Analyze short call options
        short_candidates, short_contracts_in_range = self._analyze_short_call_options(
            calls, short_criteria, quote, report
        )
        
        # Analyze PMCC combinations if both LEAPS and short calls exist
        if leaps_candidates and short_candidates:
            self._analyze_pmcc_combinations(
                leaps_candidates, short_candidates, quote, report
            )
        
        # Assess market conditions and provide recommendations
        self._assess_market_conditions(symbol, option_chain, quote, report)
        self._generate_recommendations(report)
        
        # Log summary based on verbosity
        self._log_feasibility_summary(report)
        
        return report
    
    def _analyze_leaps_options(
        self, 
        calls: List[OptionContract], 
        criteria: Any, 
        quote: StockQuote,
        report: PMCCFeasibilityReport
    ) -> Tuple[List[OptionContract], List[OptionContract]]:
        """Analyze LEAPS options and populate report metrics."""
        
        # Find contracts in LEAPS DTE range
        leaps_range_contracts = [
            c for c in calls 
            if c.dte and criteria.min_dte <= c.dte <= criteria.max_dte
        ]
        
        if not leaps_range_contracts:
            report.leaps_failure_reasons["no_contracts_in_dte_range"] = len(calls)
            if self.verbosity != AnalysisVerbosity.QUIET:
                self.logger.info(f"{report.symbol} has no LEAPS contracts "
                               f"({criteria.min_dte}-{criteria.max_dte} DTE)")
            return [], []
        
        # Calculate LEAPS metrics
        report.leaps_metrics = self._calculate_option_metrics(leaps_range_contracts)
        report.leaps_liquidity = self._calculate_liquidity_metrics(leaps_range_contracts)
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
            self.logger.info(f"{report.symbol} LEAPS analysis: {len(leaps_range_contracts)} contracts "
                           f"in DTE range, delta range {report.leaps_metrics.delta_range}, "
                           f"avg spread {report.leaps_liquidity.avg_spread_pct}%")
        
        # Filter LEAPS candidates and track failure reasons
        candidates = []
        failure_counts = defaultdict(int)
        
        for contract in leaps_range_contracts:
            failure_reason = self._check_leaps_contract(contract, criteria, quote)
            if failure_reason:
                failure_counts[failure_reason] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"{report.symbol} LEAPS {contract.strike} "
                                    f"{contract.expiration}: {failure_reason}")
            else:
                candidates.append(contract)
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"{report.symbol} LEAPS candidate: "
                                    f"{contract.strike} delta={contract.delta}")
        
        report.leaps_candidates_found = len(candidates)
        report.leaps_failure_reasons = dict(failure_counts)
        
        return candidates, leaps_range_contracts
    
    def _analyze_short_call_options(
        self, 
        calls: List[OptionContract], 
        criteria: Any, 
        quote: StockQuote,
        report: PMCCFeasibilityReport
    ) -> Tuple[List[OptionContract], List[OptionContract]]:
        """Analyze short call options and populate report metrics."""
        
        # Find contracts in short call DTE range
        short_range_contracts = [
            c for c in calls 
            if c.dte and criteria.min_dte <= c.dte <= criteria.max_dte
        ]
        
        if not short_range_contracts:
            report.short_failure_reasons["no_contracts_in_dte_range"] = len(calls)
            if self.verbosity != AnalysisVerbosity.QUIET:
                self.logger.info(f"{report.symbol} has no short call contracts "
                               f"({criteria.min_dte}-{criteria.max_dte} DTE)")
            return [], []
        
        # Calculate short call metrics
        report.short_metrics = self._calculate_option_metrics(short_range_contracts)
        report.short_liquidity = self._calculate_liquidity_metrics(short_range_contracts)
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
            self.logger.info(f"{report.symbol} short call analysis: {len(short_range_contracts)} contracts "
                           f"in DTE range, delta range {report.short_metrics.delta_range}, "
                           f"avg spread {report.short_liquidity.avg_spread_pct}%")
        
        # Filter short call candidates and track failure reasons
        candidates = []
        failure_counts = defaultdict(int)
        
        for contract in short_range_contracts:
            failure_reason = self._check_short_call_contract(contract, criteria, quote)
            if failure_reason:
                failure_counts[failure_reason] += 1
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"{report.symbol} short call {contract.strike} "
                                    f"{contract.expiration}: {failure_reason}")
            else:
                candidates.append(contract)
                if self.verbosity == AnalysisVerbosity.DEBUG:
                    self.logger.debug(f"{report.symbol} short call candidate: "
                                    f"{contract.strike} delta={contract.delta}")
        
        report.short_candidates_found = len(candidates)
        report.short_failure_reasons = dict(failure_counts)
        
        return candidates, short_range_contracts
    
    def _analyze_pmcc_combinations(
        self,
        leaps_candidates: List[OptionContract],
        short_candidates: List[OptionContract],
        quote: StockQuote,
        report: PMCCFeasibilityReport
    ) -> None:
        """Analyze PMCC combinations and track failure reasons."""
        
        total_combinations = len(leaps_candidates) * len(short_candidates)
        report.total_combinations_tested = total_combinations
        
        valid_combinations = 0
        failure_counts = defaultdict(int)
        
        for leaps in leaps_candidates:
            for short in short_candidates:
                failure_reason = self._check_pmcc_combination(leaps, short, quote)
                if failure_reason:
                    failure_counts[failure_reason] += 1
                    if self.verbosity == AnalysisVerbosity.DEBUG:
                        self.logger.debug(f"{report.symbol} PMCC {leaps.strike}/{short.strike}: "
                                        f"{failure_reason}")
                else:
                    valid_combinations += 1
                    if self.verbosity == AnalysisVerbosity.DEBUG:
                        net_debit = leaps.ask - short.bid if leaps.ask and short.bid else None
                        self.logger.debug(f"{report.symbol} valid PMCC: "
                                        f"{leaps.strike}/{short.strike} "
                                        f"net_debit={net_debit}")
        
        report.valid_combinations = valid_combinations
        report.combination_failure_reasons = dict(failure_counts)
        
        if self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
            self.logger.info(f"{report.symbol} PMCC combinations: {valid_combinations}/{total_combinations} valid")
    
    def _calculate_option_metrics(self, contracts: List[OptionContract]) -> OptionMetrics:
        """Calculate statistical metrics for option contracts."""
        if not contracts:
            return OptionMetrics()
        
        strikes = [c.strike for c in contracts if c.strike]
        deltas = [c.delta for c in contracts if c.delta]
        dtes = [c.dte for c in contracts if c.dte]
        volumes = [c.volume for c in contracts if c.volume and c.volume is not None]
        open_interests = [c.open_interest for c in contracts if c.open_interest and c.open_interest is not None]
        
        # Calculate bid-ask spreads
        spreads = []
        for c in contracts:
            if c.bid and c.ask and c.mid and c.mid > 0:
                spread_pct = (c.ask - c.bid) / c.mid * 100
                spreads.append(spread_pct)
        
        return OptionMetrics(
            count=len(contracts),
            strike_range=(min(strikes), max(strikes)) if strikes else (None, None),
            delta_range=(min(deltas), max(deltas)) if deltas else (None, None),
            dte_range=(min(dtes), max(dtes)) if dtes else (None, None),
            avg_bid_ask_spread_pct=Decimal(str(statistics.mean(spreads))) if spreads else None,
            avg_volume=statistics.mean(volumes) if volumes else None,
            avg_open_interest=statistics.mean(open_interests) if open_interests else None,
            total_volume=sum(volumes) if volumes else 0,
            total_open_interest=sum(open_interests) if open_interests else 0
        )
    
    def _calculate_liquidity_metrics(self, contracts: List[OptionContract]) -> LiquidityAnalysis:
        """Calculate liquidity analysis for option contracts."""
        if not contracts:
            return LiquidityAnalysis()
        
        contracts_with_volume = sum(1 for c in contracts if c.volume is not None and c.volume > 0)
        contracts_with_oi = sum(1 for c in contracts if c.open_interest is not None and c.open_interest > 0)
        
        spreads = []
        tight_spreads = 0
        wide_spreads = 0
        
        for c in contracts:
            if c.bid and c.ask and c.mid and c.mid > 0:
                spread_pct = (c.ask - c.bid) / c.mid * 100
                spreads.append(spread_pct)
                
                if spread_pct < 5:
                    tight_spreads += 1
                elif spread_pct > 10:
                    wide_spreads += 1
        
        volumes = [c.volume for c in contracts if c.volume is not None and c.volume > 0]
        open_interests = [c.open_interest for c in contracts if c.open_interest is not None and c.open_interest > 0]
        
        return LiquidityAnalysis(
            contracts_with_volume=contracts_with_volume,
            contracts_with_oi=contracts_with_oi,
            tight_spreads_count=tight_spreads,
            wide_spreads_count=wide_spreads,
            avg_spread_pct=Decimal(str(statistics.mean(spreads))) if spreads else None,
            median_volume=statistics.median(volumes) if volumes else None,
            median_open_interest=statistics.median(open_interests) if open_interests else None
        )
    
    def _check_leaps_contract(self, contract: OptionContract, criteria: Any, quote: StockQuote) -> Optional[str]:
        """Check if a LEAPS contract meets criteria and return failure reason if not."""
        
        # Delta requirements
        if not contract.delta or contract.delta < criteria.min_delta:
            return f"delta_too_low_{contract.delta}"
        if contract.delta > criteria.max_delta:
            return f"delta_too_high_{contract.delta}"
        
        # Moneyness check
        if not contract.moneyness or contract.moneyness != criteria.moneyness:
            criteria_moneyness_str = criteria.moneyness.lower() if criteria.moneyness else 'unknown'
            return f"not_{criteria_moneyness_str}"
        
        # Liquidity checks
        if contract.open_interest and contract.open_interest < criteria.min_open_interest:
            return f"low_open_interest_{contract.open_interest}"
        
        if criteria.min_volume > 0 and (not contract.volume or contract.volume < criteria.min_volume):
            return f"low_volume_{contract.volume or 0}"
        
        # Bid-ask spread check
        if contract.bid and contract.ask and contract.mid and contract.mid > 0:
            spread_pct = (contract.ask - contract.bid) / contract.mid * 100
            if spread_pct > criteria.max_bid_ask_spread_pct:
                return f"wide_spread_{spread_pct:.1f}pct"
        
        # Pricing validity
        if not contract.bid or not contract.ask or contract.bid <= 0:
            return "invalid_pricing"
        
        return None
    
    def _check_short_call_contract(self, contract: OptionContract, criteria: Any, quote: StockQuote) -> Optional[str]:
        """Check if a short call contract meets criteria and return failure reason if not."""
        
        # Delta requirements
        if not contract.delta or contract.delta < criteria.min_delta:
            return f"delta_too_low_{contract.delta}"
        if contract.delta > criteria.max_delta:
            return f"delta_too_high_{contract.delta}"
        
        # Moneyness check
        if not contract.moneyness or contract.moneyness != criteria.moneyness:
            criteria_moneyness_str = criteria.moneyness.lower() if criteria.moneyness else 'unknown'
            return f"not_{criteria_moneyness_str}"
        
        # Liquidity checks
        if contract.open_interest and contract.open_interest < criteria.min_open_interest:
            return f"low_open_interest_{contract.open_interest}"
        
        # Bid-ask spread check
        if contract.bid and contract.ask and contract.mid and contract.mid > 0:
            spread_pct = (contract.ask - contract.bid) / contract.mid * 100
            if spread_pct > criteria.max_bid_ask_spread_pct:
                return f"wide_spread_{spread_pct:.1f}pct"
        
        # Pricing validity
        if not contract.bid or not contract.ask or contract.bid <= 0:
            return "invalid_pricing"
        
        return None
    
    def _check_pmcc_combination(self, leaps: OptionContract, short: OptionContract, quote: StockQuote) -> Optional[str]:
        """Check if LEAPS and short call form a valid PMCC combination."""
        
        # Short call strike must be higher than LEAPS strike
        if short.strike <= leaps.strike:
            return f"short_strike_not_higher_{short.strike}_vs_{leaps.strike}"
        
        # Short call must expire before LEAPS
        if short.dte and leaps.dte and short.dte >= leaps.dte:
            return f"short_expires_after_leaps_{short.dte}_vs_{leaps.dte}"
        
        # Short call strike should be above current price (OTM)
        if quote.last and short.strike <= quote.last:
            return f"short_not_otm_{short.strike}_vs_{quote.last}"
        
        # Check that we can collect enough premium to make it worthwhile
        if not leaps.ask or not short.bid:
            return "missing_pricing_data"
        
        net_debit = leaps.ask - short.bid
        if net_debit <= 0:
            return f"net_credit_position_{net_debit}"
        
        # Ensure the position has reasonable profit potential
        strike_width = short.strike - leaps.strike
        max_profit = strike_width - net_debit
        
        if max_profit <= 0:
            return f"no_profit_potential_{max_profit}"
        
        # Risk-reward should be reasonable (at least 1:3 risk:reward)
        if max_profit / net_debit < Decimal('0.33'):
            return f"poor_risk_reward_{max_profit / net_debit:.2f}"
        
        return None
    
    def _assess_market_conditions(
        self, 
        symbol: str, 
        option_chain: OptionChain, 
        quote: StockQuote, 
        report: PMCCFeasibilityReport
    ) -> None:
        """Assess market conditions that might affect PMCC feasibility."""
        
        all_contracts = option_chain.contracts
        
        # Analyze implied volatility context
        ivs = [c.implied_volatility for c in all_contracts if hasattr(c, 'implied_volatility') and c.implied_volatility]
        if ivs:
            avg_iv = statistics.mean(ivs)
            if avg_iv < 0.15:  # 15%
                report.implied_volatility_context = "low_iv_environment"
                report.market_structure_issues.append("Low implied volatility may limit PMCC profitability")
            elif avg_iv > 0.40:  # 40%
                report.implied_volatility_context = "high_iv_environment"
                report.market_structure_issues.append("High implied volatility increases option costs")
            else:
                report.implied_volatility_context = "normal_iv_environment"
        
        # Analyze options pricing context
        all_spreads = []
        for c in all_contracts:
            if c.bid and c.ask and c.mid and c.mid > 0:
                spread_pct = (c.ask - c.bid) / c.mid * 100
                all_spreads.append(spread_pct)
        
        if all_spreads:
            avg_spread = statistics.mean(all_spreads)
            if avg_spread > 15:
                report.options_pricing_context = "wide_spreads"
                report.market_structure_issues.append(f"Wide bid-ask spreads ({avg_spread:.1f}% avg) indicate poor liquidity")
            elif avg_spread < 3:
                report.options_pricing_context = "tight_spreads"
            else:
                report.options_pricing_context = "normal_spreads"
        
        # Check for irregular option chains
        expirations = [c.expiration for c in all_contracts if c.expiration]
        strikes = [c.strike for c in all_contracts if c.strike]
        
        if len(set(expirations)) < 4:
            report.market_structure_issues.append("Limited expiration dates available")
        
        if len(set(strikes)) < 10:
            report.market_structure_issues.append("Limited strike price range")
        
        # Check volume patterns
        total_volume = sum(c.volume for c in all_contracts if c.volume and c.volume is not None)
        if total_volume < 100:
            report.market_structure_issues.append("Very low options volume suggests illiquid market")
    
    def _generate_recommendations(self, report: PMCCFeasibilityReport) -> None:
        """Generate actionable recommendations based on analysis."""
        
        if report.valid_combinations > 0:
            report.is_pmcc_feasible = True
            report.recommendations.append(f"Found {report.valid_combinations} valid PMCC combinations")
            return
        
        # Identify primary blocking factor
        if report.leaps_candidates_found == 0:
            if "no_contracts_in_dte_range" in report.leaps_failure_reasons:
                report.primary_blocking_factor = "no_leaps_available"
                report.recommendations.append("No LEAPS contracts available - consider stocks with longer-dated options")
            else:
                main_leaps_issue = max(report.leaps_failure_reasons.items(), key=lambda x: x[1])[0]
                report.primary_blocking_factor = f"leaps_{main_leaps_issue}"
                
                if "delta_too_low" in main_leaps_issue:
                    report.recommendations.append("LEAPS deltas too low - look for deeper ITM options or consider different underlying")
                elif "low_open_interest" in main_leaps_issue:
                    report.recommendations.append("LEAPS lack sufficient open interest - consider more liquid underlying stocks")
                elif "wide_spread" in main_leaps_issue:
                    report.recommendations.append("LEAPS have wide bid-ask spreads - wait for better liquidity or use limit orders")
        
        elif report.short_candidates_found == 0:
            if "no_contracts_in_dte_range" in report.short_failure_reasons:
                report.primary_blocking_factor = "no_short_calls_available"
                report.recommendations.append("No suitable short call expirations - wait for new expiration cycles")
            else:
                main_short_issue = max(report.short_failure_reasons.items(), key=lambda x: x[1])[0]
                report.primary_blocking_factor = f"short_calls_{main_short_issue}"
                
                if "delta_too_high" in main_short_issue:
                    report.recommendations.append("Short calls too ITM - consider higher strike prices")
                elif "not_otm" in main_short_issue:
                    report.recommendations.append("Short calls not OTM - wait for stock price to decline or use higher strikes")
        
        else:
            # Both LEAPS and short calls available but combinations fail
            main_combo_issue = max(report.combination_failure_reasons.items(), key=lambda x: x[1])[0]
            report.primary_blocking_factor = f"combination_{main_combo_issue}"
            
            if "poor_risk_reward" in main_combo_issue:
                report.recommendations.append("PMCC combinations have poor risk/reward - consider different strike spreads")
            elif "short_not_otm" in main_combo_issue:
                report.recommendations.append("Short strikes not sufficiently OTM - wait for better entry point")
        
        # Add market condition recommendations
        if report.options_pricing_context and "wide_spreads" in report.options_pricing_context:
            report.recommendations.append("Wide spreads detected - use limit orders and consider more liquid alternatives")
        
        if report.implied_volatility_context == "low_iv_environment":
            report.recommendations.append("Low IV environment - PMCC returns may be limited, consider waiting for higher volatility")
        elif report.implied_volatility_context == "high_iv_environment":
            report.recommendations.append("High IV environment - LEAPS are expensive, consider shorter timeframes or wait for IV crush")
    
    def _log_feasibility_summary(self, report: PMCCFeasibilityReport) -> None:
        """Log feasibility summary based on verbosity level."""
        
        if self.verbosity == AnalysisVerbosity.QUIET:
            return
        
        if report.is_pmcc_feasible:
            self.logger.info(f"{report.symbol}: PMCC feasible - {report.valid_combinations} valid combinations found")
        else:
            if self.verbosity == AnalysisVerbosity.NORMAL:
                self.logger.info(f"{report.symbol}: PMCC not feasible - {report.primary_blocking_factor}")
            
            elif self.verbosity in [AnalysisVerbosity.VERBOSE, AnalysisVerbosity.DEBUG]:
                self.logger.info(f"{report.symbol}: PMCC feasibility analysis:")
                self.logger.info(f"  LEAPS: {report.leaps_candidates_found} candidates from {report.leaps_metrics.count} in range")
                self.logger.info(f"  Short calls: {report.short_candidates_found} candidates from {report.short_metrics.count} in range")
                self.logger.info(f"  Combinations: {report.valid_combinations}/{report.total_combinations_tested} valid")
                self.logger.info(f"  Primary issue: {report.primary_blocking_factor}")
                
                if report.recommendations:
                    self.logger.info(f"  Recommendations: {'; '.join(report.recommendations)}")