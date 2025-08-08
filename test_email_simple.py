#!/usr/bin/env python3
"""Simple test of email formatting with scan data."""

import json
from src.notifications.formatters import EmailFormatter

# Load the latest scan results
with open('data/pmcc_scan_20250808_172515.json', 'r') as f:
    scan_data = json.load(f)

# Extract the opportunity
opportunity = scan_data['top_opportunities'][0]

# Create enhanced data in the format expected by the formatter
enhanced_data = [{
    'symbol': opportunity['symbol'],
    'underlying_price': opportunity['underlying_price'],
    'net_debit': opportunity['net_debit'],
    'max_profit': opportunity['risk_metrics']['max_profit'],
    'pmcc_score': opportunity['total_score'],
    'liquidity_score': opportunity['liquidity_score'],
    'claude_score': opportunity['claude_score'],
    'combined_score': opportunity['combined_score'],
    'claude_confidence': opportunity['claude_confidence'],
    'claude_reasoning': opportunity['claude_reasoning'],
    'ai_recommendation': opportunity['ai_recommendation'],
    'claude_analyzed': True,
    'ai_insights': opportunity['ai_insights'],
    'analysis': {
        'long_call': opportunity['long_call'],
        'short_call': opportunity['short_call']
    }
}]

# Call the enhanced email formatter directly
template = EmailFormatter._format_enhanced_email(enhanced_data)

print("\n" + "="*80)
print("EMAIL PREVIEW - AI ENHANCED WITH PMCC CONTRACT DETAILS")
print("="*80 + "\n")

print(f"SUBJECT: {template.subject}\n")

# Check key sections
if "PMCC CONTRACT DETAILS" in template.html_content:
    print("✅ PMCC CONTRACT DETAILS section found")
    # Extract and show the contract details section
    start = template.html_content.find('<h3 style="color: #2c3e50; margin-top: 20px;">📊 PMCC Contract Details:</h3>')
    if start > 0:
        end = template.html_content.find('</table>', start) + 8
        contract_section = template.html_content[start:end]
        print("\nCONTRACT DETAILS HTML SECTION:")
        print("-"*50)
        print(contract_section[:500] + "...")
else:
    print("❌ PMCC CONTRACT DETAILS section NOT found")

if opportunity['long_call']['option_symbol'] in template.html_content:
    print("\n✅ LEAPS contract symbol found:", opportunity['long_call']['option_symbol'])
else:
    print("\n❌ LEAPS contract symbol NOT found")

if opportunity['short_call']['option_symbol'] in template.html_content:
    print("✅ Short call contract symbol found:", opportunity['short_call']['option_symbol'])
else:
    print("❌ Short call contract symbol NOT found")

if "KEY OPPORTUNITIES" in template.html_content or "key_opportunities" in template.html_content:
    print("\n✅ KEY OPPORTUNITIES section found")
else:
    print("\n❌ KEY OPPORTUNITIES section NOT found")

print("\n" + "="*80)
print("TEXT VERSION:")
print("="*80)
print(template.text_content[:1000] + "...")
print("="*80)