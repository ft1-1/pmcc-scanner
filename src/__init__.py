"""
PMCC Scanner - Poor Man's Covered Call Options Analysis Tool.

This package provides comprehensive tools for identifying and analyzing
options trading opportunities using the Poor Man's Covered Call strategy.
"""

__version__ = "1.0.0"
__author__ = "PMCC Scanner Team"

# Re-export main components for easy access
from .main import PMCCApplication

__all__ = [
    "PMCCApplication",
]