"""
Optimized option chain retrieval for PMCC analysis.
Shows how to get all needed data in a single API call.
"""

def get_pmcc_option_chain_params():
    """
    Build optimal parameters for PMCC option chain retrieval.
    Gets both LEAPS and short calls in ONE API call.
    """
    
    # Get options from 30 days to 730 days (covers both short calls and LEAPS)
    params = {
        'from': 30,      # Minimum 30 days (for short calls)
        'to': 730,       # Maximum 730 days (2 years for LEAPS)
        'side': 'call',  # Only need calls for PMCC
        'feed': 'cached', # Use cached feed (1 credit total)
        
        # Additional filters to reduce data size
        'minVolume': 10,  # Minimum volume for liquidity
        'maxBidAskSpreadPct': 0.10,  # Max 10% bid-ask spread
        'strikeLimit': 20,  # Get 20 strikes around ATM
        
        # Exclude non-standard options
        'nonstandard': False,
        
        # Get both weekly and monthly expirations
        'weekly': True,
        'monthly': True,
    }
    
    return params


def build_pmcc_option_chain_url(symbol: str):
    """
    Build the complete URL for PMCC option chain retrieval.
    """
    base_url = "https://api.marketdata.app/v1/options/chain"
    params = get_pmcc_option_chain_params()
    
    # Convert params to query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    
    return f"{base_url}/{symbol}/?{query_string}"


# Example usage:
# For MSFT, this single API call would return:
# - All calls from 30-730 days to expiration
# - Both weekly and monthly expirations
# - 20 strikes around the money
# - Filtered for liquidity and tight spreads
# - Costs only 1 credit (cached feed)

example_url = build_pmcc_option_chain_url("MSFT")
print("Optimized PMCC Option Chain URL:")
print(example_url)
print("\nThis returns all needed data in ONE API call for 1 credit!")