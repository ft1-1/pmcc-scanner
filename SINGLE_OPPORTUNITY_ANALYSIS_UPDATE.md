# Claude AI Single Opportunity Analysis Update

## Overview

This update transforms the Claude AI integration from batch analysis to individual opportunity analysis, providing more focused and detailed analysis for each PMCC opportunity with 0-100 scoring.

## Key Changes

### 1. Claude Client (`src/api/claude_client.py`)

**New Method Added:**
- `analyze_single_opportunity()` - Analyzes one PMCC opportunity at a time
- `_build_single_opportunity_prompt()` - Creates detailed prompts for single opportunities
- `_parse_single_opportunity_response()` - Parses individual analysis responses

**Features:**
- Comprehensive prompt including all PMCC details (LEAPS, short option, Greeks, risk metrics)
- Complete enhanced EODHD data integration (8 data types)
- 0-100 scoring system with detailed breakdown
- Robust JSON response parsing and validation

### 2. Claude Provider (`src/api/providers/claude_provider.py`)

**New Method Added:**
- `analyze_single_pmcc_opportunity()` - Provider interface for single opportunity analysis

**Features:**
- Cost tracking and limits enforcement
- Health monitoring integration
- Provider metadata attachment
- Error handling and circuit breaker support

**Updated Capabilities:**
- Added `analyze_single_pmcc_opportunity` to supported operations

### 3. Claude Integration Manager (`src/analysis/claude_integration.py`)

**New Methods Added:**
- `analyze_single_opportunity_with_claude()` - Core single opportunity analysis
- `analyze_opportunities_individually()` - Batch processing with individual analysis
- `_integrate_single_claude_analysis()` - Integration of Claude results with PMCC data
- `_create_failed_analysis_result()` - Graceful handling of failed analyses

**Features:**
- Individual opportunity processing with complete data packages
- Concurrent analysis with rate limiting (max 3 concurrent by default)
- Comprehensive error handling and fallback mechanisms
- Detailed statistics tracking

## Analysis Improvements

### Enhanced Data Input
Each opportunity now receives:
- **PMCC Strategy Details**: Net debit, credit received, max profit/loss, breakeven, risk/reward ratio
- **LEAPS Option Data**: Complete Greeks, market data, liquidity metrics
- **Short Option Data**: Complete Greeks, market data, liquidity metrics
- **8 EODHD Data Types**: Fundamentals, calendar events, technical indicators, news sentiment, live price data, earnings data, historical data, economic events

### Detailed 0-100 Scoring
Claude now provides:
- **Overall PMCC Score** (0-100)
- **Component Scores**:
  - Risk Assessment (25 points)
  - Fundamental Health (25 points)  
  - Technical Setup (20 points)
  - Calendar Risk (15 points)
  - PMCC Strategy Quality (15 points)

### Enhanced Analysis Output
Each analyzed opportunity includes:
- **Claude Analysis**: Summary, detailed reasoning, component scores
- **Combined Scoring**: 60% traditional PMCC + 40% Claude AI
- **AI Insights**: Key strengths, risks, profit probability, early assignment risk
- **Recommendations**: Buy/hold/avoid with confidence levels
- **Management Guidance**: Optimal position management strategies

## Usage Examples

### Single Opportunity Analysis
```python
from src.analysis.claude_integration import ClaudeIntegrationManager

integration_manager = ClaudeIntegrationManager()

analyzed_opportunity = await integration_manager.analyze_single_opportunity_with_claude(
    opportunity_data=pmcc_opportunity,
    enhanced_stock_data=complete_enhanced_data,
    claude_provider=claude_provider,
    market_context=market_context
)

print(f"Claude Score: {analyzed_opportunity['claude_score']}")
print(f"Combined Score: {analyzed_opportunity['combined_score']}")
print(f"Recommendation: {analyzed_opportunity['claude_recommendation']}")
```

### Batch Individual Analysis
```python
analyzed_opportunities = await integration_manager.analyze_opportunities_individually(
    opportunities=pmcc_opportunities,
    enhanced_stock_data_lookup=enhanced_data_by_symbol,
    claude_provider=claude_provider,
    max_concurrent=3
)

# Results are sorted by combined score (highest first)
for opp in analyzed_opportunities[:5]:  # Top 5
    print(f"{opp['symbol']}: {opp['combined_score']:.1f}")
```

## Benefits

### 1. **Focused Analysis**
- Each opportunity gets full Claude attention
- Complete data package per analysis
- No information loss due to batch processing limits

### 2. **Better Scoring**
- 0-100 scoring system is more intuitive
- Detailed component breakdowns for transparency
- Consistent scoring methodology across all opportunities

### 3. **Enhanced Data Integration**
- All 8 EODHD data types included in analysis
- Complete option chain data with all Greeks
- Comprehensive PMCC strategy details

### 4. **Improved Reliability**
- Individual error handling per opportunity
- Graceful degradation for failed analyses
- Concurrent processing with rate limiting

### 5. **Better Cost Control**
- More predictable token usage per opportunity
- Better cost tracking and monitoring
- Configurable concurrent request limits

## Testing

A comprehensive test script is provided: `test_single_opportunity_analysis.py`

**Test Features:**
- Single opportunity analysis testing
- Batch individual analysis testing
- Sample data generation
- Results validation and display
- Performance and statistics monitoring

**Run Tests:**
```bash
python test_single_opportunity_analysis.py
```

## Configuration

### Environment Variables
```bash
CLAUDE_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Optional
CLAUDE_MAX_TOKENS=4000                   # Optional
CLAUDE_DAILY_COST_LIMIT=10.0            # Optional
```

### Provider Settings
```python
claude_config = {
    'api_key': claude_api_key,
    'model': 'claude-3-5-sonnet-20241022',
    'max_tokens': 4000,
    'temperature': 0.1,
    'daily_cost_limit': 10.0,
    'max_concurrent_analyses': 3
}
```

## Migration from Batch Analysis

The existing batch analysis methods remain available for backward compatibility:
- `analyze_pmcc_opportunities()` - Original batch method
- `get_enhanced_analysis()` - Alternative batch method

New individual analysis is accessed via:
- `analyze_single_pmcc_opportunity()` - Single opportunity method
- `analyze_opportunities_individually()` - Batch processing with individual analysis

## Performance Considerations

### Rate Limiting
- Default: 3 concurrent requests maximum
- Configurable via `max_concurrent` parameter
- Respects Claude API rate limits

### Cost Management
- Daily cost limits enforced
- Token usage tracking per analysis
- Transparent cost reporting

### Error Handling
- Individual opportunity failures don't affect others
- Graceful degradation with meaningful error messages
- Retry logic for transient failures

## Future Enhancements

1. **Caching**: Implement intelligent caching for repeated analyses
2. **Batch Optimization**: Optimize prompts for even better cost efficiency
3. **Custom Scoring**: Allow custom scoring criteria and weights
4. **Real-time Analysis**: Support for real-time opportunity analysis
5. **Enhanced Monitoring**: More detailed performance and cost analytics

## Conclusion

This update significantly improves the quality and reliability of Claude AI analysis for PMCC opportunities while providing better cost control and error handling. The individual analysis approach ensures each opportunity receives comprehensive evaluation with complete data context, leading to more accurate and actionable insights for traders.