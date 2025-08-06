"""
Unit tests for risk calculator functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.analysis.risk_calculator import (
    RiskCalculator, EarlyAssignmentRisk, PositionSizing, 
    ScenarioAnalysis, ComprehensiveRisk
)
from src.models.api_models import OptionContract, StockQuote, OptionSide
from src.models.pmcc_models import PMCCAnalysis, RiskMetrics


class TestEarlyAssignmentRisk:
    """Test EarlyAssignmentRisk dataclass."""
    
    def test_early_assignment_risk_creation(self):
        """Test creating EarlyAssignmentRisk."""
        risk = EarlyAssignmentRisk(
            risk_level="MEDIUM",
            probability=Decimal('25'),
            factors=["Short call is 3% ITM", "Less than 2 weeks to expiration"],
            days_to_dividend=5,
            dividend_amount=Decimal('0.50'),
            itm_amount=Decimal('2.50')
        )
        
        assert risk.risk_level == "MEDIUM"
        assert risk.probability == Decimal('25')
        assert len(risk.factors) == 2
        assert risk.days_to_dividend == 5
        assert risk.is_high_risk is False
    
    def test_is_high_risk_property(self):
        """Test is_high_risk property."""
        high_risk = EarlyAssignmentRisk(
            risk_level="HIGH",
            probability=Decimal('75'),
            factors=["High assignment risk"]
        )
        
        medium_risk = EarlyAssignmentRisk(
            risk_level="MEDIUM", 
            probability=Decimal('35'),
            factors=["Medium assignment risk"]
        )
        
        assert high_risk.is_high_risk is True
        assert medium_risk.is_high_risk is False


class TestPositionSizing:
    """Test PositionSizing dataclass."""
    
    def test_position_sizing_creation(self):
        """Test creating PositionSizing."""
        sizing = PositionSizing(
            max_position_size=5,
            recommended_size=2,
            capital_required=Decimal('5000'),
            capital_at_risk=Decimal('5000'),
            portfolio_percentage=Decimal('5.0')
        )
        
        assert sizing.max_position_size == 5
        assert sizing.recommended_size == 2
        assert sizing.capital_required == Decimal('5000')
        assert sizing.leverage_ratio == Decimal('1')  # 5000/5000
    
    def test_leverage_ratio_calculation(self):
        """Test leverage ratio calculation."""
        sizing = PositionSizing(
            max_position_size=3,
            recommended_size=1,
            capital_required=Decimal('10000'),
            capital_at_risk=Decimal('2500'),  # Only 25% at risk
            portfolio_percentage=Decimal('10.0')
        )
        
        assert sizing.leverage_ratio == Decimal('0.25')
    
    def test_leverage_ratio_zero_capital(self):
        """Test leverage ratio with zero capital."""
        sizing = PositionSizing(
            max_position_size=1,
            recommended_size=1,
            capital_required=Decimal('0'),
            capital_at_risk=Decimal('1000'),
            portfolio_percentage=Decimal('0')
        )
        
        assert sizing.leverage_ratio == Decimal('1')  # Default when division by zero


class TestScenarioAnalysis:
    """Test ScenarioAnalysis dataclass."""
    
    def test_scenario_analysis_creation(self):
        """Test creating ScenarioAnalysis."""
        scenarios = {
            "down_10": {"price": Decimal("135"), "pnl": Decimal("-500")},
            "flat": {"price": Decimal("150"), "pnl": Decimal("200")},
            "up_10": {"price": Decimal("165"), "pnl": Decimal("800")}
        }
        
        analysis = ScenarioAnalysis(
            scenarios=scenarios,
            best_case={"price": Decimal("165"), "pnl": Decimal("800")},
            worst_case={"price": Decimal("135"), "pnl": Decimal("-500")},
            expected_case={"price": Decimal("150"), "pnl": Decimal("200")}
        )
        
        assert len(analysis.scenarios) == 3
        assert analysis.get_scenario_pnl("up_10") == Decimal("800")
        assert analysis.get_scenario_pnl("nonexistent") is None


class TestRiskCalculator:
    """Test RiskCalculator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = RiskCalculator()
    
    def create_test_pmcc_analysis(self) -> PMCCAnalysis:
        """Helper to create test PMCC analysis."""
        long_call = OptionContract(
            option_symbol="AAPL241220C00130000",
            underlying="AAPL",
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            strike=Decimal('130'),
            bid=Decimal('24.50'),
            ask=Decimal('25.50'),
            delta=Decimal('0.80'),
            gamma=Decimal('0.01'),
            theta=Decimal('-0.05'),
            vega=Decimal('0.15'),
            dte=450,
            extrinsic_value=Decimal('5.50')
        )
        
        short_call = OptionContract(
            option_symbol="AAPL240315C00155000",
            underlying="AAPL",
            expiration=datetime(2024, 3, 15),
            side=OptionSide.CALL,
            strike=Decimal('155'),
            bid=Decimal('2.50'),
            ask=Decimal('2.70'),
            delta=Decimal('0.30'),
            gamma=Decimal('0.02'),
            theta=Decimal('-0.03'),
            vega=Decimal('0.08'),
            dte=35,
            extrinsic_value=Decimal('2.50')
        )
        
        underlying = StockQuote(
            symbol="AAPL",
            last=Decimal('150.00'),
            volume=2_000_000
        )
        
        analysis = PMCCAnalysis(
            long_call=long_call,
            short_call=short_call,
            underlying=underlying,
            net_debit=Decimal('23.00'),  # 25.50 - 2.50
            credit_received=Decimal('2.50'),
            analyzed_at=datetime.now()
        )
        
        # Calculate basic risk metrics
        analysis.risk_metrics = analysis.calculate_risk_metrics()
        
        return analysis
    
    def test_calculate_early_assignment_risk_low(self):
        """Test early assignment risk calculation - low risk scenario."""
        analysis = self.create_test_pmcc_analysis()
        
        # Modify to be OTM (low risk)
        analysis.underlying.last = Decimal('150.00')  # Below short strike of 155
        
        risk = self.calculator._calculate_early_assignment_risk(analysis)
        
        assert risk.risk_level == "LOW"
        assert risk.probability <= Decimal('30')  # Should be relatively low
        assert risk.itm_amount is None  # Not ITM
    
    def test_calculate_early_assignment_risk_high_itm(self):
        """Test early assignment risk calculation - high ITM scenario."""
        analysis = self.create_test_pmcc_analysis()
        
        # Modify to be significantly ITM
        analysis.underlying.last = Decimal('165.00')  # Well above short strike of 155
        
        risk = self.calculator._calculate_early_assignment_risk(analysis)
        
        assert risk.risk_level in ["MEDIUM", "HIGH"]
        assert risk.probability > Decimal('20')
        assert risk.itm_amount == Decimal('10.00')  # 165 - 155
        assert "Short call is 6.5% ITM" in " ".join(risk.factors)
    
    def test_calculate_early_assignment_risk_dividend(self):
        """Test early assignment risk with dividend."""
        analysis = self.create_test_pmcc_analysis()
        
        # Make short call ITM
        analysis.underlying.last = Decimal('157.00')
        
        # Add dividend info
        dividend_info = {
            'ex_dividend_date': datetime.now() + timedelta(days=10),
            'amount': Decimal('0.75')  # Higher than extrinsic value
        }
        
        risk = self.calculator._calculate_early_assignment_risk(analysis, dividend_info)
        
        assert risk.risk_level == "HIGH"
        assert risk.dividend_amount == Decimal('0.75')
        assert risk.days_to_dividend == 10
        assert "Dividend (0.75) > extrinsic value" in " ".join(risk.factors)
    
    def test_calculate_early_assignment_risk_short_dte(self):
        """Test early assignment risk with short time to expiration."""
        analysis = self.create_test_pmcc_analysis()
        
        # Modify to have very short DTE
        analysis.short_call.dte = 5  # Less than 1 week
        analysis.underlying.last = Decimal('157.00')  # Slightly ITM
        
        risk = self.calculator._calculate_early_assignment_risk(analysis)
        
        assert risk.risk_level in ["MEDIUM", "HIGH"]
        assert "Less than 1 week to expiration" in " ".join(risk.factors)
    
    def test_calculate_position_sizing_default_account(self):
        """Test position sizing with default account size."""
        analysis = self.create_test_pmcc_analysis()
        
        sizing = self.calculator._calculate_position_sizing(analysis)
        
        assert sizing.max_position_size >= 1
        assert sizing.recommended_size >= 1
        assert sizing.recommended_size <= sizing.max_position_size
        assert sizing.capital_required > 0
        assert sizing.capital_at_risk > 0
        assert sizing.portfolio_percentage >= 0
    
    def test_calculate_position_sizing_custom_account(self):
        """Test position sizing with custom account size."""
        analysis = self.create_test_pmcc_analysis()
        account_size = Decimal('50000')  # $50k account
        
        sizing = self.calculator._calculate_position_sizing(analysis, account_size)
        
        # With 2% risk limit and $23k net debit, should allow limited position
        max_risk = account_size * Decimal('0.02')  # $1000 max risk
        expected_max_size = int(max_risk / analysis.net_debit)  # Should be 0 (too expensive)
        
        # But we enforce minimum of 1 contract
        assert sizing.max_position_size >= 1
        assert sizing.capital_required == analysis.net_debit * sizing.recommended_size
    
    def test_calculate_position_sizing_large_account(self):
        """Test position sizing with large account."""
        analysis = self.create_test_pmcc_analysis()
        account_size = Decimal('1000000')  # $1M account
        
        sizing = self.calculator._calculate_position_sizing(analysis, account_size)
        
        # Should allow more contracts with larger account
        assert sizing.max_position_size > 1
        assert sizing.portfolio_percentage < Decimal('10')  # Should be well under 10%
    
    def test_perform_scenario_analysis(self):
        """Test scenario analysis with various price movements."""
        analysis = self.create_test_pmcc_analysis()
        
        scenario_analysis = self.calculator._perform_scenario_analysis(analysis)
        
        # Should have multiple scenarios
        assert len(scenario_analysis.scenarios) > 5
        assert "flat" in scenario_analysis.scenarios
        assert "up_10" in scenario_analysis.scenarios
        assert "down_10" in scenario_analysis.scenarios
        
        # Should have best/worst/expected cases
        assert scenario_analysis.best_case is not None
        assert scenario_analysis.worst_case is not None
        assert scenario_analysis.expected_case is not None
        
        # Best case P&L should be >= worst case P&L
        best_pnl = scenario_analysis.best_case.get('pnl', Decimal('0'))
        worst_pnl = scenario_analysis.worst_case.get('pnl', Decimal('0'))
        assert best_pnl >= worst_pnl
    
    def test_calculate_pnl_at_expiration_otm(self):
        """Test P&L calculation when short call expires OTM."""
        analysis = self.create_test_pmcc_analysis()
        
        # Price at expiration below short strike (OTM)
        price_at_exp = Decimal('150.00')
        pnl = self.calculator._calculate_pnl_at_expiration(analysis, price_at_exp)
        
        # Long call value: max(0, 150-130) = 20
        # Short call obligation: max(0, 150-155) = 0
        # P&L = 20 - 0 - 23 = -3
        expected_pnl = Decimal('20') - Decimal('0') - Decimal('23')
        assert pnl == expected_pnl
    
    def test_calculate_pnl_at_expiration_itm(self):
        """Test P&L calculation when short call expires ITM."""
        analysis = self.create_test_pmcc_analysis()
        
        # Price at expiration above short strike (ITM)
        price_at_exp = Decimal('160.00')
        pnl = self.calculator._calculate_pnl_at_expiration(analysis, price_at_exp)
        
        # Long call value: max(0, 160-130) = 30
        # Short call obligation: max(0, 160-155) = 5
        # P&L = 30 - 5 - 23 = 2
        expected_pnl = Decimal('30') - Decimal('5') - Decimal('23')
        assert pnl == expected_pnl
    
    def test_calculate_pnl_at_expiration_max_profit(self):
        """Test P&L calculation at max profit point."""
        analysis = self.create_test_pmcc_analysis()
        
        # Price at expiration exactly at short strike (max profit)
        price_at_exp = Decimal('155.00')
        pnl = self.calculator._calculate_pnl_at_expiration(analysis, price_at_exp)
        
        # Long call value: max(0, 155-130) = 25
        # Short call obligation: max(0, 155-155) = 0
        # P&L = 25 - 0 - 23 = 2
        expected_pnl = Decimal('25') - Decimal('0') - Decimal('23')
        assert pnl == expected_pnl
        assert pnl == analysis.risk_metrics.max_profit
    
    def test_calculate_var_95(self):
        """Test 95% Value at Risk calculation."""
        # Create scenario analysis with known P&L values
        scenarios = {}
        pnl_values = [-1000, -500, -200, 100, 300, 500, 800, 1000, 1200]
        scenario_names = [f"scenario_{i}" for i in range(len(pnl_values))]
        
        for name, pnl in zip(scenario_names, pnl_values):
            scenarios[name] = {'pnl': Decimal(str(pnl))}
        
        scenario_analysis = ScenarioAnalysis(
            scenarios=scenarios,
            best_case={},
            worst_case={},
            expected_case={}
        )
        
        var_95 = self.calculator._calculate_var_95(scenario_analysis)
        
        # 5th percentile of 9 values should be around the first value
        # VaR should be positive (representing loss)
        assert var_95 is not None
        assert var_95 > 0  # Should be positive loss amount
    
    def test_calculate_expected_shortfall(self):
        """Test expected shortfall calculation."""
        # Create scenario analysis with known P&L values
        scenarios = {}
        pnl_values = [-1000, -800, -500, -200, 100, 300, 500, 800, 1000]
        scenario_names = [f"scenario_{i}" for i in range(len(pnl_values))]
        
        for name, pnl in zip(scenario_names, pnl_values):
            scenarios[name] = {'pnl': Decimal(str(pnl))}
        
        scenario_analysis = ScenarioAnalysis(
            scenarios=scenarios,
            best_case={},
            worst_case={},
            expected_case={}
        )
        
        es = self.calculator._calculate_expected_shortfall(scenario_analysis)
        
        # Expected shortfall should be positive and >= VaR
        assert es is not None
        assert es > 0
    
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        analysis = self.create_test_pmcc_analysis()
        risk_free_rate = Decimal('0.05')  # 5%
        
        sharpe = self.calculator._calculate_sharpe_ratio(analysis, risk_free_rate)
        
        # Should return a reasonable Sharpe ratio
        assert sharpe is not None
        # Sharpe ratio can be negative, so just check it's a number
        assert isinstance(sharpe, Decimal)
    
    def test_calculate_theta_decay_rate(self):
        """Test theta decay rate calculation."""
        analysis = self.create_test_pmcc_analysis()
        
        theta_decay = self.calculator._calculate_theta_decay_rate(analysis)
        
        # Net theta = long theta - short theta = -0.05 - (-0.03) = -0.02
        expected_theta = Decimal('-0.05') - Decimal('-0.03')
        assert theta_decay == expected_theta
    
    def test_calculate_vega_risk(self):
        """Test vega risk calculation."""
        analysis = self.create_test_pmcc_analysis()
        
        vega_risk = self.calculator._calculate_vega_risk(analysis)
        
        # Net vega = long vega - short vega = 0.15 - 0.08 = 0.07
        # Vega risk should be absolute value
        expected_vega_risk = abs(Decimal('0.15') - Decimal('0.08'))
        assert vega_risk == expected_vega_risk
    
    def test_calculate_comprehensive_risk(self):
        """Test comprehensive risk calculation."""
        analysis = self.create_test_pmcc_analysis()
        account_size = Decimal('100000')
        
        comp_risk = self.calculator.calculate_comprehensive_risk(
            analysis, account_size
        )
        
        assert isinstance(comp_risk, ComprehensiveRisk)
        assert comp_risk.basic_metrics is not None
        assert comp_risk.early_assignment is not None
        assert comp_risk.position_sizing is not None
        assert comp_risk.scenario_analysis is not None
        
        # Check that all components are properly calculated
        assert comp_risk.early_assignment.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert comp_risk.position_sizing.recommended_size >= 1
        assert len(comp_risk.scenario_analysis.scenarios) > 0
    
    def test_calculate_breakeven_analysis(self):
        """Test breakeven analysis calculation."""
        analysis = self.create_test_pmcc_analysis()
        
        breakevens = self.calculator.calculate_breakeven_analysis(analysis)
        
        assert 'static_breakeven' in breakevens
        assert breakevens['static_breakeven'] == analysis.long_call.strike + analysis.net_debit
        
        # Should have profit target breakeven
        assert 'profit_target_25pct' in breakevens
        profit_target = analysis.net_debit * Decimal('0.25')
        expected_profit_be = analysis.long_call.strike + analysis.net_debit + profit_target
        assert breakevens['profit_target_25pct'] == expected_profit_be
    
    def test_assess_dividend_impact_no_dividend(self):
        """Test dividend impact assessment with no dividend."""
        analysis = self.create_test_pmcc_analysis()
        
        impact = self.calculator.assess_dividend_impact(analysis, {})
        
        assert impact['has_dividend_risk'] is False
        assert impact['dividend_amount'] is None
        assert impact['early_assignment_likely'] is False
        assert len(impact['recommendations']) == 0
    
    def test_assess_dividend_impact_high_risk(self):
        """Test dividend impact assessment with high assignment risk."""
        analysis = self.create_test_pmcc_analysis()
        
        # Make short call ITM
        analysis.underlying.last = Decimal('158.00')
        
        dividend_info = {
            'ex_dividend_date': datetime.now() + timedelta(days=15),  # Before expiration
            'amount': Decimal('3.00')  # Higher than extrinsic value
        }
        
        impact = self.calculator.assess_dividend_impact(analysis, dividend_info)
        
        assert impact['has_dividend_risk'] is True
        assert impact['dividend_amount'] == Decimal('3.00')
        assert impact['early_assignment_likely'] is True
        assert len(impact['recommendations']) > 0
        assert any("closing short call" in rec.lower() for rec in impact['recommendations'])
    
    def test_assess_dividend_impact_moderate_risk(self):
        """Test dividend impact assessment with moderate risk."""
        analysis = self.create_test_pmcc_analysis()
        
        # Make short call ITM
        analysis.underlying.last = Decimal('157.00')
        
        dividend_info = {
            'ex_dividend_date': datetime.now() + timedelta(days=20),  # Before expiration
            'amount': Decimal('1.00')  # Lower than extrinsic value
        }
        
        impact = self.calculator.assess_dividend_impact(analysis, dividend_info)
        
        assert impact['has_dividend_risk'] is True
        assert impact['dividend_amount'] == Decimal('1.00')
        assert impact['early_assignment_likely'] is False
        assert len(impact['recommendations']) > 0
        assert any("monitor" in rec.lower() for rec in impact['recommendations'])