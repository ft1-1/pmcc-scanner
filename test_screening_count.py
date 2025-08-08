#!/usr/bin/env python3
"""Test script to check screening results count"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import get_settings
from eodhd import APIClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_screening_count():
    """Test EODHD screening to see how many stocks match criteria"""
    settings = get_settings()
    
    if not settings.eodhd or not settings.eodhd.api_token:
        logger.error("EODHD API token not configured")
        return
    
    client = APIClient(api_key=settings.eodhd.api_token)
    
    # Filters matching our criteria
    filters = [
        ['market_capitalization', '>=', 50_000_000],     # $50M
        ['market_capitalization', '<=', 5_000_000_000],  # $5B
        ['avgvol_200d', '>=', 100_000]                   # 100K volume
    ]
    
    total_count = 0
    
    for exchange in ['NYSE', 'NASDAQ']:
        exchange_filters = filters + [['exchange', '=', exchange]]
        
        # Get first batch to see total available
        response = client.stock_market_screener(
            sort='market_capitalization.desc',
            filters=exchange_filters,
            limit=100,
            offset=0
        )
        
        if response and 'data' in response:
            batch_count = len(response['data'])
            logger.info(f"{exchange}: First batch has {batch_count} stocks")
            
            # Try to get count at max offset
            response_max = client.stock_market_screener(
                sort='market_capitalization.desc',
                filters=exchange_filters,
                limit=100,
                offset=900
            )
            
            if response_max and 'data' in response_max:
                logger.info(f"{exchange}: Batch at offset 900 has {len(response_max['data'])} stocks")
                # Estimate total: offset 900 + whatever we get
                estimated_total = 900 + len(response_max['data'])
                logger.info(f"{exchange}: Estimated total at least {estimated_total} stocks")
                total_count += min(estimated_total, 1000)  # Cap at 1000 due to offset limit
            else:
                # Less than 900 stocks
                total_count += batch_count
        else:
            logger.warning(f"No data for {exchange}")
    
    logger.info(f"\nTotal stocks matching criteria (accessible via API): ~{total_count}")
    logger.info("\nCriteria used:")
    logger.info("- Market Cap: $50M - $5B")
    logger.info("- Volume: >= 100K (200-day average)")
    logger.info("- Exchanges: NYSE, NASDAQ")

if __name__ == "__main__":
    test_screening_count()