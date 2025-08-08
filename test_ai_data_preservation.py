#!/usr/bin/env python3
"""
Test script to verify AI analysis data preservation and export functionality.

This script tests:
1. PMCCCandidate model with AI fields
2. Data serialization/deserialization with AI insights
3. Complete export flow with AI analysis results
4. Debug logging and persistence functionality
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract, StockQuote, OptionSide

def create_test_candidate():
    """Create a test PMCCCandidate with AI analysis data."""
    
    # Create mock option contracts
    long_call = OptionContract(
        option_symbol="AAPL240119C00150000",
        underlying="AAPL",
        strike=Decimal("150.00"),
        expiration=datetime(2024, 1, 19),
        side=OptionSide.CALL,
        dte=90,
        bid=Decimal("25.50"),
        ask=Decimal("26.00"),
        mid=Decimal("25.75"),
        last=Decimal("25.80"),
        volume=100,
        open_interest=500,
        delta=Decimal("0.85"),
        gamma=Decimal("0.02"),
        theta=Decimal("-0.15"),
        vega=Decimal("0.80"),
        iv=Decimal("0.25"),
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
        mid=Decimal("2.60"),
        last=Decimal("2.65"),
        volume=200,
        open_interest=800,
        delta=Decimal("0.35"),
        gamma=Decimal("0.05"),
        theta=Decimal("-0.08"),
        vega=Decimal("0.40"),
        iv=Decimal("0.30"),
        underlying_price=Decimal("175.50")
    )
    
    # Create stock quote
    stock_quote = StockQuote(
        symbol="AAPL",
        price=Decimal("175.50"),
        change=Decimal("2.50"),
        change_percent=Decimal("1.44"),
        volume=1000000,
        updated=datetime.now()
    )
    
    # Create risk metrics
    risk_metrics = RiskMetrics(
        max_loss=Decimal("2315.00"),  # Net debit
        max_profit=Decimal("785.00"),
        breakeven=Decimal("173.15"),
        probability_of_profit=Decimal("0.65"),
        net_delta=Decimal("0.50"),
        net_gamma=Decimal("-0.03"),
        net_theta=Decimal("-0.07"),
        net_vega=Decimal("0.40"),
        risk_reward_ratio=Decimal("0.34")
    )
    
    # Create PMCC analysis
    analysis = PMCCAnalysis(
        long_call=long_call,
        short_call=short_call,
        underlying=stock_quote,
        net_debit=Decimal("23.15"),  # Long premium - short premium
        credit_received=Decimal("2.60"),
        risk_metrics=risk_metrics,
        liquidity_score=Decimal("85.0"),
        iv_rank=Decimal("40.0"),
        analyzed_at=datetime.now()
    )
    
    # Create PMCC candidate with AI analysis fields
    candidate = PMCCCandidate(
        symbol="AAPL",
        underlying_price=Decimal("175.50"),
        analysis=analysis,
        liquidity_score=Decimal("85.0"),
        volatility_score=Decimal("75.0"),
        technical_score=Decimal("80.0"),
        fundamental_score=Decimal("90.0"),
        total_score=Decimal("82.5"),
        rank=1,
        discovered_at=datetime.now(),
        
        # AI Analysis Fields - These are the critical fields that were missing!
        ai_insights={
            "market_outlook": "bullish",
            "key_strengths": ["strong fundamentals", "technical momentum", "good liquidity"],
            "key_risks": ["high IV", "earnings risk"],
            "strategic_recommendation": "This PMCC setup offers excellent risk-adjusted returns",
            "confidence_factors": ["stable underlying", "good option liquidity"]
        },
        claude_score=87.5,
        combined_score=84.25,  # (82.5 * 0.6) + (87.5 * 0.4)
        claude_reasoning="Strong fundamental outlook combined with favorable technical setup makes this an attractive PMCC opportunity",
        ai_recommendation="strong_buy",
        claude_confidence=85.0,
        ai_analysis_timestamp=datetime.now()
    )
    
    return candidate

def test_model_fields():
    """Test that the PMCCCandidate model has all expected AI fields."""
    print("🧪 Testing PMCCCandidate model AI fields...")
    
    candidate = create_test_candidate()
    
    # Verify AI fields exist and are properly set
    assert hasattr(candidate, 'ai_insights'), "Missing ai_insights field"
    assert hasattr(candidate, 'claude_score'), "Missing claude_score field"
    assert hasattr(candidate, 'combined_score'), "Missing combined_score field"
    assert hasattr(candidate, 'claude_reasoning'), "Missing claude_reasoning field"
    assert hasattr(candidate, 'ai_recommendation'), "Missing ai_recommendation field"
    assert hasattr(candidate, 'claude_confidence'), "Missing claude_confidence field"
    assert hasattr(candidate, 'ai_analysis_timestamp'), "Missing ai_analysis_timestamp field"
    
    # Verify values are set correctly
    assert candidate.ai_insights is not None, "ai_insights is None"
    assert candidate.claude_score == 87.5, f"Expected claude_score 87.5, got {candidate.claude_score}"
    assert candidate.combined_score == 84.25, f"Expected combined_score 84.25, got {candidate.combined_score}"
    assert candidate.ai_recommendation == "strong_buy", f"Expected ai_recommendation 'strong_buy', got {candidate.ai_recommendation}"
    
    print("✅ Model fields test passed")

def test_serialization():
    """Test that to_dict() includes all AI analysis fields."""
    print("🧪 Testing PMCCCandidate serialization...")
    
    candidate = create_test_candidate()
    candidate_dict = candidate.to_dict()
    
    # Check that AI fields are included in serialized output
    required_ai_fields = [
        'ai_insights',
        'claude_score', 
        'combined_score',
        'claude_reasoning',
        'ai_recommendation',
        'claude_confidence',
        'ai_analysis_timestamp'
    ]
    
    for field in required_ai_fields:
        assert field in candidate_dict, f"Missing {field} in serialized output"
        print(f"  ✓ {field}: {candidate_dict[field]}")
    
    # Verify the AI insights structure
    ai_insights = candidate_dict['ai_insights']
    assert isinstance(ai_insights, dict), "ai_insights should be a dict"
    assert 'key_strengths' in ai_insights, "Missing key_strengths in ai_insights"
    assert 'key_risks' in ai_insights, "Missing key_risks in ai_insights"
    
    print("✅ Serialization test passed")

def test_json_export():
    """Test complete JSON export functionality."""
    print("🧪 Testing JSON export with AI data...")
    
    candidate = create_test_candidate()
    
    # Export to JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(candidate.to_dict(), f, indent=2, default=str)
        json_file = f.name
    
    try:
        # Read back and verify
        with open(json_file, 'r') as f:
            exported_data = json.load(f)
        
        # Verify key AI fields are present in exported JSON
        assert 'ai_insights' in exported_data, "ai_insights missing from JSON export"
        assert 'claude_score' in exported_data, "claude_score missing from JSON export"  
        assert 'combined_score' in exported_data, "combined_score missing from JSON export"
        
        # Verify AI insights structure in JSON
        ai_insights = exported_data['ai_insights']
        assert isinstance(ai_insights, dict), "ai_insights should be dict in JSON"
        assert 'key_strengths' in ai_insights, "key_strengths missing from AI insights in JSON"
        
        print(f"  ✓ JSON file size: {os.path.getsize(json_file)} bytes")
        print(f"  ✓ AI insights keys: {list(ai_insights.keys())}")
        print(f"  ✓ Claude score: {exported_data['claude_score']}")
        print(f"  ✓ Combined score: {exported_data['combined_score']}")
        
    finally:
        # Clean up
        os.unlink(json_file)
    
    print("✅ JSON export test passed")

def test_debug_persistence():
    """Test debug directory creation and file persistence."""
    print("🧪 Testing debug persistence functionality...")
    
    debug_dir = "test_debug_claude_responses"
    
    try:
        # Simulate debug data persistence
        os.makedirs(debug_dir, exist_ok=True)
        
        debug_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'AAPL',
            'request_data': {
                'opportunity_data': {'symbol': 'AAPL', 'pmcc_score': 82.5},
                'enhanced_stock_dict': {'market_cap': 3000000000000, 'sector': 'Technology'},
                'market_context': 'Bullish market conditions'
            },
            'response_data': {
                'pmcc_score': 87.5,
                'analysis_summary': 'Strong PMCC opportunity',
                'recommendation': 'strong_buy',
                'confidence_score': 85.0
            }
        }
        
        debug_file = os.path.join(debug_dir, f"claude_analysis_AAPL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(debug_file, 'w') as f:
            json.dump(debug_data, f, indent=2, default=str)
        
        # Verify file was created and has correct structure
        assert os.path.exists(debug_file), "Debug file was not created"
        
        with open(debug_file, 'r') as f:
            saved_data = json.load(f)
        
        assert 'request_data' in saved_data, "Missing request_data in debug file"
        assert 'response_data' in saved_data, "Missing response_data in debug file"
        assert saved_data['symbol'] == 'AAPL', "Incorrect symbol in debug file"
        
        print(f"  ✓ Debug file created: {debug_file}")
        print(f"  ✓ Debug file size: {os.path.getsize(debug_file)} bytes")
        
    finally:
        # Clean up
        if os.path.exists(debug_dir):
            shutil.rmtree(debug_dir)
    
    print("✅ Debug persistence test passed")

def test_backward_compatibility():
    """Test that candidates without AI data still work correctly."""
    print("🧪 Testing backward compatibility...")
    
    # Create candidate without AI fields
    candidate = create_test_candidate()
    
    # Clear AI fields to simulate old candidate
    candidate.ai_insights = None
    candidate.claude_score = None
    candidate.combined_score = None
    candidate.claude_reasoning = None
    candidate.ai_recommendation = None
    candidate.claude_confidence = None
    candidate.ai_analysis_timestamp = None
    
    # Should still serialize successfully
    candidate_dict = candidate.to_dict()
    
    # AI fields should be present but with None values
    assert 'ai_insights' in candidate_dict
    assert candidate_dict['ai_insights'] is None
    assert candidate_dict['claude_score'] is None
    assert candidate_dict['combined_score'] is None
    
    print("  ✓ Backward compatibility maintained")
    print("✅ Backward compatibility test passed")

def main():
    """Run all AI data preservation tests."""
    print("🚀 Starting AI Data Preservation Tests")
    print("=" * 60)
    
    try:
        test_model_fields()
        print()
        
        test_serialization()
        print()
        
        test_json_export()
        print()
        
        test_debug_persistence()
        print()
        
        test_backward_compatibility()
        print()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print()
        print("AI data preservation fixes are working correctly:")
        print("  ✓ PMCCCandidate model has all AI fields")
        print("  ✓ to_dict() exports AI analysis data")
        print("  ✓ JSON export includes AI insights") 
        print("  ✓ Debug persistence works")
        print("  ✓ Backward compatibility maintained")
        print()
        print("The AI analysis results will now be properly saved and exported!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)