#!/usr/bin/env python3
"""Debug Claude score assignment."""

import json

# Load the most recent Claude response
with open('data/claude_submissions/claude_analysis_ANF_20250808_165617.json', 'r') as f:
    data = json.load(f)

claude_result = data['response_data']

print("Claude Result Debug:")
print(f"  pmcc_score: {claude_result.get('pmcc_score')}")
print(f"  confidence_score: {claude_result.get('confidence_score')}")  
print(f"  confidence_level: {claude_result.get('confidence_level')}")
print(f"  Type of pmcc_score: {type(claude_result.get('pmcc_score'))}")

# The issue might be that Claude is returning 'confidence_level' but the code is looking for 'confidence_score'
print("\nAll keys in response_data:")
for key in sorted(claude_result.keys()):
    print(f"  {key}: {claude_result[key]}")