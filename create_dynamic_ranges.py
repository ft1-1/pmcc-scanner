#!/usr/bin/env python3
"""
Dynamic market cap range generator for EODHD API limits.
This shows how we should implement dynamic range splitting.
"""

def create_dynamic_market_cap_ranges(min_cap, max_cap, max_results_per_range=1000):
    """
    Dynamically create market cap ranges based on min/max values.
    
    The strategy:
    - For small caps (< 1B): Use smaller ranges as there are many stocks
    - For mid caps (1B-10B): Use 1B increments
    - For large caps (10B-100B): Use 5B-10B increments
    - For mega caps (> 100B): Use larger increments
    """
    ranges = []
    
    # Define range sizes based on market cap levels
    # Format: (threshold, range_size)
    range_sizes = [
        (100_000_000, 50_000_000),      # Under 100M: 50M ranges
        (500_000_000, 250_000_000),     # 100M-500M: 250M ranges
        (1_000_000_000, 500_000_000),   # 500M-1B: 500M ranges
        (5_000_000_000, 1_000_000_000), # 1B-5B: 1B ranges
        (10_000_000_000, 2_500_000_000), # 5B-10B: 2.5B ranges
        (50_000_000_000, 5_000_000_000), # 10B-50B: 5B ranges
        (100_000_000_000, 10_000_000_000), # 50B-100B: 10B ranges
        (float('inf'), 50_000_000_000),  # Above 100B: 50B ranges
    ]
    
    current = min_cap
    while current < max_cap:
        # Find appropriate range size for current market cap level
        range_size = range_sizes[-1][1]  # Default to largest
        for threshold, size in range_sizes:
            if current < threshold:
                range_size = size
                break
        
        # Calculate range end, but don't exceed max_cap
        range_end = min(current + range_size, max_cap)
        
        # Add the range
        ranges.append((current, range_end))
        
        # Move to next range
        current = range_end
    
    return ranges

# Test with different scenarios
test_cases = [
    (50_000_000, 5_000_000_000),    # Current: 50M-5B
    (50_000_000, 10_000_000_000),   # Proposed: 50M-10B
    (500_000_000, 50_000_000_000),  # Your example: 500M-50B
    (1_000_000_000, 100_000_000_000), # Large range: 1B-100B
]

for min_cap, max_cap in test_cases:
    ranges = create_dynamic_market_cap_ranges(min_cap, max_cap)
    print(f"\nRange: ${min_cap/1e6:.0f}M - ${max_cap/1e9:.1f}B")
    print(f"Number of ranges: {len(ranges)}")
    for i, (start, end) in enumerate(ranges[:10]):  # Show first 10
        print(f"  {i+1}. ${start/1e6:.0f}M - ${end/1e6:.0f}M")
    if len(ranges) > 10:
        print(f"  ... and {len(ranges) - 10} more ranges")