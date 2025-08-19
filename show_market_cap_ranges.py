#!/usr/bin/env python3
"""
Show the market cap ranges that would be generated for a given min/max range.
"""

def get_range_size(current_cap):
    """Get appropriate range size based on current market cap level"""
    if current_cap < 100_000_000:  # Under 100M
        return 50_000_000  # 50M ranges
    elif current_cap < 500_000_000:  # 100M-500M
        return 250_000_000  # 250M ranges
    elif current_cap < 1_000_000_000:  # 500M-1B
        return 500_000_000  # 500M ranges
    elif current_cap < 5_000_000_000:  # 1B-5B
        return 1_000_000_000  # 1B ranges
    elif current_cap < 10_000_000_000:  # 5B-10B
        return 2_500_000_000  # 2.5B ranges
    elif current_cap < 50_000_000_000:  # 10B-50B
        return 5_000_000_000  # 5B ranges
    elif current_cap < 100_000_000_000:  # 50B-100B
        return 10_000_000_000  # 10B ranges
    else:  # Above 100B
        return 25_000_000_000  # 25B ranges

def generate_market_cap_ranges(min_cap, max_cap):
    """Generate market cap ranges dynamically"""
    ranges = []
    current = min_cap
    
    while current < max_cap:
        range_size = get_range_size(current)
        range_end = min(current + range_size, max_cap)
        ranges.append((current, range_end))
        current = range_end
    
    return ranges

# Generate ranges for 100M to 50B (matching your .env settings)
min_cap = 100_000_000  # 100M
max_cap = 50_000_000_000  # 50B

ranges = generate_market_cap_ranges(min_cap, max_cap)

print(f"Market cap ranges for ${min_cap/1e6:.0f}M to ${max_cap/1e9:.0f}B:")
print(f"Total number of ranges: {len(ranges)}\n")

for i, (start, end) in enumerate(ranges, 1):
    if start >= 1_000_000_000:  # 1B or more
        start_str = f"${start/1e9:.1f}B"
    else:
        start_str = f"${start/1e6:.0f}M"
    
    if end >= 1_000_000_000:  # 1B or more
        end_str = f"${end/1e9:.1f}B"
    else:
        end_str = f"${end/1e6:.0f}M"
    
    range_size = end - start
    if range_size >= 1_000_000_000:
        size_str = f"{range_size/1e9:.1f}B"
    else:
        size_str = f"{range_size/1e6:.0f}M"
    
    print(f"{i:2d}. {start_str:>7} - {end_str:>7} (range size: {size_str})")