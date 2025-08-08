#!/usr/bin/env python3
"""
Debug script to capture the exact Claude prompt being generated for KSS.

This script will:
1. Run a scan specifically for KSS
2. Capture the enhanced_stock_data structure 
3. Extract the exact prompt being sent to Claude
4. Save all data to files for analysis
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, '/home/deployuser/stock-options/pmcc-scanner/src')

from config.settings import get_settings
from analysis.scanner import PMCCScanner
from api.claude_client import ClaudeClient

# Configure logging to capture debug info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_kss_claude.log')
    ]
)

logger = logging.getLogger(__name__)


class PromptCapturingClaudeClient(ClaudeClient):
    """Claude client that captures the prompt without sending it to the API."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_prompt = None
        self.last_enhanced_stock_data = None
    
    async def analyze_single_opportunity(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        market_context: Dict[str, Any] = None
    ):
        """Capture the prompt but don't send to API."""
        
        # Store the data for analysis
        self.last_enhanced_stock_data = enhanced_stock_data.copy()
        
        # Build the prompt (this will trigger our logging)
        self.last_prompt = self._build_single_opportunity_prompt(
            opportunity_data, enhanced_stock_data, market_context
        )
        
        logger.info(f"Captured prompt for {opportunity_data.get('symbol', 'Unknown')}")
        logger.info(f"Prompt length: {len(self.last_prompt)} characters")
        
        # Return a mock response without calling the API
        return {
            'status': 'mock',
            'data': {
                'symbol': opportunity_data.get('symbol'),
                'pmcc_score': 999,  # Mock score to indicate this was captured
                'prompt_captured': True
            }
        }


async def debug_kss_prompt():
    """Debug the KSS prompt generation."""
    
    logger.info("=== STARTING KSS CLAUDE PROMPT DEBUG ===")
    
    try:
        # Get settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Create scanner with mock Claude client  
        scanner = PMCCScanner()
        
        # Replace the Claude client with our capturing version
        mock_claude = PromptCapturingClaudeClient()
        scanner.claude_client = mock_claude
        
        logger.info("Scanner initialized with capturing Claude client")
        
        # Run scan for KSS specifically
        logger.info("Starting scan for KSS...")
        
        # Override the scanner to focus on KSS only
        original_symbols = scanner.target_symbols if hasattr(scanner, 'target_symbols') else None
        scanner.target_symbols = ['KSS']
        
        # Run the scan
        results = await scanner.run_scan()
        
        logger.info(f"Scan completed with {len(results.get('opportunities', []))} opportunities")
        
        # Capture the data
        if mock_claude.last_prompt and mock_claude.last_enhanced_stock_data:
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save enhanced stock data
            enhanced_data_file = f'kss_enhanced_stock_data_{timestamp}.json'
            with open(enhanced_data_file, 'w') as f:
                json.dump(mock_claude.last_enhanced_stock_data, f, indent=2, default=str)
            logger.info(f"Enhanced stock data saved to {enhanced_data_file}")
            
            # Save the prompt
            prompt_file = f'kss_claude_prompt_{timestamp}.txt'
            with open(prompt_file, 'w') as f:
                f.write("=== KSS CLAUDE PROMPT DEBUG ===\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n")
                f.write(f"Prompt length: {len(mock_claude.last_prompt)} characters\n")
                f.write("\n" + "="*80 + "\n")
                f.write("FULL PROMPT:\n")
                f.write("="*80 + "\n")
                f.write(mock_claude.last_prompt)
            logger.info(f"Claude prompt saved to {prompt_file}")
            
            # Create a summary file
            summary_file = f'kss_debug_summary_{timestamp}.txt'
            with open(summary_file, 'w') as f:
                f.write("=== KSS CLAUDE PROMPT DEBUG SUMMARY ===\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
                
                f.write("ENHANCED STOCK DATA STRUCTURE:\n")
                f.write("-" * 40 + "\n")
                for key, value in mock_claude.last_enhanced_stock_data.items():
                    if isinstance(value, dict):
                        f.write(f"{key}: dict with {len(value)} keys\n")
                        f.write(f"  Keys: {list(value.keys())}\n")
                    elif isinstance(value, list):
                        f.write(f"{key}: list with {len(value)} items\n")
                        if value and isinstance(value[0], dict):
                            f.write(f"  Sample item keys: {list(value[0].keys())}\n")
                    else:
                        f.write(f"{key}: {type(value).__name__} = {str(value)[:100]}...\n")
                
                f.write(f"\nPROMPT LENGTH: {len(mock_claude.last_prompt)} characters\n")
                f.write(f"PROMPT PREVIEW (first 500 chars):\n{mock_claude.last_prompt[:500]}...\n")
            
            logger.info(f"Debug summary saved to {summary_file}")
            
            # Print key information
            print("\n" + "="*80)
            print("KSS CLAUDE PROMPT DEBUG COMPLETED")
            print("="*80)
            print(f"Enhanced data file: {enhanced_data_file}")
            print(f"Prompt file: {prompt_file}")
            print(f"Summary file: {summary_file}")
            print(f"Log file: debug_kss_claude.log")
            print("="*80)
            
            # Show key data structure info
            print("\nENHANCED STOCK DATA KEYS:")
            for key, value in mock_claude.last_enhanced_stock_data.items():
                if isinstance(value, dict):
                    print(f"  {key}: dict with {len(value)} keys")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                else:
                    print(f"  {key}: {type(value).__name__}")
            
            return {
                'enhanced_data_file': enhanced_data_file,
                'prompt_file': prompt_file,
                'summary_file': summary_file,
                'enhanced_stock_data': mock_claude.last_enhanced_stock_data,
                'prompt': mock_claude.last_prompt
            }
        else:
            logger.error("No prompt or enhanced data captured!")
            return None
            
    except Exception as e:
        logger.error(f"Error during KSS debug: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    # Run the debug
    result = asyncio.run(debug_kss_prompt())
    
    if result:
        print("\n✅ KSS Claude prompt debug completed successfully!")
        print(f"✅ Check the generated files for detailed analysis")
    else:
        print("\n❌ KSS Claude prompt debug failed!")
        sys.exit(1)