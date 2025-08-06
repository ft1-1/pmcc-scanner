"""
Unit tests for notification formatters.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.notifications.formatters import WhatsAppFormatter, EmailFormatter
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract, StockQuote, OptionSide


@pytest.fixture
def sample_pmcc_candidate():
    """Create a sample PMCC candidate for testing."""
    # Create mock option contracts
    long_call = OptionContract(
        option_symbol="AAPL250117C00150000",
        underlying_symbol="AAPL",
        strike=Decimal("150.00"),
        expiration=datetime(2025, 1, 17),
        side=OptionSide.CALL,
        bid=Decimal("25.50"),
        ask=Decimal("26.00"),
        delta=Decimal("0.80"),
        dte=90
    )
    
    short_call = OptionContract(
        option_symbol="AAPL241220C00160000",
        underlying_symbol="AAPL",
        strike=Decimal("160.00"),
        expiration=datetime(2024, 12, 20),
        side=OptionSide.CALL,
        bid=Decimal("3.50"),
        ask=Decimal("3.75"),
        delta=Decimal("0.30"),
        dte=30
    )
    
    underlying = StockQuote(
        symbol="AAPL",
        price=Decimal("155.00"),
        timestamp=datetime.now()
    )
    
    # Create analysis
    analysis = PMCCAnalysis(
        long_call=long_call,
        short_call=short_call,
        underlying=underlying,
        net_debit=Decimal("22.25"),
        risk_metrics=RiskMetrics(
            max_loss=Decimal("22.25"),
            max_profit=Decimal("7.75"),
            breakeven=Decimal("172.25"),
            risk_reward_ratio=Decimal("0.35")
        )
    )
    
    return PMCCCandidate(
        symbol="AAPL",
        underlying_price=Decimal("155.00"),
        analysis=analysis,
        liquidity_score=Decimal("85"),
        total_score=Decimal("82")
    )


class TestWhatsAppFormatter:
    """Test WhatsApp message formatting."""
    
    def test_format_opportunity_basic(self, sample_pmcc_candidate):
        """Test basic opportunity formatting for WhatsApp."""
        template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        
        content = template.text_content
        
        # Check for key elements
        assert "PMCC Opportunity: AAPL" in content
        assert "$155.00" in content  # Current price
        assert "$150.00" in content  # Long strike
        assert "$160.00" in content  # Short strike
        assert "$22.25" in content   # Net cost
        assert "$7.75" in content    # Max profit
        assert "85/100" in content   # Liquidity score
        assert "Jan 17, 2025" in content  # Long expiration
        assert "Dec 20, 2024" in content  # Short expiration
    
    def test_format_opportunity_with_profit_percentage(self, sample_pmcc_candidate):
        """Test profit percentage calculation in WhatsApp format."""
        template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        
        content = template.text_content
        
        # Calculate expected percentage: 7.75 / 22.25 * 100 = 34.8%
        assert "34.8%" in content or "34.9%" in content or "35%" in content
    
    def test_format_opportunity_no_risk_metrics(self, sample_pmcc_candidate):
        """Test formatting when risk metrics are missing."""
        sample_pmcc_candidate.analysis.risk_metrics = None
        
        template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        
        content = template.text_content
        
        # Should still contain basic info
        assert "AAPL" in content
        assert "$155.00" in content
        assert "$22.25" in content
        # Should not crash or contain "None"
        assert "None" not in content
    
    def test_format_multiple_opportunities_with_candidates(self, sample_pmcc_candidate):
        """Test formatting multiple opportunities."""
        candidates = [sample_pmcc_candidate, sample_pmcc_candidate]
        # Make second candidate different
        candidates[1].symbol = "MSFT"
        candidates[1].underlying_price = Decimal("350.00")
        candidates[1].total_score = Decimal("78")
        
        template = WhatsAppFormatter.format_multiple_opportunities(candidates)
        
        content = template.text_content
        
        assert "PMCC Daily Scan Results" in content
        assert "Found 2 opportunities" in content
        assert "Showing top 2:" in content
        assert "1. AAPL" in content
        assert "2. MSFT" in content
        assert "$155.00" in content
        assert "$350.00" in content
    
    def test_format_multiple_opportunities_empty_list(self):
        """Test formatting with no opportunities."""
        template = WhatsAppFormatter.format_multiple_opportunities([])
        
        content = template.text_content
        
        assert "No profitable PMCC opportunities found" in content
    
    def test_format_multiple_opportunities_limit(self, sample_pmcc_candidate):
        """Test limiting number of opportunities shown."""
        # Create 10 candidates
        candidates = []
        for i in range(10):
            candidate = sample_pmcc_candidate
            candidate.symbol = f"STOCK{i}"
            candidate.total_score = Decimal(str(90 - i))  # Decreasing scores
            candidates.append(candidate)
        
        template = WhatsAppFormatter.format_multiple_opportunities(candidates, limit=3)
        
        content = template.text_content
        
        assert "Found 10 opportunities" in content
        assert "Showing top 3:" in content
        # Should only show first 3
        assert "STOCK0" in content
        assert "STOCK1" in content
        assert "STOCK2" in content
        assert "STOCK3" not in content


class TestEmailFormatter:
    """Test email formatting."""
    
    def test_format_opportunity_basic(self, sample_pmcc_candidate):
        """Test basic opportunity formatting for email."""
        template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        
        # Check subject
        assert "PMCC Opportunity Alert: AAPL" in template.subject
        assert "34.8%" in template.subject or "35%" in template.subject
        
        # Check text content
        text = template.text_content
        assert "AAPL" in text
        assert "$155.00" in text
        assert "$150.00" in text
        assert "$160.00" in text
        assert "$22.25" in text
        assert "$7.75" in text
        
        # Check HTML content
        html = template.html_content
        assert "<html>" in html
        assert "AAPL" in html
        assert "$155.00" in html
        assert "color: #2E8B57" in html  # Should have styling
    
    def test_format_opportunity_no_risk_metrics(self, sample_pmcc_candidate):
        """Test email formatting when risk metrics are missing."""
        sample_pmcc_candidate.analysis.risk_metrics = None
        
        template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        
        # Should still work but have different subject
        assert "PMCC Opportunity Alert: AAPL" in template.subject
        assert "Profitable Setup" in template.subject
        
        # Content should still be present
        assert "AAPL" in template.text_content
        assert "AAPL" in template.html_content
    
    def test_format_multiple_opportunities_with_candidates(self, sample_pmcc_candidate):
        """Test formatting multiple opportunities for email."""
        candidates = [sample_pmcc_candidate, sample_pmcc_candidate]
        candidates[1].symbol = "MSFT"
        candidates[1].underlying_price = Decimal("350.00")
        
        template = EmailFormatter.format_multiple_opportunities(candidates)
        
        # Check subject
        assert "PMCC Daily Scan - 2 Opportunities Found" in template.subject
        
        # Check text content
        text = template.text_content
        assert "PMCC Daily Scan Results" in text
        assert "Total Opportunities Found: 2" in text
        assert "1. AAPL" in text
        assert "2. MSFT" in text
        
        # Check HTML content
        html = template.html_content
        assert "<table>" in html
        assert "AAPL" in html
        assert "MSFT" in html
        assert "$155.00" in html
        assert "$350.00" in html
    
    def test_format_multiple_opportunities_empty_list(self):
        """Test email formatting with no opportunities."""
        template = EmailFormatter.format_multiple_opportunities([])
        
        assert "No Opportunities Found" in template.subject
        assert "No profitable PMCC opportunities" in template.text_content
        assert "No profitable PMCC opportunities" in template.html_content
    
    def test_generate_html_content_styling(self, sample_pmcc_candidate):
        """Test that HTML content includes proper styling."""
        html = EmailFormatter._generate_html_content(sample_pmcc_candidate)
        
        # Check for CSS styling
        assert "font-family: Arial" in html
        assert "background-color:" in html
        assert "border-radius:" in html
        assert "padding:" in html
        
        # Check for responsive design
        assert "@media" in html
        assert "max-width: 600px" in html
    
    def test_generate_text_content_structure(self, sample_pmcc_candidate):
        """Test text content structure and formatting."""
        text = EmailFormatter._generate_text_content(sample_pmcc_candidate)
        
        # Check structure
        assert "PMCC Opportunity Alert: AAPL" in text
        assert "=" * 40 in text
        assert "Current Market Data:" in text
        assert "Long LEAPS Position:" in text
        assert "Short Call Position:" in text
        assert "Position Analysis:" in text
        assert "Important Considerations:" in text
        
        # Check specific data
        assert "Underlying Price: $155.00" in text
        assert "Strike Price: $150.00" in text
        assert "Strike Price: $160.00" in text
        assert "Net Debit (Cost): $22.25" in text
    
    def test_generate_summary_html_table(self, sample_pmcc_candidate):
        """Test HTML summary table generation."""
        candidates = [sample_pmcc_candidate]
        html = EmailFormatter._generate_summary_html(candidates)
        
        # Check table structure
        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "Rank" in html
        assert "Symbol" in html
        assert "Price" in html
        assert "Net Cost" in html
        assert "Max Profit" in html
        assert "Return %" in html
        assert "Score" in html
        
        # Check data
        assert "AAPL" in html
        assert "$155.00" in html
        assert "$22.25" in html
        assert "$7.75" in html
    
    def test_profit_percentage_calculation(self, sample_pmcc_candidate):
        """Test profit percentage calculations in formatters."""
        # Test WhatsApp
        whatsapp_template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        # 7.75 / 22.25 * 100 ≈ 34.8%
        assert "34.8%" in whatsapp_template.text_content or "35%" in whatsapp_template.text_content
        
        # Test Email
        email_template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        assert "34.8%" in email_template.subject or "35%" in email_template.subject
        assert "34.8%" in email_template.text_content or "35%" in email_template.text_content
    
    def test_date_formatting(self, sample_pmcc_candidate):
        """Test date formatting in templates."""
        # WhatsApp should use short format
        whatsapp_template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        assert "Jan 17, 2025" in whatsapp_template.text_content
        assert "Dec 20, 2024" in whatsapp_template.text_content
        
        # Email should use full format
        email_template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        assert "January 17, 2025" in email_template.text_content
        assert "December 20, 2024" in email_template.text_content
    
    def test_risk_metrics_display(self, sample_pmcc_candidate):
        """Test display of risk metrics in both formats."""
        # Both should show max profit, max loss, breakeven
        whatsapp_template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        email_template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        
        for template in [whatsapp_template, email_template]:
            content = template.text_content
            assert "$7.75" in content     # Max profit
            assert "$22.25" in content    # Max loss/Net cost
            assert "$172.25" in content   # Breakeven
    
    def test_formatting_with_missing_optional_fields(self, sample_pmcc_candidate):
        """Test formatting handles missing optional fields gracefully."""
        # Remove optional fields
        sample_pmcc_candidate.analysis.long_call.bid = None
        sample_pmcc_candidate.analysis.long_call.ask = None
        sample_pmcc_candidate.analysis.short_call.bid = None
        sample_pmcc_candidate.analysis.short_call.ask = None
        sample_pmcc_candidate.total_score = None
        
        # Should not crash
        whatsapp_template = WhatsAppFormatter.format_opportunity(sample_pmcc_candidate)
        email_template = EmailFormatter.format_opportunity(sample_pmcc_candidate)
        
        # Should handle missing values gracefully
        assert "N/A" in whatsapp_template.text_content or "Cost: N/A" in whatsapp_template.text_content
        assert "AAPL" in email_template.text_content  # Basic info should still be there