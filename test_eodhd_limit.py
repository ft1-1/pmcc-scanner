#!/usr/bin/env python3
"""Test EODHD API limit fix"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.sync_eodhd_client import SyncEODHDClient
from src.config.settings import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_eodhd_limit():
    """Test EODHD screener with 500 limit"""
    settings = get_settings()
    
    if not settings.eodhd or not settings.eodhd.api_token:
        logger.error("EODHD API token not configured")
        return
    
    client = SyncEODHDClient(
        api_token=settings.eodhd.api_token,
        base_url=settings.eodhd.base_url,
        timeout=30.0  # Default timeout
    )
    
    logger.info("Testing EODHD screener with limit=500...")
    
    try:
        response = client.screen_by_market_cap(
            min_market_cap=50_000_000,    # $50M
            max_market_cap=5_000_000_000,  # $5B
            min_volume=100_000,
            limit=500  # Maximum allowed by EODHD API
        )
        
        if response.is_success and response.data:
            if hasattr(response.data, 'results'):
                symbol_count = len(response.data.results)
            elif isinstance(response.data, list):
                symbol_count = len(response.data)
            else:
                symbol_count = 0
                
            logger.info(f"✅ Success! Retrieved {symbol_count} symbols from EODHD")
            
            # Show first 5 symbols as example
            if symbol_count > 0:
                logger.info("First 5 symbols:")
                for i, stock in enumerate((response.data.results if hasattr(response.data, 'results') else response.data)[:5]):
                    if hasattr(stock, 'code'):
                        logger.info(f"  {i+1}. {stock.code}")
                    elif isinstance(stock, dict) and 'code' in stock:
                        logger.info(f"  {i+1}. {stock['code']}")
        else:
            logger.error(f"❌ Failed: {response.error}")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    test_eodhd_limit()