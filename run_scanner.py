#!/usr/bin/env python3
"""
Simple wrapper script to run PMCC Scanner without import issues.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now we can import from the src directory
try:
    from src.main import PMCCApplication
    
    if __name__ == "__main__":
        # Parse basic arguments
        mode = "once"  # Default mode
        if len(sys.argv) > 1:
            if sys.argv[1] == "--help":
                print("""
PMCC Scanner - Poor Man's Covered Call opportunity scanner

Usage:
    python3 run_scanner.py [mode]
    
Modes:
    once    - Run scanner once and exit (default)
    daemon  - Run as daemon with scheduled scans
    test    - Test mode with limited data
    
Examples:
    python3 run_scanner.py
    python3 run_scanner.py once
    python3 run_scanner.py test
""")
                sys.exit(0)
            else:
                mode = sys.argv[1]
        
        # Create and run the application
        app = PMCCApplication()
        
        if mode == "once":
            print("Running PMCC Scanner once...")
            success = app.run_once()
            sys.exit(0 if success else 1)
        elif mode == "daemon":
            print("Starting PMCC Scanner daemon...")
            app.run_daemon()
        elif mode == "test":
            print("Running PMCC Scanner in test mode...")
            success = app.run_once()  # Use run_once for test mode
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown mode: {mode}")
            sys.exit(1)
            
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed and you're running from the project root directory.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)