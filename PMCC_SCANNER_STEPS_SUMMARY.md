# PMCC Scanner Application Steps - Quick Reference

## 🚀 When You Run: `python src/main.py --mode once`

### Phase 1: Initialization (0-5 seconds)
1. **Load Configuration** → Read .env and settings
2. **Initialize Providers** → Setup MarketData.app, EODHD, Claude AI
3. **Health Checks** → Verify all providers are operational
4. **Create Scanner** → Initialize analysis components

### Phase 2: Stock Screening (5-30 seconds)
5. **Screen Stocks** → EODHD filters by market cap ($50M-$5B) and volume
6. **Get Stock Quotes** → Fetch current prices for screened stocks
7. **Log Progress** → "Step 1: Found 1,777 stocks to analyze"

### Phase 3: Options Analysis (30 seconds - 15 minutes)
8. **For Each Stock**:
   - **Fetch Option Chain** → Get all available options from MarketData.app
   - **Filter LEAPS** → Find calls with 180-720 DTE, delta 0.70-0.95
   - **Filter Short Calls** → Find calls with 30-45 DTE, delta 0.15-0.40
   - **Find Valid PMCCs** → Match LEAPS with short calls
   - **Calculate Metrics** → Risk/reward, breakeven, max profit/loss
   - **Score Opportunities** → Rate based on liquidity, risk, profit potential

### Phase 4: Risk Analysis (1-2 minutes)
9. **Calculate Greeks** → Net delta, gamma, theta, vega for positions
10. **Assess Liquidity** → Score based on bid-ask spreads and volume
11. **Rank Opportunities** → Sort by total score (minimum 70/100)
12. **Filter Results** → Keep top 25 opportunities

### Phase 5: AI Enhancement (if enabled) (2-5 minutes)
13. **Collect Enhanced Data** → EODHD fundamentals, technicals, calendar events
14. **Prepare for Claude** → Format opportunities with all Greeks and data
15. **Claude Analysis** → AI evaluates opportunities with market context
16. **Merge Results** → Combine traditional scores with AI insights
17. **Select Top 10** → Final filtering based on combined analysis

### Phase 6: Output & Notifications (10-30 seconds)
18. **Export Results** → Save to JSON and CSV in data/ directory
19. **Send WhatsApp** → Concise alerts for top opportunities
20. **Send Email** → Comprehensive summary with AI commentary
21. **Log Completion** → "Scan completed: 116 opportunities in 1,208 seconds"

## 📊 Typical Results

**Input**: ~1,777 stocks screened
**Options Analyzed**: ~1,777 option chains
**PMCC Opportunities Found**: ~100-150
**After Risk Filtering**: ~25-50
**After AI Enhancement**: Top 10 delivered

## 🔄 Data Flow

```
EODHD (Screening) → MarketData.app (Options) → Risk Analysis → 
Enhanced Data (EODHD) → Claude AI → Notifications (Twilio/Email)
```

## ⚡ Key Decision Points

1. **Provider Selection**: System automatically routes to best provider for each operation
2. **Circuit Breakers**: If provider fails 5 times, switches to fallback
3. **AI Enhancement**: Only runs if Claude API configured and enabled
4. **Notification Fallback**: If WhatsApp fails, sends via email

## 🛠️ Other Modes

### `--mode daemon`
- Same steps as above, but:
- Runs continuously
- Executes at scheduled time (default 9:30 AM Eastern)
- Sleeps between runs

### `--mode test`
- Only runs initialization and health checks
- Validates configuration
- Tests provider connectivity
- No actual scanning performed

## 📁 Output Files

- `data/pmcc_scan_YYYYMMDD_HHMMSS.json` - Complete scan results with all data
- `data/pmcc_scan_YYYYMMDD_HHMMSS.csv` - Simplified spreadsheet format
- `logs/pmcc_scanner.log` - Detailed execution logs
- `logs/daily_scan.log` - Scheduled run logs (daemon mode)

## ⏱️ Typical Execution Time

- **Test Mode**: 5-10 seconds
- **Small Scan** (100 stocks): 2-5 minutes
- **Full Scan** (1,500+ stocks): 15-20 minutes
- **With AI Enhancement**: Add 3-5 minutes

## 🔍 Error Recovery

- **Provider Failures**: Automatic fallback to secondary providers
- **Partial Failures**: Continues with available data
- **Network Issues**: Retries with exponential backoff
- **API Limits**: Respects rate limits, queues requests