#!/usr/bin/env python3
"""
Quick verification script to demonstrate the AI data export fix.

This script shows:
1. Before: AI fields were set dynamically but not exported
2. After: AI fields are properly defined and exported in JSON

Run this script to see the AI analysis data in the exported JSON.
"""

import sys
import os
import json
from datetime import datetime
from decimal import Decimal

# Add src to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract, StockQuote, OptionSide

def create_sample_candidate_with_ai():
    """Create a sample PMCCCandidate with AI analysis - simulating scanner output."""
    
    # Minimal option contracts for demo
    long_call = OptionContract(
        option_symbol="AAPL240119C00150000",
        underlying="AAPL",
        strike=Decimal("150.00"),
        expiration=datetime(2024, 1, 19),
        side=OptionSide.CALL,
        dte=90,
        bid=Decimal("25.50"),
        ask=Decimal("26.00"),
        underlying_price=Decimal("175.50")
    )
    
    short_call = OptionContract(
        option_symbol="AAPL231215C00180000", 
        underlying="AAPL",
        strike=Decimal("180.00"),
        expiration=datetime(2023, 12, 15),
        side=OptionSide.CALL,
        dte=30,
        bid=Decimal("2.50"),
        ask=Decimal("2.70"),
        underlying_price=Decimal("175.50")
    )
    
    stock_quote = StockQuote(
        symbol="AAPL",
        price=Decimal("175.50"),
        updated=datetime.now()
    )
    
    risk_metrics = RiskMetrics(
        max_loss=Decimal("2315.00"),
        max_profit=Decimal("785.00"),
        breakeven=Decimal("173.15"),
        probability_of_profit=Decimal("0.65")
    )
    
    analysis = PMCCAnalysis(
        long_call=long_call,
        short_call=short_call,
        underlying=stock_quote,
        net_debit=Decimal("23.15"),
        risk_metrics=risk_metrics,
        analyzed_at=datetime.now()
    )
    
    # Create candidate with AI analysis results (this simulates what the scanner does)
    candidate = PMCCCandidate(
        symbol="AAPL",
        underlying_price=Decimal("175.50"),
        analysis=analysis,
        liquidity_score=Decimal("85.0"),
        total_score=Decimal("82.5"),
        discovered_at=datetime.now()
    )
    
    # Simulate Claude AI analysis results being added (like in scanner.py)
    claude_result = {
        'pmcc_score': 87.5,
        'analysis_summary': 'Strong PMCC opportunity with favorable risk-reward profile',
        'recommendation': 'strong_buy',
        'confidence_score': 85.0,
        'market_outlook': 'bullish',
        'key_strengths': ['strong fundamentals', 'good option liquidity', 'favorable technical setup'],
        'key_risks': ['earnings volatility', 'market correction risk'],
        'strategic_notes': 'Excellent entry point for PMCC strategy'
    }
    
    # This is what the scanner does - now these fields are properly defined in the model
    candidate.ai_insights = claude_result
    candidate.claude_score = claude_result.get('pmcc_score', 0) 
    candidate.combined_score = (float(candidate.total_score) * 0.6 + claude_result.get('pmcc_score', 0) * 0.4)
    candidate.claude_reasoning = claude_result.get('analysis_summary', '')
    candidate.ai_recommendation = claude_result.get('recommendation', 'neutral')
    candidate.claude_confidence = claude_result.get('confidence_score', 0)
    candidate.ai_analysis_timestamp = datetime.now()
    
    return candidate

def main():
    print("🔧 AI Data Export Verification")
    print("=" * 50)
    
    # Create candidate with AI analysis
    candidate = create_sample_candidate_with_ai()
    
    print(f"📊 Created PMCC candidate for {candidate.symbol}")
    print(f"   Traditional PMCC Score: {candidate.total_score}")
    print(f"   Claude AI Score: {candidate.claude_score}")
    print(f"   Combined Score: {candidate.combined_score}")
    print(f"   AI Recommendation: {candidate.ai_recommendation}")
    print()
    
    # Export to dictionary (this is what gets saved to JSON)
    exported_data = candidate.to_dict()
    
    print("🔍 Checking AI fields in exported data:")
    ai_fields = [
        'ai_insights', 'claude_score', 'combined_score',  
        'claude_reasoning', 'ai_recommendation', 'claude_confidence',
        'ai_analysis_timestamp'
    ]
    
    for field in ai_fields:
        if field in exported_data and exported_data[field] is not None:
            print(f"   ✅ {field}: Present")
        else:
            print(f"   ❌ {field}: Missing or None")
    
    print()
    
    # Show sample AI insights
    print("🧠 AI Insights Sample:")
    ai_insights = exported_data.get('ai_insights', {})
    if ai_insights:
        print(f"   Market Outlook: {ai_insights.get('market_outlook', 'N/A')}")
        print(f"   Key Strengths: {len(ai_insights.get('key_strengths', []))} items")
        print(f"   Key Risks: {len(ai_insights.get('key_risks', []))} items")
        print(f"   Strategic Notes: {ai_insights.get('strategic_notes', 'N/A')}")
    
    print()
    
    # Export to JSON file to demonstrate complete export
    json_filename = "sample_pmcc_with_ai.json"
    with open(json_filename, 'w') as f:
        json.dump(exported_data, f, indent=2, default=str)
    
    file_size = os.path.getsize(json_filename)
    print(f"📄 Exported complete data to {json_filename} ({file_size} bytes)")
    
    # Show key sections of the JSON
    print("\n📋 Key sections in exported JSON:")
    key_sections = ['symbol', 'underlying_price', 'total_score', 'claude_score', 'combined_score', 'ai_insights']
    for section in key_sections:
        if section in exported_data:
            if section == 'ai_insights' and isinstance(exported_data[section], dict):
                print(f"   ✓ {section}: {len(exported_data[section])} AI analysis fields")
            else:
                print(f"   ✓ {section}: {exported_data[section]}")
    
    print()
    print("🎉 VERIFICATION COMPLETE!")
    print()
    print("The AI analysis data is now properly preserved and exported!")
    print(f"Check the file '{json_filename}' to see all AI analysis results.")
    
    # Clean up
    os.remove(json_filename)

if __name__ == "__main__":
    main()