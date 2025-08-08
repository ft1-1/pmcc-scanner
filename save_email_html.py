#!/usr/bin/env python3
"""Save the email HTML to a file for inspection."""

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

# Call formatter
template = EmailFormatter._format_enhanced_email(enhanced_data)

# Save HTML to file
with open('test_email_output.html', 'w') as f:
    f.write(template.html_content)

print("Email HTML saved to test_email_output.html")
print(f"Subject: {template.subject}")
print(f"HTML size: {len(template.html_content)} characters")

# Also save text version
with open('test_email_output.txt', 'w') as f:
    f.write(template.text_content)
    
print("Email text saved to test_email_output.txt")