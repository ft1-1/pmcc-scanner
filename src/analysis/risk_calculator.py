"""
Risk calculator for PMCC positions.

Calculates comprehensive risk metrics including max loss, breakeven points,
probability of profit, early assignment risk, and position sizing recommendations.
"""

import logging
import math
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta

try:
    from src.models.api_models import OptionContract, StockQuote, OptionSide
    from src.models.pmcc_models import PMCCAnalysis, RiskMetrics
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.api_models import OptionContract, StockQuote, OptionSide
    from models.pmcc_models import PMCCAnalysis, RiskMetrics


logger = logging.getLogger(__name__)


@dataclass
class EarlyAssignmentRisk:
    """Early assignment risk assessment."""
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    probability: Optional[Decimal]  # Estimated probability %
    factors: List[str]  # Risk factors
    days_to_dividend: Optional[int] = None
    dividend_amount: Optional[Decimal] = None
    itm_amount: Optional[Decimal] = None  # How much ITM
    
    @property
    def is_high_risk(self) -> bool:
        """Check if early assignment risk is high."""
        return self.risk_level == "HIGH"


@dataclass
class PositionSizing:
    """Position sizing recommendations."""
    max_position_size: int  # Maximum number of contracts
    recommended_size: int  # Recommended number of contracts
    capital_required: Decimal  # Total capital required
    capital_at_risk: Decimal  # Capital at risk (max loss)
    portfolio_percentage: Decimal  # % of portfolio this represents
    margin_required: Optional[Decimal] = None  # If applicable
    
    @property
    def leverage_ratio(self) -> Decimal:
        """Calculate leverage ratio."""
        if self.capital_required > 0:
            return self.capital_at_risk / self.capital_required
        return Decimal('1')


@dataclass
class ScenarioAnalysis:
    """Scenario analysis for different price movements."""
    scenarios: Dict[str, Dict[str, Decimal]]  # scenario_name -> metrics
    best_case: Dict[str, Decimal]
    worst_case: Dict[str, Decimal]
    expected_case: Dict[str, Decimal]
    
    def get_scenario_pnl(self, scenario: str) -> Optional[Decimal]:
        """Get P&L for a specific scenario."""
        return self.scenarios.get(scenario, {}).get('pnl')


@dataclass
class ComprehensiveRisk:
    """Comprehensive risk analysis for PMCC position."""
    basic_metrics: RiskMetrics
    early_assignment: EarlyAssignmentRisk
    position_sizing: PositionSizing
    scenario_analysis: ScenarioAnalysis
    
    # Additional risk metrics
    var_95: Optional[Decimal] = None  # 95% Value at Risk
    expected_shortfall: Optional[Decimal] = None  # Expected tail loss
    sharpe_ratio: Optional[Decimal] = None  # Risk-adjusted return
    
    # Time decay analysis
    theta_decay_rate: Optional[Decimal] = None  # Daily theta decay
    vega_risk: Optional[Decimal] = None  # IV sensitivity
    
    analyzed_at: datetime = datetime.now()


class RiskCalculator:
    """Calculates comprehensive risk metrics for PMCC positions."""
    
    def __init__(self):
        """Initialize risk calculator."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_comprehensive_risk(self, analysis: PMCCAnalysis,
                                   account_size: Optional[Decimal] = None,
                                   risk_free_rate: Decimal = Decimal('0.05'),
                                   dividend_info: Optional[Dict] = None) -> ComprehensiveRisk:
        """
        Calculate comprehensive risk analysis.
        
        Args:
            analysis: PMCC analysis object
            account_size: Total account size for position sizing
            risk_free_rate: Risk-free rate for calculations
            dividend_info: Dividend information for early assignment risk
            
        Returns:
            ComprehensiveRisk object with all risk metrics
        """
        
        # Calculate basic risk metrics if not already done
        if not analysis.risk_metrics:
            analysis.risk_metrics = analysis.calculate_risk_metrics()
        
        basic_metrics = analysis.risk_metrics
        
        # Calculate early assignment risk
        early_assignment = self._calculate_early_assignment_risk(
            analysis, dividend_info
        )
        
        # Calculate position sizing
        position_sizing = self._calculate_position_sizing(
            analysis, account_size
        )
        
        # Perform scenario analysis
        scenario_analysis = self._perform_scenario_analysis(analysis)
        
        # Calculate advanced risk metrics
        var_95 = self._calculate_var_95(scenario_analysis)
        expected_shortfall = self._calculate_expected_shortfall(scenario_analysis)
        sharpe_ratio = self._calculate_sharpe_ratio(analysis, risk_free_rate)
        
        # Calculate Greeks-based risks
        theta_decay_rate = self._calculate_theta_decay_rate(analysis)
        vega_risk = self._calculate_vega_risk(analysis)
        
        return ComprehensiveRisk(
            basic_metrics=basic_metrics,
            early_assignment=early_assignment,
            position_sizing=position_sizing,
            scenario_analysis=scenario_analysis,
            var_95=var_95,
            expected_shortfall=expected_shortfall,
            sharpe_ratio=sharpe_ratio,
            theta_decay_rate=theta_decay_rate,
            vega_risk=vega_risk
        )
    
    def _calculate_early_assignment_risk(self, analysis: PMCCAnalysis,
                                       dividend_info: Optional[Dict] = None) -> EarlyAssignmentRisk:
        """Calculate early assignment risk for the short call."""
        
        risk_factors = []
        risk_level = "LOW"
        probability = Decimal('5')  # Base 5% probability
        
        short_call = analysis.short_call
        current_price = analysis.underlying.last
        
        # Factor 1: How much is the short call ITM?
        itm_amount = None
        if current_price and short_call.strike:
            if current_price > short_call.strike:
                itm_amount = current_price - short_call.strike
                itm_percentage = (itm_amount / short_call.strike) * 100
                
                if itm_percentage > 5:
                    risk_factors.append(f"Short call is {itm_percentage:.1f}% ITM")
                    probability += itm_percentage * 2  # 2% per 1% ITM
                    risk_level = "HIGH" if itm_percentage > 10 else "MEDIUM"
        
        # Factor 2: Time to expiration
        if short_call.dte:
            if short_call.dte <= 7:
                risk_factors.append("Less than 1 week to expiration")
                probability += Decimal('15')
                risk_level = "HIGH" if risk_level != "HIGH" else risk_level
            elif short_call.dte <= 14:
                risk_factors.append("Less than 2 weeks to expiration")
                probability += Decimal('5')
        
        # Factor 3: Dividend risk
        days_to_dividend = None
        dividend_amount = None
        
        if dividend_info:
            ex_dividend_date = dividend_info.get('ex_dividend_date')
            dividend_amount = dividend_info.get('amount')
            
            if ex_dividend_date and isinstance(ex_dividend_date, datetime):
                days_to_dividend = (ex_dividend_date - datetime.now()).days
                
                if 0 <= days_to_dividend <= short_call.dte:
                    # Dividend before expiration
                    if dividend_amount and short_call.extrinsic_value:
                        if dividend_amount > short_call.extrinsic_value:
                            risk_factors.append(
                                f"Dividend (${dividend_amount}) > extrinsic value"
                            )
                            probability += Decimal('25')
                            risk_level = "HIGH"
                        else:
                            risk_factors.append("Dividend before expiration")
                            probability += Decimal('10')
        
        # Factor 4: Liquidity and spread
        if short_call.bid and short_call.ask and short_call.mid:
            spread = short_call.ask - short_call.bid
            spread_pct = (spread / short_call.mid) * 100
            
            if spread_pct > 20:
                risk_factors.append("Wide bid-ask spread may indicate assignment")
                probability += Decimal('5')
        
        # Factor 5: Open interest and volume
        if short_call.open_interest and short_call.open_interest < 10:
            risk_factors.append("Low open interest")
            probability += Decimal('5')
        
        # Cap probability at 90%
        probability = min(probability, Decimal('90'))
        
        # Determine final risk level
        if probability > 50:
            risk_level = "HIGH"
        elif probability > 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return EarlyAssignmentRisk(
            risk_level=risk_level,
            probability=probability,
            factors=risk_factors,
            days_to_dividend=days_to_dividend,
            dividend_amount=dividend_amount,
            itm_amount=itm_amount
        )
    
    def _calculate_position_sizing(self, analysis: PMCCAnalysis,
                                 account_size: Optional[Decimal] = None) -> PositionSizing:
        """Calculate position sizing recommendations."""
        
        net_debit = analysis.net_debit
        max_loss = analysis.risk_metrics.max_loss if analysis.risk_metrics else net_debit
        
        # Default account size if not provided
        if account_size is None:
            account_size = Decimal('100000')  # $100k default
        
        # Risk management rules
        max_risk_per_trade = account_size * Decimal('0.02')  # 2% max risk per trade
        max_capital_per_trade = account_size * Decimal('0.10')  # 10% max capital per trade
        
        # Calculate position sizes
        max_size_by_risk = int(max_risk_per_trade / max_loss)
        max_size_by_capital = int(max_capital_per_trade / net_debit)
        
        max_position_size = min(max_size_by_risk, max_size_by_capital)
        max_position_size = max(1, max_position_size)  # At least 1 contract
        
        # Conservative recommendation (50% of max)
        recommended_size = max(1, max_position_size // 2)
        
        capital_required = net_debit * recommended_size
        capital_at_risk = max_loss * recommended_size
        portfolio_percentage = (capital_required / account_size) * 100
        
        return PositionSizing(
            max_position_size=max_position_size,
            recommended_size=recommended_size,
            capital_required=capital_required,
            capital_at_risk=capital_at_risk,
            portfolio_percentage=portfolio_percentage
        )
    
    def _perform_scenario_analysis(self, analysis: PMCCAnalysis) -> ScenarioAnalysis:
        """Perform scenario analysis for different price movements."""
        
        current_price = analysis.underlying.last
        if not current_price:
            # Return empty scenarios if no current price
            return ScenarioAnalysis(
                scenarios={},
                best_case={},
                worst_case={},
                expected_case={}
            )
        
        scenarios = {}
        
        # Define price scenarios (percentage moves)
        price_scenarios = {
            "crash_20": -20,
            "down_10": -10,
            "down_5": -5,
            "flat": 0,
            "up_5": 5,
            "up_10": 10,
            "up_15": 15,
            "up_20": 20,
            "moon_30": 30
        }
        
        short_dte = analysis.short_call.dte or 30
        
        for scenario_name, move_pct in price_scenarios.items():
            new_price = current_price * (1 + Decimal(str(move_pct)) / 100)
            pnl = self._calculate_pnl_at_expiration(analysis, new_price)
            
            scenarios[scenario_name] = {
                'price': new_price,
                'move_pct': Decimal(str(move_pct)),
                'pnl': pnl,
                'roi': (pnl / analysis.net_debit) * 100 if analysis.net_debit > 0 else Decimal('0')
            }
        
        # Identify best/worst/expected cases
        all_pnls = [s['pnl'] for s in scenarios.values()]
        best_pnl = max(all_pnls)
        worst_pnl = min(all_pnls)
        
        best_case = next(s for s in scenarios.values() if s['pnl'] == best_pnl)
        worst_case = next(s for s in scenarios.values() if s['pnl'] == worst_pnl)
        expected_case = scenarios.get('up_5', scenarios.get('flat', {}))
        
        return ScenarioAnalysis(
            scenarios=scenarios,
            best_case=best_case,
            worst_case=worst_case,
            expected_case=expected_case
        )
    
    def _calculate_pnl_at_expiration(self, analysis: PMCCAnalysis, 
                                   price_at_expiration: Decimal) -> Decimal:
        """Calculate P&L at short call expiration for given stock price."""
        
        long_strike = analysis.long_call.strike
        short_strike = analysis.short_call.strike
        net_debit = analysis.net_debit
        
        # Value of long call at expiration
        long_value = max(Decimal('0'), price_at_expiration - long_strike)
        
        # Value of short call at expiration (our obligation)
        short_obligation = max(Decimal('0'), price_at_expiration - short_strike)
        
        # Net P&L = Long call value - Short call obligation - Net debit paid
        pnl = long_value - short_obligation - net_debit
        
        return pnl
    
    def _calculate_var_95(self, scenario_analysis: ScenarioAnalysis) -> Optional[Decimal]:
        """Calculate 95% Value at Risk."""
        
        if not scenario_analysis.scenarios:
            return None
        
        pnls = [s['pnl'] for s in scenario_analysis.scenarios.values()]
        pnls.sort()
        
        # 95% VaR is the 5th percentile loss
        index = int(len(pnls) * 0.05)
        if index < len(pnls):
            return abs(pnls[index])  # Return as positive loss
        
        return None
    
    def _calculate_expected_shortfall(self, scenario_analysis: ScenarioAnalysis) -> Optional[Decimal]:
        """Calculate expected shortfall (average loss beyond VaR)."""
        
        if not scenario_analysis.scenarios:
            return None
        
        pnls = [s['pnl'] for s in scenario_analysis.scenarios.values()]
        pnls.sort()
        
        # Expected shortfall is average of worst 5% outcomes
        cutoff_index = int(len(pnls) * 0.05)
        if cutoff_index > 0:
            tail_losses = pnls[:cutoff_index]
            return abs(sum(tail_losses) / len(tail_losses))  # Return as positive loss
        
        return None
    
    def _calculate_sharpe_ratio(self, analysis: PMCCAnalysis,
                               risk_free_rate: Decimal) -> Optional[Decimal]:
        """Calculate Sharpe ratio for the PMCC position."""
        
        if not analysis.risk_metrics or not analysis.risk_metrics.max_profit:
            return None
        
        # Estimate expected return (simplified)
        max_profit = analysis.risk_metrics.max_profit
        max_loss = analysis.risk_metrics.max_loss
        
        # Assume 60% probability of profit (rough estimate)
        expected_return = max_profit * Decimal('0.6') + max_loss * Decimal('0.4') * Decimal('-1')
        expected_return_pct = (expected_return / analysis.net_debit) * 100
        
        # Estimate volatility (simplified as half the range)
        volatility = ((max_profit - (-max_loss)) / analysis.net_debit) * 50
        
        if volatility > 0:
            # Annualize assuming 30-45 day holding period
            short_dte = analysis.short_call.dte or 30
            annualization_factor = Decimal('365') / short_dte
            
            annual_return = expected_return_pct * annualization_factor
            annual_vol = volatility * (annualization_factor ** Decimal('0.5'))
            
            risk_free_rate_pct = risk_free_rate * 100
            excess_return = annual_return - risk_free_rate_pct
            
            return excess_return / annual_vol
        
        return None
    
    def _calculate_theta_decay_rate(self, analysis: PMCCAnalysis) -> Optional[Decimal]:
        """Calculate daily theta decay rate."""
        
        if (analysis.long_call.theta is not None and 
            analysis.short_call.theta is not None):
            # Net theta = long theta - short theta (we're short the short call)
            net_theta = analysis.long_call.theta - analysis.short_call.theta
            return net_theta
        
        return None
    
    def _calculate_vega_risk(self, analysis: PMCCAnalysis) -> Optional[Decimal]:
        """Calculate vega risk (sensitivity to IV changes)."""
        
        if (analysis.long_call.vega is not None and 
            analysis.short_call.vega is not None):
            # Net vega = long vega - short vega
            net_vega = analysis.long_call.vega - analysis.short_call.vega
            return abs(net_vega)  # Return absolute risk
        
        return None
    
    def calculate_breakeven_analysis(self, analysis: PMCCAnalysis) -> Dict[str, Decimal]:
        """Calculate multiple breakeven scenarios."""
        
        breakevens = {}
        
        # Static breakeven at expiration
        breakevens['static_breakeven'] = analysis.long_call.strike + analysis.net_debit
        
        # Dynamic breakeven considering time decay
        if analysis.short_call.dte and analysis.short_call.theta:
            days_to_exp = analysis.short_call.dte
            theta_decay = analysis.short_call.theta * days_to_exp
            
            # Breakeven accounting for theta
            breakevens['theta_adjusted_breakeven'] = (
                analysis.long_call.strike + analysis.net_debit - theta_decay
            )
        
        # Profit target breakeven (25% profit)
        profit_target = analysis.net_debit * Decimal('0.25')
        breakevens['profit_target_25pct'] = (
            analysis.long_call.strike + analysis.net_debit + profit_target
        )
        
        return breakevens
    
    def assess_dividend_impact(self, analysis: PMCCAnalysis,
                              dividend_info: Dict) -> Dict[str, Any]:
        """Assess impact of upcoming dividends on the position."""
        
        impact_analysis = {
            'has_dividend_risk': False,
            'dividend_amount': None,
            'ex_dividend_date': None,
            'days_to_ex_dividend': None,
            'early_assignment_likely': False,
            'recommendations': []
        }
        
        if not dividend_info:
            return impact_analysis
        
        ex_div_date = dividend_info.get('ex_dividend_date')
        dividend_amount = dividend_info.get('amount')
        
        if not ex_div_date or not dividend_amount:
            return impact_analysis
        
        impact_analysis['dividend_amount'] = dividend_amount
        impact_analysis['ex_dividend_date'] = ex_div_date
        
        if isinstance(ex_div_date, datetime):
            days_to_ex_div = (ex_div_date - datetime.now()).days
            impact_analysis['days_to_ex_dividend'] = days_to_ex_div
            
            # Check if dividend is before short call expiration
            short_dte = analysis.short_call.dte or 0
            if 0 <= days_to_ex_div <= short_dte:
                impact_analysis['has_dividend_risk'] = True
                
                # Check if early assignment is likely
                current_price = analysis.underlying.last
                short_strike = analysis.short_call.strike
                
                if (current_price and short_strike and 
                    current_price > short_strike):
                    
                    # ITM short call with dividend
                    extrinsic_value = analysis.short_call.extrinsic_value or Decimal('0')
                    
                    if dividend_amount > extrinsic_value:
                        impact_analysis['early_assignment_likely'] = True
                        impact_analysis['recommendations'].append(
                            "Consider closing short call before ex-dividend date"
                        )
                    else:
                        impact_analysis['recommendations'].append(
                            "Monitor short call closely approaching ex-dividend"
                        )
                
                impact_analysis['recommendations'].append(
                    "Factor dividend into profit/loss calculations"
                )
        
        return impact_analysis