#!/usr/bin/env python3
"""Test the data flow from EODHD to Claude prompt"""

import json
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.config import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.data_provider import ProviderType
from src.analysis.scanner import PMCCScanner

async def test_data_flow():
    """Test data flow from EODHD through scanner to Claude"""
    print("\n=== Testing Data Flow ===\n")
    
    settings = get_settings()
    
    # 1. Get data from EODHD
    print("1. Fetching from EODHD...")
    eodhd_config = {
        'api_token': settings.eodhd.api_token,
        'enable_caching': True,
        'cache_ttl_hours': 24
    }
    
    provider = EnhancedEODHDProvider(ProviderType.EODHD, eodhd_config)
    response = await provider.get_comprehensive_enhanced_data('KSS')
    
    if response.is_success:
        enhanced_data = response.data
        fundamentals = enhanced_data.get('fundamentals', {})
        
        print("\nEODHD fundamentals sections:")
        for section in ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment']:
            if section in fundamentals:
                print(f"  ✓ {section}: {len(fundamentals[section])} fields")
            else:
                print(f"  ✗ {section}: Not found")
                
        # 2. Convert through scanner
        print("\n2. Converting through scanner...")
        scanner = PMCCScanner(None, settings)
        enhanced_dict = scanner._enhanced_stock_data_to_dict(enhanced_data)
        
        print("\nScanner output sections:")
        for section in ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment']:
            if section in enhanced_dict:
                data = enhanced_dict[section]
                if isinstance(data, dict):
                    non_zero = sum(1 for v in data.values() if v and v != 0)
                    print(f"  ✓ {section}: {len(data)} fields ({non_zero} non-zero)")
                    # Show first 3 fields
                    for i, (k, v) in enumerate(data.items()):
                        if i < 3:
                            print(f"     - {k}: {v}")
                else:
                    print(f"  ⚠ {section}: Not a dict")
            else:
                print(f"  ✗ {section}: Not found")
                
        # 3. Build Claude prompt
        print("\n3. Building Claude prompt...")
        from src.api.claude_client import ClaudeClient
        
        claude_config = {
            'api_key': settings.claude.api_key if settings.claude else 'dummy',
            'max_tokens': 4000,
            'temperature': 0.7,
            'rate_limit': 10,
            'retry_max_attempts': 3,
            'retry_delay': 1.0,
            'daily_request_limit': 1000,
            'daily_cost_limit': 50.0
        }
        
        claude_client = ClaudeClient(ProviderType.CLAUDE, claude_config)
        
        # Build prompt
        opportunity_data = {'symbol': 'KSS', 'total_score': 75.0}
        prompt = claude_client._build_single_opportunity_prompt(
            opportunity_data,
            enhanced_dict
        )
        
        # Check what's in the prompt
        print("\nChecking prompt content:")
        sections_to_find = [
            ('BALANCE SHEET STRENGTH:', 'balance_sheet'),
            ('CASH FLOW ANALYSIS:', 'cash_flow'),
            ('INCOME STATEMENT:', 'income_statement'),
            ('ANALYST SENTIMENT:', 'analyst_sentiment')
        ]
        
        for prompt_section, data_key in sections_to_find:
            if prompt_section in prompt:
                # Find the line
                lines = prompt.split('\n')
                for i, line in enumerate(lines):
                    if prompt_section in line:
                        print(f"  ✓ {prompt_section}")
                        # Show the next line which should have the data
                        if i + 1 < len(lines):
                            data_line = lines[i + 1].strip()
                            if data_line.startswith('-'):
                                print(f"     {data_line[:100]}...")
                            else:
                                print(f"     (no data line found)")
                        break
            else:
                print(f"  ✗ {prompt_section} NOT FOUND")
                
        # Save debug files
        with open('debug_enhanced_dict.json', 'w') as f:
            json.dump(enhanced_dict, f, indent=2, default=str)
        print("\n✓ Enhanced dict saved to debug_enhanced_dict.json")
        
        with open('debug_claude_prompt.txt', 'w') as f:
            f.write(prompt)
        print("✓ Claude prompt saved to debug_claude_prompt.txt")
        
    else:
        print(f"✗ Failed to fetch data: {response.error}")
        
    await provider.close()

if __name__ == "__main__":
    asyncio.run(test_data_flow())