#!/usr/bin/env python3
"""Simple test script to verify financial data is properly included in Claude prompt"""

import json
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.config import get_settings
from src.analysis.scanner import PMCCScanner

def test_financial_data():
    """Test that financial data is properly included in the Claude prompt"""
    print("\n=== Testing Financial Data Fix ===\n")
    
    # Initialize components
    settings = get_settings()
    
    # Create scanner with provider factory
    print("Creating scanner with provider factory...")
    scanner = PMCCScanner.create_with_provider_factory(settings)
    
    # Force provider creation by getting status
    print("Initializing providers...")
    provider_status = scanner.get_provider_status()
    print(f"Provider status: {provider_status.get('available_providers', [])}")
    
    # Test with KSS stock
    symbol = 'KSS'
    print(f"Testing with symbol: {symbol}")
    
    try:
        # Debug provider availability
        print("\nAvailable providers:")
        if hasattr(scanner.provider_factory, 'providers'):
            for ptype, provider in scanner.provider_factory.providers.items():
                print(f"  - {ptype}: {type(provider).__name__}")
        
        # Get provider for enhanced data
        provider = scanner.provider_factory.get_provider('get_comprehensive_enhanced_data')
        if not provider:
            print("✗ No provider available for enhanced data")
            # Try to get any EODHD provider
            from src.api.data_provider import ProviderType
            eodhd_provider = scanner.provider_factory.providers.get(ProviderType.EODHD)
            if eodhd_provider:
                print("  Found EODHD provider, using it directly")
                provider = eodhd_provider
            else:
                return
            
        # Get enhanced data
        print("\n1. Fetching enhanced data from EODHD...")
        enhanced_data_response = provider.get_comprehensive_enhanced_data(symbol)
        
        if enhanced_data_response.is_success:
            enhanced_data = enhanced_data_response.data
            print("✓ Enhanced data fetched successfully")
            
            # Check if financial data is present
            fundamentals = enhanced_data.get('fundamentals', {})
            print(f"\nFundamentals type: {type(fundamentals)}")
            
            if isinstance(fundamentals, dict):
                # Check for financial statement sections
                sections_to_check = ['balance_sheet', 'income_statement', 'cash_flow', 'analyst_sentiment']
                
                print("\n2. Checking for financial statement sections:")
                for section in sections_to_check:
                    if section in fundamentals:
                        section_data = fundamentals[section]
                        if section_data and isinstance(section_data, dict):
                            # Count non-zero values
                            non_zero_count = sum(1 for v in section_data.values() if v and v != 0)
                            print(f"  ✓ {section}: Found with {len(section_data)} fields ({non_zero_count} non-zero)")
                            
                            # Show sample data
                            if section == 'balance_sheet':
                                print(f"     - Total Assets: ${section_data.get('total_assets', 'N/A')}M")
                                print(f"     - Total Debt: ${section_data.get('total_debt', 'N/A')}M")
                                print(f"     - Cash: ${section_data.get('cash_and_equivalents', 'N/A')}M")
                            elif section == 'cash_flow':
                                print(f"     - Operating Cash Flow: ${section_data.get('operating_cash_flow', 'N/A')}M")
                                print(f"     - Free Cash Flow: ${section_data.get('free_cash_flow', 'N/A')}M")
                        else:
                            print(f"  ✗ {section}: Empty or not a dict")
                    else:
                        print(f"  ✗ {section}: Not found in fundamentals")
                
                # Now test the Claude prompt generation
                print("\n3. Testing Claude prompt generation...")
                
                # Convert to dict format for scanner
                enhanced_dict = scanner._enhanced_stock_data_to_dict(enhanced_data)
                
                # Build a mock opportunity to test prompt generation
                from src.models.pmcc_models import PMCCOpportunity, PMCCParameters
                
                mock_opportunity = PMCCOpportunity(
                    symbol=symbol,
                    stock_price=50.0,
                    pmcc_params=PMCCParameters(
                        stock_price=50.0,
                        leaps_strike=40.0,
                        leaps_expiration=datetime(2025, 1, 17),
                        leaps_premium=15.0,
                        leaps_delta=0.8,
                        short_strike=55.0,
                        short_expiration=datetime(2024, 3, 15),
                        short_premium=2.0,
                        short_delta=0.3
                    ),
                    risk_metrics=None,
                    total_score=75.0,
                    enhanced_stock_data=enhanced_data
                )
                
                # Get Claude provider and build prompt
                from src.models.provider_config import ProviderType
                claude_provider = scanner.provider_factory.providers.get(ProviderType.CLAUDE)
                if claude_provider:
                    # Use the internal prompt builder
                    request_data = {
                        'symbol': symbol,
                        'opportunity': mock_opportunity,
                        'enhanced_stock_data': enhanced_dict
                    }
                    
                    prompt = claude_provider._build_single_opportunity_prompt(request_data)
                    
                    # Check if financial sections are in the prompt
                    print("\n4. Checking Claude prompt for financial data:")
                    
                    sections_in_prompt = {
                        'balance_sheet': '"balance_sheet":' in prompt,
                        'cash_flow': '"cash_flow":' in prompt,
                        'income_statement': '"income_statement":' in prompt,
                        'analyst_sentiment': '"analyst_sentiment":' in prompt,
                        'historical_prices': '"historical_prices":' in prompt
                    }
                    
                    for section, found in sections_in_prompt.items():
                        status = "✓" if found else "✗"
                        print(f"  {status} {section}: {'Found' if found else 'NOT FOUND'} in prompt")
                    
                    # Save prompt for inspection
                    with open('test_claude_prompt_financial_simple.json', 'w') as f:
                        f.write(prompt)
                    print("\n✓ Full prompt saved to test_claude_prompt_financial_simple.json for inspection")
                    
                    # Parse and check the actual data in the prompt
                    try:
                        # Extract the JSON portion
                        json_start = prompt.find('```json') + 7
                        json_end = prompt.find('```', json_start)
                        prompt_json_str = prompt[json_start:json_end].strip()
                        prompt_json = json.loads(prompt_json_str)
                        enhanced_data_in_prompt = prompt_json.get('enhanced_stock_data', {})
                        
                        print("\n5. Analyzing actual data in prompt:")
                        for section in ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment']:
                            if section in enhanced_data_in_prompt:
                                section_data = enhanced_data_in_prompt[section]
                                if section_data:
                                    non_zero = sum(1 for v in section_data.values() if v and v != 0)
                                    print(f"  ✓ {section}: {len(section_data)} fields ({non_zero} non-zero)")
                                else:
                                    print(f"  ⚠ {section}: Present but empty")
                            else:
                                print(f"  ✗ {section}: Missing from enhanced_stock_data")
                    except Exception as e:
                        print(f"\n⚠ Could not parse prompt JSON: {e}")
                
                else:
                    print("✗ Claude provider not available")
            else:
                print(f"✗ Fundamentals is not a dict: {type(fundamentals)}")
        else:
            print(f"✗ Failed to fetch enhanced data: {enhanced_data_response.error}")
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up providers
        if hasattr(scanner.provider_factory, 'providers'):
            for provider in scanner.provider_factory.providers.values():
                if hasattr(provider, 'close'):
                    provider.close()

if __name__ == "__main__":
    test_financial_data()