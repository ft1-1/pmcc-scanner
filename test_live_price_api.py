#!/usr/bin/env python3
"""Debug live price API issue."""

import os
from eodhd import APIClient
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('EODHD_API_TOKEN')
api = APIClient(api_key)

# Test different parameter combinations
test_date = '2025-08-07'
symbol = 'KSS'

print("Testing EODHD live price API...")
print(f"Date: {test_date}")
print(f"Symbol: {symbol}")
print()

# Test 1: With ticker parameter (as in example)
print("Test 1: Using ticker parameter")
try:
    result = api.get_live_stock_prices(
        date_from=test_date,
        date_to=test_date,
        ticker=symbol
    )
    print(f"✅ Success! Type: {type(result)}")
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 2: Without ticker parameter (just positional)
print("Test 2: Positional parameter for ticker")
try:
    result = api.get_live_stock_prices(
        test_date,
        test_date,
        symbol
    )
    print(f"✅ Success! Type: {type(result)}")
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 3: Check method signature
print("Test 3: Checking method signature")
import inspect
sig = inspect.signature(api.get_live_stock_prices)
print(f"Method signature: {sig}")
print(f"Parameters: {list(sig.parameters.keys())}")