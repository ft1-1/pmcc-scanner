#!/usr/bin/env python3
"""Test script to verify Claude rate limiting and enhanced email fixes."""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_claude_rate_limiting():
    """Test that Claude API calls have 60-second delay."""
    print("\n" + "="*60)
    print("TEST 1: Claude API Rate Limiting")
    print("="*60)
    
    # Check if the delay is implemented
    with open('src/analysis/scanner.py', 'r') as f:
        content = f.read()
        if 'time.sleep(60)' in content and 'Waiting 60 seconds before next Claude API call' in content:
            print("✅ SUCCESS: 60-second delay implemented for Claude API calls")
            print("   - Found time.sleep(60) in scanner.py")
            print("   - Found appropriate logging message")
            return True
        else:
            print("❌ FAILED: 60-second delay not found in scanner.py")
            return False

def test_enhanced_email_configuration():
    """Test that enhanced email format is enabled."""
    print("\n" + "="*60)
    print("TEST 2: Enhanced Email Configuration")
    print("="*60)
    
    # Check notification manager
    with open('src/notifications/notification_manager.py', 'r') as f:
        content = f.read()
        
        checks = {
            'debug_logging': 'Enhanced format decision:' in content,
            'ai_format_logging': 'Using AI-enhanced email format with Claude insights' in content,
            'create_from_env': "ai_enhanced_notifications=os.getenv('AI_ENHANCED_NOTIFICATIONS', 'true')" in content
        }
        
        all_passed = True
        for check_name, check_result in checks.items():
            if check_result:
                print(f"✅ {check_name}: PASSED")
            else:
                print(f"❌ {check_name}: FAILED")
                all_passed = False
        
        return all_passed

def test_env_variables():
    """Check environment variables."""
    print("\n" + "="*60)
    print("TEST 3: Environment Variables")
    print("="*60)
    
    # Check if AI_ENHANCED_NOTIFICATIONS is not explicitly set to false
    ai_enhanced = os.getenv('AI_ENHANCED_NOTIFICATIONS', 'true').lower()
    force_traditional = os.getenv('FORCE_TRADITIONAL_NOTIFICATIONS', 'false').lower()
    
    print(f"AI_ENHANCED_NOTIFICATIONS: {ai_enhanced} (default: true)")
    print(f"FORCE_TRADITIONAL_NOTIFICATIONS: {force_traditional} (default: false)")
    
    if ai_enhanced == 'true' and force_traditional == 'false':
        print("✅ Environment variables configured correctly for enhanced emails")
        return True
    else:
        print("❌ Environment variables may prevent enhanced emails")
        return False

def main():
    """Run all tests."""
    print(f"\nRunning PMCC Scanner Fix Verification Tests")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'Claude Rate Limiting': test_claude_rate_limiting(),
        'Enhanced Email Config': test_enhanced_email_configuration(),
        'Environment Variables': test_env_variables()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Fixes are properly implemented!")
        print("\nNext steps:")
        print("1. Run the scanner with: python3 src/main.py --mode once")
        print("2. Monitor logs for:")
        print("   - 'Waiting 60 seconds before next Claude API call' messages")
        print("   - 'Using AI-enhanced email format with Claude insights' message")
        print("3. Check email to verify AI insights are included")
    else:
        print("❌ SOME TESTS FAILED - Please review the implementation")
    print("="*60)

if __name__ == "__main__":
    main()