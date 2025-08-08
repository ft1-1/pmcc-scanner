# Claude AI Integration for PMCC Scanner

This document provides comprehensive guidance on using the Claude AI integration features in the PMCC Scanner.

## Overview

The Claude AI integration enhances the PMCC Scanner with intelligent market analysis, risk assessment, and commentary capabilities. It provides AI-powered insights while maintaining strict cost controls and preserving backward compatibility.

## Features

### 🤖 AI-Powered Analysis
- **Market Commentary**: Generate intelligent commentary on market conditions and opportunities
- **Risk Assessment**: AI-driven risk analysis and categorization 
- **Opportunity Ranking**: Enhanced ranking with qualitative insights
- **Strategic Recommendations**: Actionable trading insights and timing suggestions

### 💰 Cost Management
- **Configurable Limits**: Set daily and monthly spending limits
- **Real-time Tracking**: Monitor API usage and costs in real-time
- **Cost Tiers**: Pre-configured cost profiles (Conservative, Balanced, Aggressive)
- **Usage Alerts**: Automatic alerts when approaching limits

### 📱 Enhanced Notifications
- **WhatsApp**: AI insights included in mobile alerts
- **Email**: Comprehensive market commentary in daily summaries
- **Smart Formatting**: Concise insights optimized for each channel

## Quick Start

### 1. Configuration

Add your Claude API key to your `.env` file:

```bash
# Claude AI Configuration
CLAUDE_API_KEY=sk-ant-your-actual-api-key-here

# Optional: Customize settings
CLAUDE_ANALYSIS_MODE=enhanced          # basic, enhanced, research
CLAUDE_COST_TIER=balanced             # conservative, balanced, aggressive
CLAUDE_DAILY_COST_LIMIT_USD=5.00      # Daily spending limit
CLAUDE_MAX_OPPORTUNITIES_FOR_ANALYSIS=10  # Max opportunities to analyze
```

### 2. Test Configuration

```bash
python examples/claude_analysis_demo.py
```

### 3. Run Enhanced Scan

```bash
python src/main.py --mode once
```

## Configuration Options

### Analysis Modes

| Mode | Description | Use Case | Typical Cost |
|------|-------------|----------|--------------|
| `basic` | Brief analysis and commentary | Daily scans | $0.50-1.00 |
| `enhanced` | Comprehensive analysis with insights | Detailed analysis | $1.00-3.00 |
| `research` | Deep analytical reports | Research/planning | $3.00-8.00 |

### Cost Tiers

| Tier | Daily Limit | Max Analysis | Model | Description |
|------|-------------|--------------|-------|-------------|
| `conservative` | $2.00 | 3-5 opportunities | Haiku | Minimal cost, basic insights |
| `balanced` | $5.00 | 5-10 opportunities | Haiku/Sonnet | Good value, solid insights |
| `aggressive` | $15.00 | 10-20 opportunities | Sonnet | Comprehensive analysis |

### Environment Variables

```bash
# Core Configuration
CLAUDE_API_KEY=sk-ant-your-key                    # Required
CLAUDE_ANALYSIS_MODE=enhanced                     # basic|enhanced|research
CLAUDE_COST_TIER=balanced                         # conservative|balanced|aggressive

# Cost Controls
CLAUDE_DAILY_COST_LIMIT_USD=5.00                 # Daily spending limit
CLAUDE_MONTHLY_COST_LIMIT_USD=100.00             # Monthly spending limit
CLAUDE_MAX_OPPORTUNITIES_FOR_ANALYSIS=10         # Max opportunities per scan

# Advanced Settings
CLAUDE_PRIMARY_MODEL=claude-3-5-haiku-20241022   # Primary model
CLAUDE_MAX_REQUESTS_PER_MINUTE=50                # Rate limiting
CLAUDE_MAX_CONCURRENT_REQUESTS=3                 # Concurrency limit
CLAUDE_REQUEST_TIMEOUT_SECONDS=60                # Request timeout

# Feature Flags
CLAUDE_ENABLE_MARKET_COMMENTARY=true             # Market commentary
CLAUDE_ENABLE_OPPORTUNITY_RANKING=true           # AI ranking
CLAUDE_ENABLE_RISK_INSIGHTS=true                 # Risk analysis
CLAUDE_CACHE_ANALYSIS_RESULTS=true               # Response caching
```

## Usage Examples

### Basic Daily Scan with AI

```python
from src.main import PMCCApplication

# Create app with Claude AI enabled
app = PMCCApplication({
    'CLAUDE_ANALYSIS_MODE': 'basic',
    'CLAUDE_COST_TIER': 'conservative'
})

# Run scan with AI analysis
results = app.run_scan()

# Access Claude insights
if results.claude_analysis:
    print("AI Market Commentary:", results.claude_analysis['market_commentary'])
    print("Overall Recommendation:", results.claude_analysis['summary_insights']['overall_recommendation'])
```

### Custom Analysis Configuration

```python
from src.config.claude_config import ClaudeConfig, ClaudeAnalysisMode, CostTier
from src.analysis.claude_analyzer import ClaudeAnalysisEngine

# Custom configuration
config = ClaudeConfig(
    api_key="your-api-key",
    analysis_mode=ClaudeAnalysisMode.ENHANCED,
    cost_tier=CostTier.BALANCED,
    daily_cost_limit_usd=Decimal("10.00"),
    max_opportunities_for_analysis=8
)

# Create analyzer
analyzer = ClaudeAnalysisEngine(config)

# Analyze opportunities
results = await analyzer.analyze_opportunities(candidates, market_context)
```

## Sample Output

### WhatsApp Notification with AI

```
🎯 *PMCC Daily Scan Results*
Found opportunities in 3 stocks
Showing top 3:

*1. AAPL* - $175.50
   Net Cost: $2,500.00
   Max Profit: $650.00 (26.0%)
   Score: 83/100

*2. MSFT* - $410.25
   Score: 78/100

🤖 AI: Favorable market conditions
💡 AI Rec: Focus on highest-scored candidates with proper sizing

⏰ Scan completed at 9:32 AM
```

### Email with Claude Insights

```
📧 PMCC Daily Summary with AI Insights

🤖 Claude AI Market Insights
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Market Commentary:
Technology sector showing resilience with solid fundamentals across 
major names. Current volatility creating attractive PMCC entry points 
for patient investors.

AI Recommendation:
Selective opportunities available - focus on highest-scored candidates 
with proper position sizing and consider market timing.

Key Themes Identified:
• Technology sector strength across mega-cap names
• Volatility environment favorable for premium collection
• Risk-reward ratios attractive in current market conditions

AI Analysis: 5 requests, $1.25 cost
```

## Cost Management

### Monitoring Usage

```python
# Get usage summary
usage = claude_client.get_usage_summary()

print(f"Daily cost: ${usage['daily']['cost_usd']:.2f}")
print(f"Requests: {usage['daily']['requests']}")
print(f"Within limit: {usage['limits']['within_daily_limit']}")
print(f"Usage: {usage['limits']['daily_usage_percentage']:.1f}%")
```

### Cost Optimization Tips

1. **Use Basic Mode for Routine Scans**: Save enhanced analysis for important decisions
2. **Limit Opportunity Analysis**: Set `max_opportunities_for_analysis` to essential picks
3. **Monitor Daily Usage**: Check costs in scan results and adjust as needed
4. **Choose Appropriate Tier**: Conservative for daily use, Balanced for regular analysis
5. **Cache Results**: Enable caching to avoid repeat analysis costs

### Cost Scenarios

| Scenario | Mode | Opportunities | Est. Daily Cost | Monthly Est. |
|----------|------|---------------|-----------------|--------------|
| Light Daily Use | Basic | 3-5 | $0.75-1.50 | $22.50-45.00 |
| Regular Analysis | Enhanced | 5-10 | $2.00-4.00 | $60.00-120.00 |
| Heavy Research | Research | 10-20 | $6.00-15.00 | $180.00-450.00 |

## Error Handling

The Claude integration includes comprehensive error handling:

### Automatic Fallbacks
- **API Errors**: Scan continues without Claude analysis
- **Cost Limits**: Analysis blocked when limits exceeded
- **Rate Limits**: Automatic retry with exponential backoff
- **Network Issues**: Graceful degradation with error logging

### Error Messages
```python
# Example error handling in scan results
if results.claude_analysis['status'] == 'error':
    print(f"Claude analysis failed: {results.claude_analysis['error']}")
    # Scan results still available in results.top_opportunities

if results.claude_analysis['status'] == 'cost_limit_exceeded':
    print("Daily cost limit reached - reduce limits or upgrade tier")
```

## Testing

### Unit Tests
```bash
# Test Claude client
pytest tests/unit/api/test_claude_client.py -v

# Test analysis engine
pytest tests/unit/analysis/test_claude_analyzer.py -v
```

### Integration Tests
```bash
# Test full integration
pytest tests/integration/test_claude_integration.py -v
```

### Demo Mode
```bash
# Run demo without API calls
python examples/claude_analysis_demo.py
```

### Real API Testing (requires API key)
```bash
# Test with real API
CLAUDE_API_KEY=your-key pytest tests/integration/ -m integration -v
```

## Troubleshooting

### Common Issues

1. **"Claude API key cannot be empty"**
   - Solution: Set `CLAUDE_API_KEY` in `.env` file

2. **"Cost limit exceeded"**
   - Solution: Increase `CLAUDE_DAILY_COST_LIMIT_USD` or wait for daily reset

3. **"Analysis disabled"**  
   - Solution: Set `CLAUDE_ANALYSIS_MODE` to `basic`, `enhanced`, or `research`

4. **"Rate limit exceeded"**
   - Solution: Lower `CLAUDE_MAX_REQUESTS_PER_MINUTE` or upgrade Claude API plan

5. **Missing insights in notifications**
   - Solution: Verify Claude analysis completed successfully in scan logs

### Debug Mode

Enable verbose logging:
```bash
LOG_LEVEL=DEBUG python src/main.py --mode once
```

### Health Check

```python
# Check Claude integration health
health = await claude_client.health_check()
print(f"Claude healthy: {health['healthy']}")
print(f"Model available: {health['model_available']}")
```

## Security Considerations

### API Key Protection
- Store API keys securely in `.env` files
- Never commit API keys to version control
- Use environment-specific keys (dev, staging, prod)
- Rotate keys regularly

### Cost Controls
- Set appropriate daily/monthly limits
- Monitor usage regularly
- Use alerts for unusual usage patterns
- Review analysis value vs. cost regularly

### Data Privacy
- Claude AI processes market data and analysis prompts
- No personal or account information is sent to Claude
- Analysis results are cached locally only
- Review Anthropic's data usage policies

## Advanced Configuration

### Custom Prompts

For advanced users, prompts can be customized by extending the `ClaudeClient`:

```python
class CustomClaudeClient(ClaudeClient):
    def _prepare_opportunity_analysis_prompt(self, stock_data, opp_data, context):
        # Custom prompt logic
        prompt = f"Analyze {stock_data['symbol']} with custom criteria..."
        return prompt
```

### Multiple Analysis Modes

Configure different modes for different scan types:

```python
# Morning scan - basic insights
morning_config = ClaudeConfig(
    analysis_mode=ClaudeAnalysisMode.BASIC,
    max_opportunities_for_analysis=5
)

# Weekly deep dive - comprehensive analysis  
weekly_config = ClaudeConfig(
    analysis_mode=ClaudeAnalysisMode.RESEARCH,
    max_opportunities_for_analysis=15
)
```

## Performance Optimization

### Caching Strategy
- Enable response caching for repeated analysis
- Set appropriate cache TTL (default: 6 hours)
- Clear cache for fresh market analysis

### Concurrency Tuning
```python
# Optimize for your API limits
CLAUDE_MAX_CONCURRENT_REQUESTS=3      # Conservative
CLAUDE_MAX_REQUESTS_PER_MINUTE=50     # Standard tier
```

### Analysis Limits
```python
# Balance insight quality vs. cost
CLAUDE_MAX_OPPORTUNITIES_FOR_ANALYSIS=8   # Sweet spot for most users
```

## Support and Resources

### Getting Help
1. Check logs for detailed error messages
2. Run demo script to verify configuration
3. Review usage summary in scan results
4. Test with basic mode first

### Documentation
- [Claude API Documentation](https://docs.anthropic.com/)
- [PMCC Scanner Documentation](../README.md)
- [Configuration Examples](../config_examples/)

### Best Practices
1. Start with Conservative tier and Basic mode
2. Monitor costs for first week of usage
3. Adjust limits based on actual usage patterns
4. Use Enhanced mode for important decisions
5. Enable all error handling and logging

## Conclusion

The Claude AI integration transforms the PMCC Scanner from a quantitative analysis tool into an intelligent trading assistant. With proper configuration and cost management, it provides valuable market insights while maintaining financial discipline.

Start conservatively, monitor usage, and scale up based on the value you receive from the AI insights. The system is designed to enhance your trading decisions while staying within your specified cost parameters.