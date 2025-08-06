"""
Comprehensive tests for EmailFormatter.format_daily_summary() method.
Tests the new HTML email rendering functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date
from decimal import Decimal
from typing import List

import sys
sys.path.append('src')

from src.notifications.formatters import EmailFormatter
from src.notifications.models import NotificationTemplate
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract, OptionSide


class TestEmailFormatterDailySummary:
    """Test cases for the new EmailFormatter.format_daily_summary() method."""
    
    @pytest.fixture
    def sample_option_contract(self):
        """Create a sample option contract for testing."""
        return OptionContract(
            option_symbol="AAPL250117C00150000",
            underlying="AAPL",
            strike=Decimal("150.00"),
            expiration=datetime(2025, 1, 17),
            side=OptionSide.CALL,
            bid=Decimal("8.50"),
            ask=Decimal("8.75"),
            last=Decimal("8.60"),
            volume=1250,
            open_interest=5000,
            delta=Decimal("0.65"),
            gamma=Decimal("0.02"),
            theta=Decimal("-0.08"),
            vega=Decimal("0.15")
        )
    
    @pytest.fixture
    def sample_pmcc_candidate(self, sample_option_contract):
        """Create a sample PMCC candidate for testing."""
        long_call = sample_option_contract
        short_call = OptionContract(
            option_symbol="AAPL241220C00160000", 
            underlying="AAPL",
            strike=Decimal("160.00"),
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            bid=Decimal("2.30"),
            ask=Decimal("2.45"),
            last=Decimal("2.35"),
            volume=800,
            open_interest=2500,
            delta=Decimal("0.25"),
            gamma=Decimal("0.015"),
            theta=Decimal("-0.12"),
            vega=Decimal("0.08")
        )
        
        risk_metrics = RiskMetrics(
            max_loss=Decimal("575.00"),
            max_profit=Decimal("625.00"),
            breakeven=Decimal("156.25"),
            probability_of_profit=Decimal("0.68")
        )
            max_loss=Decimal("575.00"),
            max_profit=Decimal("625.00"),
            breakeven=Decimal("156.25"),
            probability_of_profit=Decimal("0.68")
        )
            max_loss=Decimal("575.00"),
            breakeven=Decimal("156.25"),
            probability_of_profit=Decimal("0.68")
        )
        
        analysis = PMCCAnalysis(
            long_call=long_call,
            short_call=short_call,
            net_debit=Decimal("625.00"),
            strike_width=Decimal("10.00"),
            risk_metrics=risk_metrics,
            analyzed_at=datetime(2024, 8, 3, 14, 30, 0)
        )
        
        return PMCCCandidate(
            symbol="AAPL",
            underlying_price=Decimal("155.00"),
            analysis=analysis,
            total_score=82.5,
            liquidity_score=85.0,
            risk_reward_ratio=1.09,
            discovered_at=datetime(2024, 8, 3, 14, 25, 0)
        )
    
    def test_format_daily_summary_with_opportunities(self, sample_pmcc_candidate):
        """Test format_daily_summary with multiple opportunities."""
        candidates = [sample_pmcc_candidate]
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        result = EmailFormatter.format_daily_summary(candidates, scan_metadata)
        
        # Verify return type
        assert isinstance(result, NotificationTemplate)
        
        # Verify subject line
        assert "PMCC Daily Summary" in result.subject
        assert "1 Opportunities" in result.subject
        assert "August 03, 2024" in result.subject
        
        # Verify HTML content exists and contains key elements
        assert result.html_content is not None
        assert len(result.html_content) > 1000  # Should be substantial HTML
        
        # Check for essential HTML structure
        assert "<!DOCTYPE html>" in result.html_content
        assert "<html lang=\"en\">" in result.html_content
        assert "PMCC Daily Summary" in result.html_content
        assert "AAPL" in result.html_content
        assert "$155.00" in result.html_content
        
        # Check for metadata in HTML
        assert "45.7s" in result.html_content or "45s" in result.html_content
        assert "1,250" in result.html_content or "1250" in result.html_content
        assert "85" in result.html_content
        
        # Check for responsive design CSS
        assert "@media (max-width: 600px)" in result.html_content
        assert "font-family:" in result.html_content
        
        # Check for table structure
        assert "<table" in result.html_content
        assert "<thead>" in result.html_content
        assert "<tbody>" in result.html_content
        
        # Verify plain text fallback exists
        assert result.text_content is not None
        assert len(result.text_content) > 100
        assert "PMCC Daily Summary" in result.text_content
        assert "AAPL" in result.text_content
        
    def test_format_daily_summary_no_opportunities(self):
        """Test format_daily_summary with no opportunities found."""
        candidates = []
        scan_metadata = {
            'duration_seconds': 32.1,
            'stocks_screened': 1500,
            'stocks_passed_screening': 95,
            'scan_id': 'test-scan-456'
        }
        
        result = EmailFormatter.format_daily_summary(candidates, scan_metadata)
        
        # Verify subject reflects no opportunities
        assert "No Opportunities" in result.subject
        
        # Verify HTML still contains metadata and structure
        assert result.html_content is not None
        assert "opportunities found: 0" in result.text_content.lower()
        assert "1,500" in result.html_content or "1500" in result.html_content
        assert "32.1s" in result.html_content or "32s" in result.html_content
        
        # Check for no-opportunities message
        assert "no profitable" in result.html_content.lower()
        
        # Verify text content
        assert result.text_content is not None
        assert "no opportunities found" in result.text_content.lower()
        
    def test_format_daily_summary_large_dataset(self, sample_pmcc_candidate):
        """Test format_daily_summary with large number of opportunities (50+)."""
        # Create 52 opportunities to test performance and rendering
        candidates = []
        for i in range(52):
            candidate = PMCCCandidate(
                symbol=f"STOCK{i:02d}",
                underlying_price=Decimal(f"{100 + i}.50"),
                analysis=sample_pmcc_candidate.analysis,
                total_score=85.0 - (i * 0.5),  # Descending scores
                liquidity_score=80.0,
                risk_reward_ratio=1.2 - (i * 0.01),
                discovered_at=datetime(2024, 8, 3, 14, 25, i)
            )
            candidates.append(candidate)
        
        scan_metadata = {
            'duration_seconds': 185.3,
            'stocks_screened': 5000,
            'stocks_passed_screening': 450,
            'scan_id': 'test-scan-large'
        }
        
        result = EmailFormatter.format_daily_summary(candidates, scan_metadata)
        
        # Verify subject shows correct count
        assert "52 Opportunities" in result.subject
        
        # Verify HTML can handle large dataset
        assert result.html_content is not None
        assert len(result.html_content) > 10000  # Should be very substantial
        
        # Check for proper sorting (highest score first)
        stock00_pos = result.html_content.find("STOCK00")
        stock10_pos = result.html_content.find("STOCK10")
        assert stock00_pos < stock10_pos  # STOCK00 should appear before STOCK10
        
        # Verify all opportunities are included (not truncated)
        for i in range(52):
            assert f"STOCK{i:02d}" in result.html_content
        
        # Check for performance metadata
        assert "185.3s" in result.html_content or "3m 5s" in result.html_content
        assert "5,000" in result.html_content or "5000" in result.html_content
