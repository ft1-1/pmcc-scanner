#!/usr/bin/env python3
"""Debug email formatting to find why PMCC section is missing."""

import json
from src.notifications.formatters import EmailFormatter

# Load the latest scan results
with open('data/pmcc_scan_20250808_172515.json', 'r') as f:
    scan_data = json.load(f)

opportunity = scan_data['top_opportunities'][0]

# Create enhanced data
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

print("DEBUG: Enhanced data structure:")
print(f"- Has 'analysis' key: {'analysis' in enhanced_data[0]}")
print(f"- Analysis type: {type(enhanced_data[0].get('analysis'))}")
print(f"- Has 'long_call' in analysis: {'long_call' in enhanced_data[0].get('analysis', {})}")
print(f"- Has 'short_call' in analysis: {'short_call' in enhanced_data[0].get('analysis', {})}")

# Also check for top-level keys
print(f"- Has top-level 'long_call': {'long_call' in enhanced_data[0]}")
print(f"- Has top-level 'short_call': {'short_call' in enhanced_data[0]}")

# Call formatter
template = EmailFormatter._format_enhanced_email(enhanced_data)

# Search for the PMCC section in HTML
html = template.html_content

# Look for different parts of the PMCC section
searches = [
    "PMCC Contract Details",
    "📊 PMCC Contract Details",
    "pmcc-details",
    "Long LEAPS Call",
    "📈 Long LEAPS Call"
]

print("\nHTML Search Results:")
for search in searches:
    if search in html:
        print(f"✅ Found: '{search}'")
        # Find context
        idx = html.find(search)
        context = html[max(0, idx-50):idx+100]
        print(f"   Context: ...{context}...")
    else:
        print(f"❌ Not found: '{search}'")

# Check the actual HTML structure around where contracts should be
print("\nDEBUG: Looking for where PMCC details should be added...")
if "Traditional Metrics" in html:
    idx = html.find("Traditional Metrics")
    print(f"Found 'Traditional Metrics' at position {idx}")
    # Show what comes after traditional metrics
    next_section = html[idx:idx+500]
    print("Next 500 chars after Traditional Metrics:")
    print(next_section)