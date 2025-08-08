#!/usr/bin/env python3
"""Find all .get() calls in the _enhanced_stock_data_to_dict method."""

import re

# Read the scanner.py file
with open('/home/deployuser/stock-options/pmcc-scanner/src/analysis/scanner.py', 'r') as f:
    content = f.read()

# Find the method
method_start = content.find('def _enhanced_stock_data_to_dict(self, comprehensive_data) -> Dict[str, Any]:')
if method_start == -1:
    print("Method not found!")
    exit(1)

# Find the end of the method (next def or class)
method_end = content.find('\n    def ', method_start + 1)
if method_end == -1:
    method_end = content.find('\nclass ', method_start + 1)
if method_end == -1:
    method_end = len(content)

method_content = content[method_start:method_end]

# Find all .get( calls with their line numbers
lines = method_content.split('\n')
base_line_number = content[:method_start].count('\n') + 1

print("All .get() calls in _enhanced_stock_data_to_dict:")
print("-" * 80)

for i, line in enumerate(lines):
    if '.get(' in line:
        line_number = base_line_number + i
        # Get the variable being called
        match = re.search(r'(\w+)\.get\(', line)
        if match:
            var_name = match.group(1)
            print(f"Line {line_number}: {var_name}.get() - {line.strip()}")