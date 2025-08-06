"""
Unit tests for PMCC scanner orchestrator.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from src.analysis.scanner import (
    PMCCScanner, ScanConfiguration, ScanResults
)
from src.analysis.stock_screener import StockScreenResult
from src.analysis.options_analyzer import PMCCOpportunity
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis
from src.models.api_models import StockQuote, OptionContract, OptionSide
from src.api.marketdata_client import MarketDataClient


class TestScanConfiguration:
    """Test ScanConfiguration dataclass."""
    
    def test_default_configuration(self):
        """Test default scan configuration values."""
        config = ScanConfiguration()
        
        assert config.universe == "SP500"
        assert config.custom_symbols is None
        assert config.max_stocks_to_screen == 100
        assert config.account_size is None
        assert config.max_risk_per_trade == Decimal('0.02')
        assert config.risk_free_rate == Decimal('0.05')
        assert config.max_opportunities == 25
        assert config.min_total_score == Decimal('60')
        assert config.include_dividend_analysis is True
        assert config.perform_scenario_analysis is True
    
    def test_custom_configuration(self):
        """Test custom scan configuration."""
        config = ScanConfiguration(
            universe="NASDAQ100",
            custom_symbols=["AAPL", "MSFT", "GOOGL"],
            max_stocks_to_screen=50,
            account_size=Decimal('250000'),
            max_opportunities=10,
            min_total_score=Decimal('70')
        )
        
        assert config.universe == "NASDAQ100"
        assert config.custom_symbols == ["AAPL", "MSFT", "GOOGL"]
        assert config.max_stocks_to_screen == 50
        assert config.account_size == Decimal('250000')
        assert config.max_opportunities == 10
        assert config.min_total_score == Decimal('70')


class TestScanResults:
    """Test ScanResults dataclass."""
    
    def test_scan_results_creation(self):
        """Test creating ScanResults."""
        results = ScanResults(
            scan_id="test_scan_123",
            started_at=datetime.now(),
            stocks_screened=100,
            stocks_passed_screening=15,
            options_analyzed=15,
            opportunities_found=8
        )
        
        assert results.scan_id == "test_scan_123"
        assert results.stocks_screened == 100
        assert results.stocks_passed_screening == 15
        assert results.opportunities_found == 8
        assert len(results.top_opportunities) == 0  # Default empty list
        assert len(results.errors) == 0
        assert len(results.warnings) == 0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        results = ScanResults(
            scan_id="test",
            started_at=datetime.now(),
            stocks_screened=100,
            stocks_passed_screening=20
        )
        
        assert results.success_rate == 0.20  # 20/100
    
    def test_success_rate_zero_screened(self):
        """Test success rate with zero stocks screened."""
        results = ScanResults(
            scan_id="test",
            started_at=datetime.now(),
            stocks_screened=0,
            stocks_passed_screening=0
        )
        
        assert results.success_rate == 0.0
    
    def test_opportunity_rate_calculation(self):
        """Test opportunity rate calculation."""
        results = ScanResults(
            scan_id="test",
            started_at=datetime.now(),
            stocks_passed_screening=20,
            opportunities_found=5
        )
        
        assert results.opportunity_rate == 0.25  # 5/20
    
    def test_opportunity_rate_zero_passed(self):
        """Test opportunity rate with zero stocks passed."""
        results = ScanResults(
            scan_id="test",
            started_at=datetime.now(),
            stocks_passed_screening=0,
            opportunities_found=0
        )
        
        assert results.opportunity_rate == 0.0
    
    def test_to_dict_conversion(self):
        """Test converting results to dictionary."""
        results = ScanResults(
            scan_id="test_scan",
            started_at=datetime(2024, 1, 15, 10, 30, 0),
            completed_at=datetime(2024, 1, 15, 10, 35, 0),
            total_duration_seconds=300.0,
            stocks_screened=50,
            stocks_passed_screening=10,
            opportunities_found=3
        )
        
        result_dict = results.to_dict()
        
        assert result_dict['scan_id'] == "test_scan"
        assert result_dict['started_at'] == "2024-01-15T10:30:00"
        assert result_dict['completed_at'] == "2024-01-15T10:35:00"
        assert result_dict['total_duration_seconds'] == 300.0
        assert result_dict['stats']['stocks_screened'] == 50
        assert result_dict['stats']['success_rate'] == 0.2
        assert result_dict['stats']['opportunity_rate'] == 0.3


class TestPMCCScanner:
    """Test PMCCScanner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api_client = Mock(spec=MarketDataClient)
        self.scanner = PMCCScanner(self.mock_api_client)
    
    def test_init(self):
        """Test PMCCScanner initialization."""
        assert self.scanner.api_client == self.mock_api_client
        assert hasattr(self.scanner, 'stock_screener')
        assert hasattr(self.scanner, 'options_analyzer')
        assert hasattr(self.scanner, 'risk_calculator')
        assert hasattr(self.scanner, 'logger')
    
    def create_test_stock_result(self, symbol: str, score: Decimal = Decimal('75')) -> StockScreenResult:
        """Helper to create test stock screen results."""
        quote = StockQuote(
            symbol=symbol,
            last=Decimal('150.00'),
            volume=1_000_000
        )
        
        return StockScreenResult(
            symbol=symbol,
            quote=quote,
            market_cap=Decimal('2000000000'),
            has_weekly_options=True,
            has_leaps=True,
            screening_score=score
        )
    
    def create_test_opportunity(self, symbol: str, score: Decimal = Decimal('80')) -> PMCCOpportunity:
        """Helper to create test PMCC opportunities."""
        leaps = OptionContract(
            option_symbol=f"{symbol}241220C00130000",
            underlying=symbol,
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            strike=Decimal('130'),
            bid=Decimal('24.50'),
            ask=Decimal('25.50'),
            delta=Decimal('0.80'),
            dte=450
        )
        
        short = OptionContract(
            option_symbol=f"{symbol}240315C00155000",
            underlying=symbol,
            expiration=datetime(2024, 3, 15),
            side=OptionSide.CALL,
            strike=Decimal('155'),
            bid=Decimal('2.50'),
            ask=Decimal('2.70'),
            delta=Decimal('0.30'),
            dte=35
        )
        
        quote = StockQuote(symbol=symbol, last=Decimal('150.00'))
        
        return PMCCOpportunity(
            leaps_contract=leaps,
            short_contract=short,
            underlying_quote=quote,
            net_debit=Decimal('23.00'),
            max_profit=Decimal('2.00'),
            max_loss=Decimal('23.00'),
            breakeven=Decimal('153.00'),
            roi_potential=Decimal('8.70'),
            risk_reward_ratio=Decimal('0.087'),
            probability_score=Decimal('70'),
            liquidity_score=Decimal('75'),
            total_score=score,
            analyzed_at=datetime.now()
        )
    
    @patch.object(PMCCScanner, '_screen_stocks')
    @patch.object(PMCCScanner, '_analyze_options')
    @patch.object(PMCCScanner, '_calculate_risk_metrics')
    @patch.object(PMCCScanner, '_rank_and_filter')
    def test_scan_complete_workflow(self, mock_rank, mock_calc_risk, 
                                   mock_analyze_options, mock_screen_stocks):
        """Test complete scan workflow."""
        # Mock the workflow steps
        stock_results = [
            self.create_test_stock_result("AAPL"),
            self.create_test_stock_result("MSFT")
        ]
        
        opportunities = [
            self.create_test_opportunity("AAPL"),
            self.create_test_opportunity("MSFT")
        ]
        
        # Create mock PMCCCandidate objects
        candidates = []
        for opp in opportunities:
            analysis = PMCCAnalysis(
                long_call=opp.leaps_contract,
                short_call=opp.short_contract,
                underlying=opp.underlying_quote,
                net_debit=opp.net_debit,
                analyzed_at=datetime.now()
            )
            
            candidate = PMCCCandidate(
                symbol=opp.underlying_quote.symbol,
                underlying_price=opp.underlying_quote.last,
                analysis=analysis,
                liquidity_score=opp.liquidity_score,
                total_score=opp.total_score,
                discovered_at=datetime.now()
            )
            candidates.append(candidate)
        
        # Set up mocks
        mock_screen_stocks.return_value = stock_results
        mock_analyze_options.return_value = opportunities
        mock_calc_risk.return_value = candidates
        mock_rank.return_value = candidates[:1]  # Return top 1
        
        # Run scan
        config = ScanConfiguration(max_opportunities=1)
        results = self.scanner.scan(config)
        
        # Verify workflow was called
        assert mock_screen_stocks.called
        assert mock_analyze_options.called
        assert mock_calc_risk.called
        assert mock_rank.called
        
        # Verify results
        assert results.scan_id.startswith("pmcc_scan_")
        assert results.completed_at is not None
        assert results.stocks_passed_screening == 2
        assert results.opportunities_found == 2
        assert len(results.top_opportunities) == 1
        assert results.total_duration_seconds is not None
    
    @patch.object(PMCCScanner, '_screen_stocks')
    def test_scan_no_stocks_passed(self, mock_screen_stocks):
        """Test scan when no stocks pass screening."""
        mock_screen_stocks.return_value = []  # No stocks passed
        
        results = self.scanner.scan()
        
        assert results.stocks_passed_screening == 0
        assert results.opportunities_found == 0
        assert len(results.top_opportunities) == 0
        assert results.completed_at is not None
    
    @patch.object(PMCCScanner, '_screen_stocks')
    @patch.object(PMCCScanner, '_analyze_options')
    def test_scan_no_opportunities_found(self, mock_analyze_options, mock_screen_stocks):
        """Test scan when no opportunities are found."""
        stock_results = [self.create_test_stock_result("AAPL")]
        mock_screen_stocks.return_value = stock_results
        mock_analyze_options.return_value = []  # No opportunities
        
        results = self.scanner.scan()
        
        assert results.stocks_passed_screening == 1
        assert results.opportunities_found == 0
        assert len(results.top_opportunities) == 0
    
    @patch.object(PMCCScanner, '_screen_stocks')
    def test_scan_with_error(self, mock_screen_stocks):
        """Test scan behavior when error occurs."""
        mock_screen_stocks.side_effect = Exception("API Error")
        
        results = self.scanner.scan()
        
        assert len(results.errors) > 0
        assert "Scan error: API Error" in results.errors[0]
        assert results.completed_at is not None
    
    def test_rank_and_filter_by_score(self):
        """Test ranking and filtering candidates by score."""
        # Create candidates with different scores
        candidates = []
        for i, (symbol, score) in enumerate([("AAPL", 85), ("MSFT", 75), ("GOOGL", 90), ("TSLA", 55)]):
            analysis = PMCCAnalysis(
                long_call=Mock(),
                short_call=Mock(),
                underlying=StockQuote(symbol=symbol, last=Decimal('150')),
                net_debit=Decimal('20'),
                analyzed_at=datetime.now()
            )
            
            candidate = PMCCCandidate(
                symbol=symbol,
                underlying_price=Decimal('150'),
                analysis=analysis,
                liquidity_score=Decimal('70'),
                total_score=Decimal(str(score)),
                discovered_at=datetime.now()
            )
            candidates.append(candidate)
        
        config = ScanConfiguration(
            min_total_score=Decimal('70'),  # Should filter out TSLA (55)
            max_opportunities=2
        )
        
        result = self.scanner._rank_and_filter(candidates, config)
        
        # Should return top 2 with score >= 70, ranked by score
        assert len(result) == 2
        assert result[0].symbol == "GOOGL"  # Highest score (90)
        assert result[1].symbol == "AAPL"   # Second highest (85)
        assert result[0].rank == 1
        assert result[1].rank == 2
        
        # TSLA should be filtered out due to low score
        symbols = [c.symbol for c in result]
        assert "TSLA" not in symbols
    
    def test_rank_and_filter_empty_list(self):
        """Test ranking and filtering with empty candidate list."""
        config = ScanConfiguration()
        result = self.scanner._rank_and_filter([], config)
        
        assert result == []
    
    def test_get_scan_summary_with_opportunities(self):
        """Test generating scan summary with opportunities."""
        # Create test results with opportunities
        analysis = PMCCAnalysis(
            long_call=Mock(),
            short_call=Mock(),
            underlying=StockQuote(symbol="AAPL", last=Decimal('150')),
            net_debit=Decimal('20'),
            analyzed_at=datetime.now()
        )
        analysis.risk_metrics = Mock()
        analysis.risk_metrics.max_profit = Decimal('5.00')
        
        candidate = PMCCCandidate(
            symbol="AAPL",
            underlying_price=Decimal('150'),
            analysis=analysis,
            liquidity_score=Decimal('80'),
            total_score=Decimal('85'),
            discovered_at=datetime.now()
        )
        candidate.risk_reward_ratio = Decimal('0.25')
        
        results = ScanResults(
            scan_id="test_scan",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_seconds=120.0,
            stocks_screened=50,
            stocks_passed_screening=10,
            opportunities_found=5,
            top_opportunities=[candidate]
        )
        
        summary = self.scanner.get_scan_summary(results)
        
        assert summary['scan_id'] == "test_scan"
        assert summary['duration_seconds'] == 120.0
        assert summary['statistics']['stocks_screened'] == 50
        assert summary['statistics']['success_rate'] == "20.0%"
        assert summary['statistics']['opportunity_rate'] == "50.0%"
        
        # Check top opportunity summary
        assert summary['top_opportunity']['symbol'] == "AAPL"
        assert summary['top_opportunity']['score'] == 85.0
        assert summary['top_opportunity']['max_profit'] == 5.0
        assert summary['top_opportunity']['risk_reward_ratio'] == 0.25
        
        # Check score distribution
        assert summary['score_distribution']['highest'] == 85.0
        assert summary['score_distribution']['lowest'] == 85.0
        assert summary['score_distribution']['average'] == 85.0
    
    def test_get_scan_summary_no_opportunities(self):
        """Test generating scan summary with no opportunities."""
        results = ScanResults(
            scan_id="empty_scan",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_seconds=60.0,
            stocks_screened=100,
            stocks_passed_screening=0,
            opportunities_found=0
        )
        
        summary = self.scanner.get_scan_summary(results)
        
        assert summary['scan_id'] == "empty_scan"
        assert summary['duration_seconds'] == 60.0
        assert summary['statistics']['success_rate'] == "0.0%"
        assert summary['statistics']['opportunity_rate'] == "0.0%"
        assert 'top_opportunity' not in summary
        assert 'score_distribution' not in summary
    
    def test_get_scan_summary_with_errors_warnings(self):
        """Test scan summary includes error and warning counts."""
        results = ScanResults(
            scan_id="error_scan",
            started_at=datetime.now(),
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1", "Warning 2", "Warning 3"]
        )
        
        summary = self.scanner.get_scan_summary(results)
        
        assert summary['errors'] == 2
        assert summary['warnings'] == 3
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_export_results_json(self, mock_json_dump, mock_open):
        """Test exporting results to JSON."""
        results = ScanResults(
            scan_id="test_export",
            started_at=datetime.now()
        )
        
        filename = self.scanner.export_results(results, "json", "test_results.json")
        
        assert filename == "test_results.json"
        mock_open.assert_called_once_with("test_results.json", 'w')
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', create=True)
    @patch('csv.DictWriter')
    def test_export_results_csv(self, mock_csv_writer, mock_open):
        """Test exporting results to CSV."""
        # Create test candidate for CSV export
        analysis = PMCCAnalysis(
            long_call=Mock(),
            short_call=Mock(),
            underlying=StockQuote(symbol="AAPL", last=Decimal('150')),
            net_debit=Decimal('20'),
            analyzed_at=datetime.now()
        )
        
        candidate = PMCCCandidate(
            symbol="AAPL",
            underlying_price=Decimal('150'),
            analysis=analysis,
            liquidity_score=Decimal('80'),
            total_score=Decimal('85'),
            discovered_at=datetime.now()
        )
        
        results = ScanResults(
            scan_id="test_csv",
            started_at=datetime.now(),
            top_opportunities=[candidate]
        )
        
        # Mock the CSV writer
        mock_writer_instance = Mock()
        mock_csv_writer.return_value = mock_writer_instance
        
        filename = self.scanner.export_results(results, "csv", "test_results.csv")
        
        assert filename == "test_results.csv"
        mock_open.assert_called_once_with("test_results.csv", 'w', newline='')
        mock_writer_instance.writeheader.assert_called_once()
        mock_writer_instance.writerow.assert_called_once()
    
    def test_export_results_unsupported_format(self):
        """Test export with unsupported format raises error."""
        results = ScanResults(scan_id="test", started_at=datetime.now())
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            self.scanner.export_results(results, "xlsx")
    
    @patch.object(PMCCScanner, '_get_option_chain')
    @patch.object(PMCCScanner, '_get_current_quote')
    def test_scan_symbol_success(self, mock_get_quote, mock_get_chain):
        """Test scanning a specific symbol successfully."""
        # Mock API responses
        from src.api.marketdata_client import APIResponse, APIStatus
        
        quote_response = APIResponse(
            status=APIStatus.OK,
            data={'symbol': ['AAPL'], 'last': [150.00]}
        )
        mock_get_quote.return_value = quote_response
        
        # Mock options analyzer
        with patch.object(self.scanner.options_analyzer, 'find_pmcc_opportunities') as mock_find:
            mock_find.return_value = [self.create_test_opportunity("AAPL")]
            
            result = self.scanner.scan_symbol("AAPL")
            
            assert len(result) == 1
            assert result[0].symbol == "AAPL"
            assert result[0].total_score is not None
    
    @patch.object(PMCCScanner, '_get_option_chain')
    @patch.object(PMCCScanner, '_get_current_quote')
    def test_scan_symbol_api_failure(self, mock_get_quote, mock_get_chain):
        """Test scanning symbol when API calls fail."""
        from src.api.marketdata_client import APIResponse, APIStatus, APIError
        
        # Mock failed API response
        quote_response = APIResponse(
            status=APIStatus.ERROR,
            error=APIError(code=500, message="Server Error")
        )
        mock_get_quote.return_value = quote_response
        
        result = self.scanner.scan_symbol("INVALID")
        
        assert result == []