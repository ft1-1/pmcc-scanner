"""
Comprehensive tests for CSV export functionality in the scanner module.
Tests the new CSV generation and historical preservation features.
"""

import pytest
import os
import csv
import tempfile
import shutil
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.append('src')

from src.analysis.scanner import PMCCScanner, ScanResults
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract


class TestCSVExport:
    """Test cases for CSV export functionality."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_scan_results(self):
        """Create sample scan results for testing."""
        # Create sample option contracts
        long_call = OptionContract(
            symbol="AAPL",
            option_symbol="AAPL250117C00150000",
            strike=Decimal("150.00"),
            expiration=date(2025, 1, 17),
            option_type="call",
            bid=Decimal("8.50"),
            ask=Decimal("8.75"),
            last=Decimal("8.60"),
            volume=1250,
            open_interest=5000,
            delta=0.65
        )
        
        short_call = OptionContract(
            symbol="AAPL",
            option_symbol="AAPL241220C00160000",
            strike=Decimal("160.00"),
            expiration=date(2024, 12, 20),
            option_type="call",
            bid=Decimal("2.30"),
            ask=Decimal("2.45"),
            last=Decimal("2.35"),
            volume=800,
            open_interest=2500,
            delta=0.25
        )
        
        # Create risk metrics
        risk_metrics = RiskMetrics(
            max_profit=Decimal("625.00"),
            max_loss=Decimal("575.00"),
            breakeven=Decimal("156.25"),
            profit_probability=0.68
        )
        
        # Create analysis
        analysis = PMCCAnalysis(
            long_call=long_call,
            short_call=short_call,
            net_debit=Decimal("625.00"),
            strike_width=Decimal("10.00"),
            risk_metrics=risk_metrics,
            analyzed_at=datetime(2024, 8, 3, 14, 30, 0)
        )
        
        # Create PMCC candidate
        candidate = PMCCCandidate(
            symbol="AAPL",
            underlying_price=Decimal("155.00"),
            analysis=analysis,
            total_score=82.5,
            liquidity_score=85.0,
            risk_reward_ratio=1.09,
            discovered_at=datetime(2024, 8, 3, 14, 25, 0)
        )
        
        # Create scan results
        results = ScanResults(
            scan_id="test-scan-123",
            started_at=datetime(2024, 8, 3, 14, 20, 0),
            stocks_screened=1250,
            stocks_passed_screening=85,
            total_duration_seconds=45.7,
            top_opportunities=[candidate]
        )
        
        return results
    
    @pytest.fixture
    def mock_scanner(self):
        """Create a mock scanner for testing."""
        return PMCCScanner()
    
    def test_export_results_csv_basic(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test basic CSV export functionality."""
        # Export to CSV
        csv_file = mock_scanner.export_results(
            sample_scan_results, 
            format="csv", 
            output_dir=temp_output_dir
        )
        
        # Verify file was created
        assert os.path.exists(csv_file)
        assert csv_file.endswith('.csv')
        
        # Verify file content
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have exactly one row (one opportunity)
            assert len(rows) == 1
            
            row = rows[0]
            
            # Verify essential fields are present
            assert row['symbol'] == 'AAPL'
            assert row['underlying_price'] == '155.00'
            assert row['total_score'] == '82.5'
            assert row['scan_id'] == 'test-scan-123'
            assert row['scan_duration_seconds'] == '45.7'
            assert row['total_stocks_screened'] == '1250'
            assert row['stocks_passed_screening'] == '85'
            
            # Verify LEAPS data
            assert row['long_strike'] == '150.00'
            assert row['long_expiration'] == '2025-01-17'
            assert row['long_delta'] == '0.65'
            
            # Verify short call data
            assert row['short_strike'] == '160.00'
            assert row['short_expiration'] == '2024-12-20'
            assert row['short_delta'] == '0.25'
            
            # Verify risk metrics
            assert row['net_debit'] == '625.00'
            assert row['max_profit'] == '625.00'
            assert row['max_loss'] == '575.00'
            assert row['breakeven'] == '156.25'
    
    def test_export_results_csv_no_opportunities(self, mock_scanner, temp_output_dir):
        """Test CSV export when no opportunities are found."""
        # Create scan results with no opportunities
        results = ScanResults(
            scan_id="test-scan-empty",
            started_at=datetime(2024, 8, 3, 15, 0, 0),
            stocks_screened=2000,
            stocks_passed_screening=120,
            total_duration_seconds=38.2,
            top_opportunities=[]
        )
        
        # Export to CSV
        csv_file = mock_scanner.export_results(results, format="csv", output_dir=temp_output_dir)
        
        # Verify file was created
        assert os.path.exists(csv_file)
        
        # Verify file content
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have exactly one row with scan metadata only
            assert len(rows) == 1
            
            row = rows[0]
            
            # Verify scan metadata is present
            assert row['scan_id'] == 'test-scan-empty'
            assert row['scan_duration_seconds'] == '38.2'
            assert row['total_stocks_screened'] == '2000'
            assert row['stocks_passed_screening'] == '120'
            
            # Verify opportunity fields are None/empty
            assert row['symbol'] == '' or row['symbol'] == 'None'
            assert row['total_score'] == '' or row['total_score'] == 'None'
    
    def test_export_results_csv_large_dataset(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test CSV export with large number of opportunities."""
        # Create 50 opportunities
        opportunities = []
        for i in range(50):
            candidate = PMCCCandidate(
                symbol=f"STOCK{i:02d}",
                underlying_price=Decimal(f"{100 + i}.50"),
                analysis=sample_scan_results.top_opportunities[0].analysis,
                total_score=90.0 - (i * 0.5),
                liquidity_score=85.0,
                risk_reward_ratio=1.5 - (i * 0.01),
                discovered_at=datetime(2024, 8, 3, 14, 25, i)
            )
            opportunities.append(candidate)
        
        # Update scan results
        large_results = ScanResults(
            scan_id="test-scan-large",
            started_at=datetime(2024, 8, 3, 14, 0, 0),
            stocks_screened=5000,
            stocks_passed_screening=500,
            total_duration_seconds=180.5,
            top_opportunities=opportunities
        )
        
        # Export to CSV
        csv_file = mock_scanner.export_results(large_results, format="csv", output_dir=temp_output_dir)
        
        # Verify file was created
        assert os.path.exists(csv_file)
        
        # Verify file content
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have 50 rows
            assert len(rows) == 50
            
            # Verify all symbols are present
            symbols = [row['symbol'] for row in rows]
            for i in range(50):
                assert f"STOCK{i:02d}" in symbols
            
            # Verify scan metadata is consistent across all rows
            for row in rows:
                assert row['scan_id'] == 'test-scan-large'
                assert row['scan_duration_seconds'] == '180.5'
                assert row['total_stocks_screened'] == '5000'
                assert row['stocks_passed_screening'] == '500'
    
    def test_export_results_csv_special_characters(self, mock_scanner, temp_output_dir):
        """Test CSV export with special characters in data."""
        # Create opportunity with special characters
        long_call = OptionContract(
            symbol="BRK.B",  # Contains period
            option_symbol="BRK.B250117C00150000",
            strike=Decimal("150.00"),
            expiration=date(2025, 1, 17),
            option_type="call",
            bid=Decimal("8.50"),
            ask=Decimal("8.75"),
            last=Decimal("8.60"),
            volume=1250,
            open_interest=5000,
            delta=0.65
        )
        
        analysis = PMCCAnalysis(
            long_call=long_call,
            short_call=long_call,  # Simplified
            net_debit=Decimal("625.00"),
            strike_width=Decimal("10.00"),
            analyzed_at=datetime(2024, 8, 3, 14, 30, 0)
        )
        
        candidate = PMCCCandidate(
            symbol="BRK.B",
            underlying_price=Decimal("155.00"),
            analysis=analysis,
            total_score=82.5,
            liquidity_score=85.0,
            risk_reward_ratio=1.09
        )
        
        results = ScanResults(
            scan_id="test-special-chars",
            started_at=datetime(2024, 8, 3, 14, 0, 0),
            stocks_screened=100,
            stocks_passed_screening=10,
            total_duration_seconds=25.0,
            top_opportunities=[candidate]
        )
        
        # Export to CSV
        csv_file = mock_scanner.export_results(results, format="csv", output_dir=temp_output_dir)
        
        # Verify file was created and content is correct
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]['symbol'] == 'BRK.B'
            assert rows[0]['long_option_symbol'] == 'BRK.B250117C00150000'
    
    def test_export_results_csv_historical_preservation(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test that CSV exports preserve historical data with timestamps."""
        # Export first scan
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 8, 3, 14, 30, 0)
            mock_datetime.strftime = datetime.strftime
            csv_file1 = mock_scanner.export_results(
                sample_scan_results, 
                format="csv", 
                output_dir=temp_output_dir
            )
        
        # Export second scan (different timestamp)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 8, 3, 15, 30, 0)
            mock_datetime.strftime = datetime.strftime
            csv_file2 = mock_scanner.export_results(
                sample_scan_results, 
                format="csv", 
                output_dir=temp_output_dir
            )
        
        # Verify both files exist and have different names
        assert os.path.exists(csv_file1)
        assert os.path.exists(csv_file2)
        assert csv_file1 \!= csv_file2
        
        # Verify timestamps are in filenames
        assert "20240803_143000" in csv_file1
        assert "20240803_153000" in csv_file2
    
    def test_export_historical_csv_with_detailed_scoring(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test export_historical_csv with detailed scoring breakdown."""
        # Export detailed CSV
        csv_file = mock_scanner.export_historical_csv(
            sample_scan_results,
            include_sub_scores=True,
            output_dir=temp_output_dir
        )
        
        # Verify file was created
        assert os.path.exists(csv_file)
        assert "detailed" in csv_file
        
        # Verify file content has extended fields
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            # Should have additional detailed fields
            basic_fields = ['symbol', 'underlying_price', 'total_score']
            for field in basic_fields:
                assert field in fieldnames
            
            # Check for some expected detailed fields (exact fields depend on implementation)
            # These would be defined in the _create_detailed_csv_row method
            expected_detailed_fields = [
                'liquidity_score', 'risk_reward_ratio', 'net_debit',
                'max_profit', 'max_loss', 'breakeven'
            ]
            
            for field in expected_detailed_fields:
                assert field in fieldnames
    
    def test_csv_field_data_types_and_formatting(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test that CSV fields are properly formatted and typed."""
        # Export to CSV
        csv_file = mock_scanner.export_results(sample_scan_results, format="csv", output_dir=temp_output_dir)
        
        # Read and verify data types
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[0]
            
            # Test decimal formatting (should be string representations of numbers)
            assert '.' in row['underlying_price']  # Should have decimal point
            assert row['underlying_price'] == '155.00'  # Should have proper precision
            
            # Test date formatting (should be ISO format)
            assert row['long_expiration'] == '2025-01-17'
            assert row['short_expiration'] == '2024-12-20'
            
            # Test timestamp formatting
            assert 'scan_timestamp' in row
            # Should be ISO timestamp format
            
            # Test float/decimal precision
            assert row['long_delta'] == '0.65'
            assert row['short_delta'] == '0.25'
    
    def test_csv_export_error_handling(self, mock_scanner, sample_scan_results):
        """Test CSV export error handling."""
        # Test with invalid output directory
        with pytest.raises(Exception):
            mock_scanner.export_results(
                sample_scan_results, 
                format="csv",
                output_dir="/invalid/directory/that/does/not/exist"
            )
        
        # Test with invalid format
        with pytest.raises(ValueError):
            mock_scanner.export_results(
                sample_scan_results,
                format="invalid_format"
            )
    
    def test_csv_file_naming_convention(self, mock_scanner, sample_scan_results, temp_output_dir):
        """Test that CSV files follow proper naming conventions."""
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 8, 3, 14, 30, 45)
            mock_datetime.strftime = datetime.strftime
            
            csv_file = mock_scanner.export_results(
                sample_scan_results,
                format="csv",
                output_dir=temp_output_dir
            )
        
        filename = os.path.basename(csv_file)
        
        # Should contain expected components
        assert filename.startswith("pmcc_scan_")
        assert "20240803_143045" in filename
        assert filename.endswith(".csv")
        
        # Test custom filename
        custom_file = mock_scanner.export_results(
            sample_scan_results,
            format="csv",
            filename="custom_scan.csv",
            output_dir=temp_output_dir
        )
        
        assert os.path.basename(custom_file) == "custom_scan.csv"
