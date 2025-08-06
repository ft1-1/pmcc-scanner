Usage Example & parameters
Screener API request example:

https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&sort=market_capitalization.desc&filters=[["market_capitalization",">",1000],["name","match","apple"],["code","=","AAPL"],["exchange","=","us"],["sector","=","Technology"]]&limit=10&offset=0

Parameters
filters: String, Optional. Usage: filters=[[“field1”, “operation1”, value1], [“field2”, “operation2”, value2] , … ]. Filters out tickers by different fields.
signals: String, Optional. Usage: signals=signal1, signal2, …, signalN. Filter out tickers by signals, the calculated fields.
sort: String, Optional. Usage: sort=field_name.(asc|desc). Sorts all fields with type ‘Number’ in ascending/descending order.
api_token: String, Requiered. Your api_token to access the API. You will get it after registration.
limit: Number, Optional. The number of results should be returned with the query. Default value: 50, minimum value: 1, maximum value: 100.
offset: Number, Optional. The offset of the data. Default value: 0, minimum value: 0, maximum value: 999. For example, to get 100 symbols starting from 200 you should use limit=100 and offset=200.
Output
The output for the API request above:


Filtering data by fields
Various filter fields come in two types: Strings and Numbers. String Operations should be applied to strings, while Numeric Operations are suitable for numbers (see further). List of supported filter fields:

code: String. Filters by the ticker code.
name: String. Filters by the ticker name.
exchange: String. Filters by the exchange code. The list of all exchange codes is here. In addition, it’s possible to use ‘NYSE’ and ‘NASDAQ’ exchange codes to filter out only tickers from these exchanges.
sector: String. Filters by sector. The list of sectors and industries is here. Please note: two-word sectors and industries require the string operation “match” instead of “=”.
industry: String. Filters by industry. The list of sectors and industries is here.
market_capitalization: Number. Filters by Market Capitalization, the latest value. Please note, that input for market_capitalization in USD.
earnings_share: Number. Filters by Earnings-per-share (EPS), the latest value.
dividend_yield: Number. Filters by Dividend yield, the latest value.
refund_1d_p: Number. The last day gain/loss in percent. Useful to get top gainers, losers for the past day.
refund_5d_p: Number. The last 5 days gain/loss in percent. Useful to get top gainers, losers for the past week.
avgvol_1d: Number. The last day volume.
avgvol_200d: Number. The average last 200 days volume.
adjusted_close: Number. The latest known EOD adjusted close.
Example: Filter all companies with a market capitalization above 1 billion, positive EPS within the ‘Personal Products’ industry, and names starting with the letter ‘B’:

https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&sort=market_capitalization.desc&filters=[[“market_capitalization”,”>”,1000000000],[“earnings_share”,”>”,0],[“industry”,”match”,”Personal Products”],[“name”,”match”,”B*”]]&limit=10&offset=0

List of Operations
String operations are supported for all fields with the type ‘String’. Numeric Operations are supported for all fields with type ‘NUMBER’:

String Operations: [‘=’, ‘match’].
Numeric Operations: [‘=’, ‘>’, ‘<‘, ‘>=’, ‘<=’].
Filtering Data with Signals
You can use signals to filter tickers by different calculated fields. All signals are pre-calculated on our side.

For example, if you need only tickers that have new lows for the past 200 days and the Book Value is negative, you can use the parameter ‘signal’ with the following value, to get all tickers with the criteria:

signals=bookvalue_neg,200d_new_lo

List of supported Signals
200d_new_lo, 200d_new_hi – filters tickers that have new 200 days’ lows or new 200 days’ highs.
bookvalue_neg, bookvalue_pos – filters tickers with positive Book Value or with Negative Book Value.
wallstreet_lo, wallstreet_hi – filters tickers that have a price lower or higher than expected by Wall Street analysts.
We continuously develop new signals and can accommodate additional ones upon request. Feel free to contact us on our forum or via support@eodhistoricaldata.com.
Consumption
Each Screener API request consumes 5 API calls. Best to be used together with our other APIs.

Screener and Technical Indicators are integrated into our Google Sheets & Excel add-ons and in Python library already.

