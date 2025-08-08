#!/usr/bin/env python3
"""Test to capture the exact Claude prompt being sent."""

import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Monkey patch the Claude client to capture prompts
original_analyze_method = None
captured_prompts = []

def capture_analyze_single_opportunity(self, opportunity_data, enhanced_stock_data, market_context):
    """Capture the prompt before sending to Claude."""
    # Build the prompt
    prompt = self._build_single_opportunity_prompt(opportunity_data, enhanced_stock_data, market_context)
    
    # Save the prompt
    captured_prompts.append({
        'symbol': opportunity_data.get('symbol', 'Unknown'),
        'prompt': prompt,
        'opportunity_data': opportunity_data
    })
    
    # Save to file for review
    with open('captured_claude_prompt.json', 'w') as f:
        json.dump({
            'prompt': prompt,
            'opportunity_data': opportunity_data,
            'enhanced_stock_data': enhanced_stock_data,
            'market_context': market_context
        }, f, indent=2, default=str)
    
    print(f"\n📝 Captured Claude prompt for {opportunity_data.get('symbol', 'Unknown')}")
    print(f"   Prompt length: {len(prompt)} characters")
    
    # Call the original method
    return original_analyze_method(self, opportunity_data, enhanced_stock_data, market_context)

# Apply the monkey patch
from src.api.claude_client import ClaudeClient
original_analyze_method = ClaudeClient.analyze_single_opportunity
ClaudeClient.analyze_single_opportunity = capture_analyze_single_opportunity

# Now run a scan
from src.main import main

if __name__ == "__main__":
    # Run scanner in once mode
    sys.argv = ['test_claude_prompt.py', '--mode', 'once']
    main()
    
    # After scan, show captured prompts
    if captured_prompts:
        print("\n" + "="*80)
        print("📋 CAPTURED CLAUDE PROMPTS")
        print("="*80)
        for i, capture in enumerate(captured_prompts, 1):
            print(f"\n{i}. Symbol: {capture['symbol']}")
            print(f"   Prompt length: {len(capture['prompt'])} characters")
            print("\n   First 500 characters of prompt:")
            print("   " + "-"*60)
            print(capture['prompt'][:500])
            print("   " + "-"*60)