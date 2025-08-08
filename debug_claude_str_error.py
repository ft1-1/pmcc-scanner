#!/usr/bin/env python3
"""Debug the 'str' object has no attribute 'get' error"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.claude_client import ClaudeClient

# Simple test data
opportunity_data = {
    'symbol': 'KSS',
    'underlying_price': 11.35,
    'strategy_details': {
        'net_debit': 3.2,
        'credit_received': 0,
        'max_profit': 100,
        'max_loss': 320,
        'breakeven_price': 13.2,
        'risk_reward_ratio': 0.31
    }
}

enhanced_stock_dict = {
    'quote': {
        'symbol': 'KSS',
        'last': 11.35,
        'change': -0.5,
        'change_percent': -4.2,
        'volume': 1000000,
        'market_cap': 1300000000
    },
    'fundamentals': {
        'market_capitalization': 1300000000,
        'pe_ratio': 10.5,
        'roe': 3.2,
        'profit_margin': 0.8
    }
}

market_context = {
    'volatility_regime': 'normal',
    'market_sentiment': 'neutral'
}

# Test the prompt building
try:
    # Initialize Claude client with dummy key
    os.environ['CLAUDE_API_KEY'] = 'test-key'
    client = ClaudeClient()
    
    # Test building the prompt
    print("Testing _build_single_opportunity_prompt...")
    prompt = client._build_single_opportunity_prompt(
        opportunity_data,
        enhanced_stock_dict,
        market_context
    )
    
    print(f"Prompt built successfully! Length: {len(prompt)}")
    
    # Save prompt for inspection
    with open('data/test_claude_prompt.txt', 'w') as f:
        f.write(prompt)
    print("Prompt saved to data/test_claude_prompt.txt")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
    # Try to identify which parameter caused the issue
    print("\nTesting individual parameters...")
    for name, param in [
        ('opportunity_data', opportunity_data),
        ('enhanced_stock_dict', enhanced_stock_dict),
        ('market_context', market_context)
    ]:
        print(f"\n{name}:")
        print(f"  Type: {type(param)}")
        if isinstance(param, dict):
            print(f"  Keys: {list(param.keys())}")
        elif isinstance(param, str):
            print(f"  String value: '{param[:50]}...'")