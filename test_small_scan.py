#!/usr/bin/env python3
"""Test small scan with 2-3 stocks to verify Claude rate limiting and email format."""

import os
import logging
from datetime import datetime

# Setup logging to see all debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set custom symbols to limit the scan
os.environ['SCAN_CUSTOM_SYMBOLS'] = 'AAPL,MSFT,GOOGL'
os.environ['SCAN_MAX_OPPORTUNITIES'] = '3'
os.environ['SCAN_CLAUDE_ANALYSIS_ENABLED'] = 'true'

print(f"\nStarting small test scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("This will scan only 3 stocks: AAPL, MSFT, GOOGL")
print("Watch for:")
print("1. '60 seconds before next Claude API call' messages between analyses")
print("2. 'Using AI-enhanced email format' message when sending notifications")
print("\n" + "="*60 + "\n")

# Import and run the scanner
from src.main import PMCCApplication

app = PMCCApplication()
success = app.run_once()

if success:
    print("\n✅ Test scan completed successfully!")
else:
    print("\n❌ Test scan failed!")

print(f"\nTest completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")