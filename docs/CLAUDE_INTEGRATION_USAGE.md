# Claude AI Integration Usage Guide

This document describes how to use the Claude AI integration for enhanced PMCC analysis in the PMCC Scanner.

## Setup

### 1. Install Dependencies

The Claude integration requires the `anthropic` Python library:

```bash
pip install anthropic>=0.20.0
```

### 2. Configure API Key

Set your Claude API key as an environment variable:

```bash
export CLAUDE_API_KEY="your-anthropic-api-key-here"
```

You can also add this to your `.env` file:

```
CLAUDE_API_KEY=your-anthropic-api-key-here
```

### 3. Optional Configuration

You can customize Claude behavior with these environment variables:

```bash
# Model selection (default: claude-3-5-sonnet-20241022)
export CLAUDE_MODEL="claude-3-5-sonnet-20241022"

# Response length (default: 4000)
export CLAUDE_MAX_TOKENS=4000

# Creativity level (default: 0.1, range: 0.0-1.0)
export CLAUDE_TEMPERATURE=0.1

# Daily cost limit in USD (default: 10.0)
export CLAUDE_DAILY_COST_LIMIT=10.0

# Analysis settings
export CLAUDE_MAX_STOCKS_PER_ANALYSIS=20
export CLAUDE_MIN_DATA_COMPLETENESS_THRESHOLD=60.0
```

## Usage

### Using the Provider Factory

The Claude provider integrates seamlessly with the existing provider factory:

```python
from src.api.provider_factory import DataProviderFactory, ProviderConfig
from src.api.providers import ClaudeProvider
from src.api.data_provider import ProviderType

# Create provider config
claude_config = ProviderConfig(
    provider_type=ProviderType.CLAUDE,
    provider_class=ClaudeProvider,
    config={
        'api_key': 'your-api-key',
        'model': 'claude-3-5-sonnet-20241022',
        'max_tokens': 4000,
        'temperature': 0.1,
        'daily_cost_limit': 10.0
    },
    preferred_operations=['analyze_pmcc_opportunities']
)

# Register with factory
factory = DataProviderFactory()
factory.register_provider(claude_config)

# Use the analysis
response = await factory.analyze_pmcc_opportunities(
    enhanced_stock_data=your_stock_data,
    market_context={'volatility_regime': 'Normal'},
    preferred_provider=ProviderType.CLAUDE
)
```

### Direct Provider Usage

You can also use the Claude provider directly:

```python
from src.api.providers import ClaudeProvider
from src.api.data_provider import ProviderType

# Create provider
provider = ClaudeProvider(ProviderType.CLAUDE, {
    'api_key': 'your-api-key',
    'model': 'claude-3-5-sonnet-20241022',
    'max_tokens': 4000,
    'temperature': 0.1
})

# Analyze opportunities
response = await provider.analyze_pmcc_opportunities(
    enhanced_stock_data=your_enhanced_data,
    market_context={
        'volatility_regime': 'Normal',
        'market_sentiment': 'Neutral',
        'interest_rate_trend': 'Rising'
    }
)

if response.is_success:
    analysis = response.data
    print(f"Found {len(analysis.opportunities)} opportunities")
    for opp in analysis.get_top_opportunities(5):
        print(f"{opp.symbol}: {opp.score} - {opp.reasoning}")
```

### Integration with Existing PMCC Data

Use the integration manager to merge Claude analysis with existing PMCC results:

```python
from src.analysis.claude_integration import ClaudeIntegrationManager

# Create integration manager
integration_manager = ClaudeIntegrationManager()

# Merge Claude analysis with existing PMCC opportunities
enhanced_opportunities = integration_manager.merge_claude_analysis_with_pmcc_data(
    pmcc_opportunities=existing_pmcc_data,
    claude_response=claude_analysis_response,
    enhanced_stock_data=original_stock_data
)

# Create enhanced summary
summary = integration_manager.create_enhanced_opportunity_summary(
    enhanced_opportunities=enhanced_opportunities,
    claude_response=claude_analysis_response
)

# Filter by AI criteria
high_quality_opportunities = integration_manager.filter_opportunities_by_ai_criteria(
    enhanced_opportunities=enhanced_opportunities,
    min_combined_score=75.0,
    min_confidence=70.0,
    required_recommendation='buy'
)
```

## Response Structure

### ClaudeAnalysisResponse

```python
{
    'opportunities': [PMCCOpportunityAnalysis],
    'market_assessment': str,
    'analysis_timestamp': datetime,
    'model_used': str,
    'processing_time_ms': float,
    'input_tokens': int,
    'output_tokens': int
}
```

### PMCCOpportunityAnalysis

```python
{
    'symbol': str,
    'score': Decimal,  # 0-100
    'reasoning': str,
    'risk_score': Decimal,  # 0-100, higher = riskier
    'fundamental_health_score': Decimal,  # 0-100
    'technical_setup_score': Decimal,  # 0-100
    'calendar_risk_score': Decimal,  # 0-100
    'pmcc_quality_score': Decimal,  # 0-100
    'key_strengths': List[str],
    'key_risks': List[str],
    'recommendation': str,  # 'strong_buy', 'buy', 'hold', 'avoid'
    'confidence': Decimal  # 0-100
}
```

### Enhanced Opportunity (after integration)

```python
{
    # Original PMCC data
    'symbol': str,
    'pmcc_score': float,
    'recommendation': str,
    
    # Claude AI additions
    'claude_analyzed': bool,
    'claude_score': float,
    'claude_reasoning': str,
    'claude_confidence': float,
    'combined_score': float,  # Weighted combination
    'ai_recommendation': str,
    
    # Detailed AI insights
    'ai_insights': {
        'risk_score': float,
        'fundamental_health_score': float,
        'technical_setup_score': float,
        'calendar_risk_score': float,
        'pmcc_quality_score': float,
        'key_strengths': List[str],
        'key_risks': List[str]
    },
    
    # Metadata
    'analysis_timestamp': str,
    'model_used': str
}
```

## Testing

Run the integration test to verify everything is working:

```bash
export CLAUDE_API_KEY="your-api-key"
python test_claude_integration.py
```

This will test:
- Configuration validation
- Provider creation
- Health checks
- Analysis functionality (optional, uses API credits)

## Cost Management

The Claude integration includes built-in cost management:

1. **Daily Limits**: Set `CLAUDE_DAILY_COST_LIMIT` to control maximum daily spend
2. **Stock Limits**: `CLAUDE_MAX_STOCKS_PER_ANALYSIS` limits stocks per request
3. **Data Quality Filtering**: Only analyzes stocks meeting data completeness thresholds
4. **Cost Tracking**: Monitor usage with `provider.get_provider_info()`

Example cost monitoring:

```python
# Check current usage
info = provider.get_provider_info()
print(f"Daily cost used: ${info['daily_cost_used']:.4f}")
print(f"Daily limit: ${info['daily_cost_limit']}")

# Check client stats
stats = provider.client.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Estimated total cost: ${stats['total_cost_estimate']:.4f}")
```

## Error Handling

The Claude integration includes comprehensive error handling:

- **Authentication errors**: Invalid API key
- **Rate limiting**: Automatic retry with exponential backoff
- **Token limits**: Request size management
- **Network issues**: Retry logic with circuit breakers
- **Response parsing**: Robust JSON validation

Check the logs for detailed error information and troubleshooting guidance.

## Best Practices

1. **Data Quality**: Ensure stock data has good completeness scores (>60%)
2. **Batch Size**: Keep analysis batches under 20 stocks for optimal performance
3. **Market Context**: Provide market context for better analysis quality
4. **Cost Monitoring**: Regularly check usage against daily limits
5. **Error Handling**: Always check `response.is_success` before using results
6. **Circuit Breakers**: Allow the system to handle failures gracefully

## Troubleshooting

### Common Issues

1. **"No Claude API key provided"**
   - Set the `CLAUDE_API_KEY` environment variable
   - Verify the key is valid and not expired

2. **"Daily cost limit exceeded"**
   - Increase `CLAUDE_DAILY_COST_LIMIT` or wait for daily reset
   - Check usage with `provider.get_provider_info()`

3. **"No opportunities found in Claude response"**
   - Check if input data meets minimum quality thresholds
   - Verify the prompt is receiving valid stock data
   - Review logs for JSON parsing errors

4. **High latency or timeouts**
   - Reduce `CLAUDE_MAX_STOCKS_PER_ANALYSIS`
   - Increase `CLAUDE_TIMEOUT_SECONDS`
   - Check network connectivity

For additional support, check the application logs and the Claude provider's health status.