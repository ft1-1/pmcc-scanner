#!/usr/bin/env python3
"""Debug script to verify PMCC scoring calculations."""

import os
from src.config import get_settings

# Example scenario based on user's test
def debug_scoring():
    print("=" * 80)
    print("PMCC SCORING DEBUG")
    print("=" * 80)
    
    # Get current settings
    settings = get_settings()
    
    print("\n📊 Current Configuration:")
    print(f"  Traditional PMCC Weight: {settings.scan.traditional_pmcc_weight} ({settings.scan.traditional_pmcc_weight * 100}%)")
    print(f"  AI Analysis Weight: {settings.scan.ai_analysis_weight} ({settings.scan.ai_analysis_weight * 100}%)")
    print(f"  Min Combined Score: {settings.scan.min_combined_score}")
    print(f"  Min Claude Confidence: {settings.scan.min_claude_confidence}")
    
    # Test scenario: ANF
    print("\n🔍 Test Scenario: ANF")
    traditional_score = 50  # Example traditional PMCC score
    claude_score = 72
    claude_confidence = 65  # Example confidence
    
    # Calculate combined score
    combined_score = (traditional_score * settings.scan.traditional_pmcc_weight + 
                     claude_score * settings.scan.ai_analysis_weight)
    
    print(f"\n📈 Scoring Calculation:")
    print(f"  Traditional PMCC Score: {traditional_score}")
    print(f"  Claude AI Score: {claude_score}")
    print(f"  Claude Confidence: {claude_confidence}")
    print(f"\n  Combined Score = ({traditional_score} × {settings.scan.traditional_pmcc_weight}) + ({claude_score} × {settings.scan.ai_analysis_weight})")
    print(f"  Combined Score = {traditional_score * settings.scan.traditional_pmcc_weight} + {claude_score * settings.scan.ai_analysis_weight}")
    print(f"  Combined Score = {combined_score}")
    
    print(f"\n✅ Threshold Checks:")
    print(f"  Combined Score ({combined_score}) >= Min Score ({settings.scan.min_combined_score})? {combined_score >= settings.scan.min_combined_score}")
    print(f"  Claude Confidence ({claude_confidence}) >= Min Confidence ({settings.scan.min_claude_confidence})? {claude_confidence >= settings.scan.min_claude_confidence}")
    
    if combined_score >= settings.scan.min_combined_score and claude_confidence >= settings.scan.min_claude_confidence:
        print(f"\n✅ ANF WOULD BE SELECTED")
    else:
        print(f"\n❌ ANF WOULD BE REJECTED")
        if combined_score < settings.scan.min_combined_score:
            print(f"   - Combined score {combined_score} is below minimum {settings.scan.min_combined_score}")
        if claude_confidence < settings.scan.min_claude_confidence:
            print(f"   - Claude confidence {claude_confidence} is below minimum {settings.scan.min_claude_confidence}")
    
    # Show different weight scenarios
    print("\n📊 Other Weight Scenarios:")
    weights = [
        (0.6, 0.4, "Default"),
        (0.5, 0.5, "Equal"),
        (0.1, 0.9, "AI-Heavy (Your Config)"),
        (0.0, 1.0, "Pure AI")
    ]
    
    for trad_weight, ai_weight, label in weights:
        score = traditional_score * trad_weight + claude_score * ai_weight
        print(f"  {label}: {score:.1f} (Traditional: {trad_weight*100}%, AI: {ai_weight*100}%)")

if __name__ == "__main__":
    debug_scoring()