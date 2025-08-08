#!/usr/bin/env python3
"""
Test script to verify what data is being sent to Claude AI.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.analysis.claude_integration import ClaudeIntegrationManager
from src.models.pmcc_models import PMCCCandidate
from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_claude_data_flow():
    """Test what data Claude AI receives."""
    print("\n" + "="*100)
    print("CLAUDE AI DATA FLOW TEST")
    print("="*100 + "\n")
    
    # Load a PMCC opportunity from the scan results
    scan_file = "data/pmcc_scan_20250806_220918.json"
    with open(scan_file, 'r') as f:
        scan_data = json.load(f)
    
    # Get KSS opportunity
    kss_opp = None
    for opp in scan_data['top_opportunities']:
        if opp['symbol'] == 'KSS':
            kss_opp = opp
            break
    
    if not kss_opp:
        print("❌ KSS not found in scan results")
        return
    
    print(f"1. PMCC OPPORTUNITY DATA FROM SCAN")
    print("-" * 50)
    print(f"Symbol: {kss_opp['symbol']}")
    print(f"Stock Price: ${kss_opp['underlying_price']}")
    print(f"Traditional Score: {kss_opp['total_score']}")
    print(f"\nLEAPS Call:")
    print(f"  Strike: ${kss_opp['long_call']['strike']}")
    print(f"  Delta: {kss_opp['long_call']['delta']}")
    print(f"  DTE: {kss_opp['long_call']['dte']}")
    print(f"\nShort Call:")
    print(f"  Strike: ${kss_opp['short_call']['strike']}")
    print(f"  Delta: {kss_opp['short_call']['delta']}")
    print(f"  DTE: {kss_opp['short_call']['dte']}")
    
    # Initialize Claude Integration Manager
    settings = get_settings()
    claude_manager = ClaudeIntegrationManager()
    
    # Test prepare_opportunities_for_claude
    print(f"\n2. TESTING prepare_opportunities_for_claude METHOD")
    print("-" * 50)
    
    # Pass the opportunity as a list
    prepared_data = claude_manager.prepare_opportunities_for_claude([kss_opp])
    
    # The method returns a dict with 'opportunities' key
    if isinstance(prepared_data, dict) and 'opportunities' in prepared_data:
        print("Prepared opportunities count:", len(prepared_data['opportunities']))
        opportunities_list = prepared_data['opportunities']
    else:
        print("Unexpected data format:", type(prepared_data))
        opportunities_list = []
    
    if opportunities_list:
        opp_data = opportunities_list[0]
        print(f"\nPrepared data for {opp_data['symbol']}:")
        print(f"  Has PMCC data: {'pmcc_data' in opp_data}")
        print(f"  Has enhanced data: {'enhanced_data' in opp_data}")
        
        if 'pmcc_data' in opp_data:
            pmcc = opp_data['pmcc_data']
            print(f"\n  PMCC Data:")
            print(f"    Stock Price: ${pmcc.get('underlying_price', 'N/A')}")
            print(f"    Net Debit: ${pmcc.get('net_debit', 'N/A')}")
            print(f"    Max Profit: ${pmcc.get('max_profit', 'N/A')}")
            print(f"    Risk/Reward: {pmcc.get('risk_reward_ratio', 'N/A')}")
            
            if 'long_call' in pmcc:
                print(f"\n    LEAPS Details:")
                print(f"      Strike: ${pmcc['long_call'].get('strike', 'N/A')}")
                print(f"      Delta: {pmcc['long_call'].get('delta', 'N/A')}")
                print(f"      Gamma: {pmcc['long_call'].get('gamma', 'N/A')}")
                print(f"      Theta: {pmcc['long_call'].get('theta', 'N/A')}")
                print(f"      Vega: {pmcc['long_call'].get('vega', 'N/A')}")
                print(f"      IV: {pmcc['long_call'].get('iv', 'N/A')}")
                print(f"      Volume: {pmcc['long_call'].get('volume', 'N/A')}")
                print(f"      Open Interest: {pmcc['long_call'].get('open_interest', 'N/A')}")
    
    # Export the prepared data
    print(f"\n3. EXPORTING PREPARED DATA")
    print("-" * 50)
    
    output_file = f"data/claude_prepared_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(prepared_data, f, indent=2, default=str)
    
    print(f"✅ Prepared data exported to: {output_file}")
    
    # Check what prompt would be sent
    print(f"\n4. CLAUDE AI PROMPT PREVIEW")
    print("-" * 50)
    
    # Mock enhanced data for testing
    mock_enhanced = {
        'KSS': {
            'fundamentals': {'pe_ratio': 10.55},
            'technical_indicators': {'sector': 'Consumer Cyclical'},
            'risk_metrics': {'institutional_ownership': 108.46}
        }
    }
    
    # Note: The new implementation combines PMCC and enhanced data internally
    prepared_with_enhanced = prepared_data  # Already includes all data
    
    # Get a preview of what Claude would see
    if prepared_with_enhanced:
        print("Data structure being sent to Claude:")
        print(f"  - Symbol: {prepared_with_enhanced[0]['symbol']}")
        print(f"  - Has PMCC data: {'pmcc_data' in prepared_with_enhanced[0]}")
        print(f"  - Has enhanced data: {'enhanced_data' in prepared_with_enhanced[0]}")
        
        if 'pmcc_data' in prepared_with_enhanced[0]:
            pmcc_keys = list(prepared_with_enhanced[0]['pmcc_data'].keys())
            print(f"  - PMCC data keys: {pmcc_keys[:5]}...")  # Show first 5 keys
        
        if 'enhanced_data' in prepared_with_enhanced[0]:
            enhanced_keys = list(prepared_with_enhanced[0]['enhanced_data'].keys())
            print(f"  - Enhanced data keys: {enhanced_keys[:5]}...")


if __name__ == "__main__":
    print("Starting Claude AI data flow test...")
    asyncio.run(test_claude_data_flow())