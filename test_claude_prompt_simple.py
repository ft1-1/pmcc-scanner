#!/usr/bin/env python3
"""Simple test of Claude prompt generation with financial data"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.config import get_settings

def test_claude_prompt():
    """Test that Claude prompt includes all financial data"""
    print("\n=== Testing Claude Prompt with Financial Data ===\n")
    
    # Load the enhanced data we saved from the previous test
    try:
        with open('test_enhanced_data.json', 'r') as f:
            enhanced_data = json.load(f)
    except FileNotFoundError:
        print("✗ test_enhanced_data.json not found. Run test_financial_direct.py first.")
        return
        
    print("✓ Loaded enhanced data from previous test")
    
    # Check fundamentals
    fundamentals = enhanced_data.get('fundamentals', {})
    financial_sections = ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment']
    found_sections = [s for s in financial_sections if s in fundamentals]
    print(f"\nFundamentals has {len(found_sections)} financial sections: {', '.join(found_sections)}")
    
    # Show what we have in fundamentals
    print("\nFinancial data in fundamentals:")
    for section in financial_sections:
        if section in fundamentals:
            data = fundamentals[section]
            if isinstance(data, dict):
                non_zero = sum(1 for v in data.values() if v and v != 0)
                print(f"  ✓ {section}: {len(data)} fields ({non_zero} non-zero)")
                # Show a sample field
                if data:
                    first_key = list(data.keys())[0]
                    print(f"     Sample: {first_key} = {data[first_key]}")
            else:
                print(f"  ⚠ {section}: Not a dict")
        else:
            print(f"  ✗ {section}: Missing")
            
    # Now test scanner's conversion
    print("\nTesting scanner's _enhanced_stock_data_to_dict conversion...")
    
    from src.analysis.scanner import PMCCScanner
    settings = get_settings()
    scanner = PMCCScanner(None, settings)
    
    # Convert to dict
    enhanced_dict = scanner._enhanced_stock_data_to_dict(enhanced_data)
    
    # Check what sections made it through the conversion
    print("\nAfter scanner conversion:")
    for section in financial_sections:
        if section in enhanced_dict:
            data = enhanced_dict[section]
            if isinstance(data, dict):
                non_zero = sum(1 for v in data.values() if v and v != 0)
                print(f"  ✓ {section}: {len(data)} fields ({non_zero} non-zero)")
            else:
                print(f"  ⚠ {section}: Present but not a dict")
        else:
            print(f"  ✗ {section}: Missing from enhanced_dict")
            
    # Save the converted data
    with open('test_enhanced_dict.json', 'w') as f:
        json.dump(enhanced_dict, f, indent=2, default=str)
    print("\n✓ Converted data saved to test_enhanced_dict.json")
    
    # Create a mock request data structure
    request_data = {
        'symbol': 'KSS',
        'opportunity': {
            'symbol': 'KSS',
            'total_score': 75.0
        },
        'enhanced_stock_data': enhanced_dict
    }
    
    # Now test Claude prompt building if Claude is configured
    settings = get_settings()
    if settings.claude and settings.claude.api_key:
        print("\nTesting Claude prompt generation...")
        
        from src.api.claude_client import ClaudeClient
        from src.api.data_provider import ProviderType
        
        claude_config = {
            'api_key': settings.claude.api_key,
            'max_tokens': getattr(settings.claude, 'max_tokens', 4000),
            'temperature': getattr(settings.claude, 'temperature', 0.7),
            'rate_limit': getattr(settings.claude, 'rate_limit', 10),
            'retry_max_attempts': getattr(settings.claude, 'retry_max_attempts', 3),
            'retry_delay': getattr(settings.claude, 'retry_delay', 1.0),
            'daily_request_limit': getattr(settings.claude, 'daily_request_limit', 1000),
            'daily_cost_limit': getattr(settings.claude, 'daily_cost_limit', 50.0)
        }
        
        claude_client = ClaudeClient(ProviderType.CLAUDE, claude_config)
        
        # Build prompt
        prompt = claude_client._build_single_opportunity_prompt(
            opportunity_data={'symbol': 'KSS', 'total_score': 75.0},
            enhanced_stock_data=enhanced_dict
        )
        
        # Check if financial sections are in the prompt
        print("\nChecking Claude prompt for financial data:")
        
        sections_to_check = ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment', 'historical_prices']
        
        for section in sections_to_check:
            pattern = f'"{section}":'
            found = pattern in prompt
            status = "✓" if found else "✗"
            print(f"  {status} {section}: {'Found' if found else 'NOT FOUND'} in prompt")
        
        # Save prompt
        with open('test_claude_prompt_final.txt', 'w') as f:
            f.write(prompt)
        print("\n✓ Full prompt saved to test_claude_prompt_final.txt")
        
        # Try to parse the JSON in the prompt
        try:
            json_start = prompt.find('```json') + 7
            json_end = prompt.find('```', json_start)
            prompt_json_str = prompt[json_start:json_end].strip()
            prompt_json = json.loads(prompt_json_str)
            
            enhanced_in_prompt = prompt_json.get('enhanced_stock_data', {})
            
            print("\nFinancial sections in parsed prompt JSON:")
            for section in financial_sections:
                if section in enhanced_in_prompt:
                    data = enhanced_in_prompt[section]
                    if isinstance(data, dict):
                        non_zero = sum(1 for v in data.values() if v and v != 0)
                        print(f"  ✓ {section}: {len(data)} fields ({non_zero} non-zero)")
                    else:
                        print(f"  ⚠ {section}: Present but not a dict")
                else:
                    print(f"  ✗ {section}: Missing from enhanced_stock_data in prompt")
                    
        except Exception as e:
            print(f"\n⚠ Error parsing prompt JSON: {e}")
    else:
        print("\n⚠ Claude not configured, skipping prompt generation test")

if __name__ == "__main__":
    test_claude_prompt()