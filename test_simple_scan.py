#!/usr/bin/env python3
"""Simple test to check what's happening with KSS scan."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    # Run scanner in once mode
    sys.argv = ['test_simple_scan.py', '--mode', 'once']
    main()