#!/usr/bin/env python3
"""Test script to verify ANF scoring issue."""

import os
from dataclasses import dataclass
from typing import Optional
from src.config import get_settings

@dataclass
class TestOpportunity:
    """Mock opportunity for testing."""
    symbol: str
    total_score: float
    claude_score: Optional[float] = None
    combined_score: Optional[float] = None
    claude_confidence: Optional[float] = None
    ai_insights: Optional[dict] = None

def test_scoring_logic():
    """Test the scoring logic that should be happening."""
    print("=" * 80)
    print("ANF SCORING TEST")
    print("=" * 80)
    
    settings = get_settings()
    
    # Create test opportunity
    anf = TestOpportunity(
        symbol="ANF",
        total_score=50.0  # Example traditional score
    )
    
    # Simulate Claude analysis result
    claude_result = {
        'pmcc_score': 72,
        'confidence_score': 65,
        'analysis_summary': 'Test analysis',
        'recommendation': 'buy'
    }
    
    print(f"\n1️⃣ Initial State:")
    print(f"   Symbol: {anf.symbol}")
    print(f"   Traditional PMCC Score: {anf.total_score}")
    print(f"   Claude Score: None")
    print(f"   Combined Score: None")
    
    # Simulate what scanner.py does
    anf.ai_insights = claude_result
    anf.claude_score = claude_result.get('pmcc_score', 0)
    anf.claude_confidence = claude_result.get('confidence_score', 0)
    
    # Calculate combined score with configured weights
    traditional_weight = settings.scan.traditional_pmcc_weight
    ai_weight = settings.scan.ai_analysis_weight
    
    anf.combined_score = (
        float(anf.total_score) * traditional_weight + 
        claude_result.get('pmcc_score', 0) * ai_weight
    )
    
    print(f"\n2️⃣ After Claude Analysis:")
    print(f"   Claude Score: {anf.claude_score}")
    print(f"   Claude Confidence: {anf.claude_confidence}")
    print(f"   Combined Score: {anf.combined_score}")
    print(f"   Calculation: ({anf.total_score} × {traditional_weight}) + ({anf.claude_score} × {ai_weight}) = {anf.combined_score}")
    
    # Test the selection logic
    enhanced_opportunities = [anf]
    
    # Step 1: Filter for AI-analyzed opportunities
    ai_analyzed_opportunities = [
        opp for opp in enhanced_opportunities 
        if hasattr(opp, 'claude_score') and opp.claude_score is not None
    ]
    
    print(f"\n3️⃣ AI Analysis Filter:")
    print(f"   Has claude_score attribute? {hasattr(anf, 'claude_score')}")
    print(f"   claude_score is not None? {anf.claude_score is not None}")
    print(f"   Passes AI filter? {anf in ai_analyzed_opportunities}")
    
    # Step 2: Check thresholds
    min_combined_score = settings.scan.min_combined_score
    min_claude_confidence = settings.scan.min_claude_confidence
    
    score = getattr(anf, 'combined_score', None) or float(anf.total_score)
    confidence = getattr(anf, 'claude_confidence', 0)
    
    passes_score = score >= min_combined_score
    passes_confidence = confidence >= min_claude_confidence
    
    print(f"\n4️⃣ Threshold Checks:")
    print(f"   Combined Score: {score} >= {min_combined_score}? {passes_score}")
    print(f"   Claude Confidence: {confidence} >= {min_claude_confidence}? {passes_confidence}")
    
    if passes_score and passes_confidence:
        print(f"\n✅ RESULT: ANF would be SELECTED")
    else:
        print(f"\n❌ RESULT: ANF would be REJECTED")
        if not passes_score:
            print(f"   - Failed score threshold: {score} < {min_combined_score}")
        if not passes_confidence:
            print(f"   - Failed confidence threshold: {confidence} < {min_claude_confidence}")
    
    # Debug: Check what might be going wrong
    print(f"\n5️⃣ Debugging Info:")
    print(f"   Type of combined_score: {type(anf.combined_score)}")
    print(f"   Type of claude_score: {type(anf.claude_score)}")
    print(f"   Type of claude_confidence: {type(anf.claude_confidence)}")
    
    # Check for any edge cases
    if anf.claude_score == 0:
        print("   ⚠️  WARNING: Claude score is 0 - API might have returned empty/failed result")
    if anf.claude_confidence == 0:
        print("   ⚠️  WARNING: Claude confidence is 0 - API might have returned empty/failed result")

if __name__ == "__main__":
    test_scoring_logic()