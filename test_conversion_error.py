#!/usr/bin/env python3
"""Test the exact conversion error"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Test data that mimics comprehensive enhanced data
test_data = {
    'live_price': [{
        'code': 'KSS.US',
        'close': 11.35,
        'change': -0.5,
        'change_p': -4.2,
        'volume': 1000000
    }],
    'fundamentals': {
        'company_info': {
            'market_cap_mln': 1300
        },
        'financial_health': {
            'pe_ratio': 10.5
        }
    },
    'technical_indicators': {
        'rsi': 'string_instead_of_list'  # This might be the issue
    }
}

# Now test the problematic code
try:
    tech_data = test_data['technical_indicators']
    for indicator_name, indicator_data in tech_data.items():
        print(f"\nProcessing {indicator_name}:")
        print(f"  Type: {type(indicator_data)}")
        print(f"  Value: {indicator_data}")
        
        if indicator_data and isinstance(indicator_data, list) and len(indicator_data) > 0:
            print("  Is a list with data")
            latest = indicator_data[0] if isinstance(indicator_data[0], dict) else indicator_data[-1]
            print(f"  Latest type: {type(latest)}")
        else:
            print("  Not a list or empty")
            
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

# Test with actual string.get() error
print("\n\nTesting string.get() error:")
test_string = "I am a string"
try:
    result = test_string.get('something')
except Exception as e:
    print(f"Error: {e}")
    print(f"This is the error we're looking for!")