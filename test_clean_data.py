#!/usr/bin/env python3
"""Test script to verify clean data package for Claude."""

import json
import asyncio
from src.analysis.scanner import PMCCScanner
from src.api.provider_factory import DataProviderFactory
from src.config import get_settings

async def test_clean_data():
    """Test the clean data package being sent to Claude."""
    
    # Initialize scanner
    settings = get_settings()
    factory = DataProviderFactory(settings)
    scanner = PMCCScanner(factory)
    
    # Test data filtering
    test_data = {
        "fundamentals": {
            "market_cap": 1000000,  # Should be kept
            "pe_ratio": 0,  # Should be removed
            "revenue": 0.0,  # Should be removed
            "employees": "",  # Should be removed
            "sector": "Technology",  # Should be kept
            "dividend_yield": 0,  # Should be removed
            "beta": 1.2,  # Should be kept
            "empty_field": None,  # Should be removed
            "another_empty": "N/A",  # Should be removed
            "profit_margin": "0",  # Should be removed
            "debt_ratio": "0.0"  # Should be removed
        },
        "news": [
            {
                "date": "2025-08-07",
                "title": "Test Article",
                "content": "Full article content here",
                "sentiment": 0.5  # Should be removed
            }
        ],
        "empty_list": [],  # Should be removed
        "zero_value": 0,  # Should be removed
        "null_value": None  # Should be removed
    }
    
    # Apply filtering
    cleaned = scanner._filter_null_empty_fields(test_data)
    
    print("Original data keys:", list(test_data.keys()))
    print("Cleaned data keys:", list(cleaned.keys()))
    print("\nCleaned data:")
    print(json.dumps(cleaned, indent=2))
    
    # Verify news has no sentiment
    if 'news' in cleaned and cleaned['news']:
        print("\nNews article keys:", list(cleaned['news'][0].keys()))
        assert 'sentiment' not in cleaned['news'][0], "Sentiment should be removed from news!"
    
    # Verify fundamentals cleaned
    if 'fundamentals' in cleaned:
        fund_keys = list(cleaned['fundamentals'].keys())
        print("\nFundamentals keys after cleaning:", fund_keys)
        assert 'pe_ratio' not in cleaned['fundamentals'], "Zero pe_ratio should be removed!"
        assert 'revenue' not in cleaned['fundamentals'], "Zero revenue should be removed!"
        assert 'employees' not in cleaned['fundamentals'], "Empty employees should be removed!"
        assert 'dividend_yield' not in cleaned['fundamentals'], "Zero dividend_yield should be removed!"
        assert 'empty_field' not in cleaned['fundamentals'], "None values should be removed!"
        assert 'another_empty' not in cleaned['fundamentals'], "N/A values should be removed!"
        assert 'profit_margin' not in cleaned['fundamentals'], "String '0' should be removed!"
        assert 'debt_ratio' not in cleaned['fundamentals'], "String '0.0' should be removed!"
    
    # Test with real KSS data
    print("\n" + "="*50)
    print("Testing with real KSS data...")
    
    # Get enhanced data for KSS
    provider = await factory.get_provider('enhanced_eodhd')
    result = await provider.get_enhanced_stock_data('KSS')
    if result.status.is_ok and result.data:
        enhanced_data = result.data
        
        # Convert to dict for cleaning
        data_dict = enhanced_data.model_dump()
        
        # Apply cleaning
        cleaned_real = scanner._filter_null_empty_fields(data_dict)
        
        print("\nOriginal enhanced data keys:", list(data_dict.keys()))
        print("Cleaned enhanced data keys:", list(cleaned_real.keys()))
        
        # Check fundamentals
        if 'fundamentals' in cleaned_real:
            print(f"\nFundamentals fields: {len(cleaned_real['fundamentals'])} (from {len(data_dict.get('fundamentals', {}))})")
            
        # Check news
        if 'recent_news' in cleaned_real:
            print(f"News articles: {len(cleaned_real['recent_news'])}")
            if cleaned_real['recent_news']:
                print("First article keys:", list(cleaned_real['recent_news'][0].keys()))
                assert 'sentiment' not in cleaned_real['recent_news'][0], "Sentiment in real news!"
        
        print("\nSample of cleaned data:")
        print(json.dumps(cleaned_real, indent=2)[:1000] + "...")

if __name__ == "__main__":
    asyncio.run(test_clean_data())