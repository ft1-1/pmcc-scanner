
"""
Basic working test for EmailFormatter.format_daily_summary() method.
"""

import pytest
from datetime import datetime
from decimal import Decimal

import sys
sys.path.append('src')

from src.notifications.formatters import EmailFormatter


class TestEmailFormatterDailySummary:
    """Test cases for the new EmailFormatter.format_daily_summary() method."""
    
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
    
    def test_format_daily_summary_without_metadata(self):
        """Test format_daily_summary when scan metadata is None."""
        candidates = []
        
        result = EmailFormatter.format_daily_summary(candidates, None)
        
        # Should still work without metadata
        assert result.subject is not None
        assert result.html_content is not None
        assert result.text_content is not None
        
        # Should have basic structure even without metadata
        assert "PMCC Daily Summary" in result.subject
