---title: MarketData API Docs (consolidated)source_root: https://www.marketdata.app/docs/apipage_count: 47fetched_at: 2025-08-01T23:31:11Z---# MarketData API Documentation (Consolidated)
_Source root: https://www.marketdata.app/docs/api • Fetched at: 2025-08-01T23:31:11Z_
## Table of Contents
- [Introduction](#introduction)
- [Authentication](#authentication)
- [Universal Parameters](#universal-parameters)
- [Dates and Times](#dates-and-times)
- [Mutual Funds](#mutual-funds)
- [CandlesNew](#candlesnew)
- [Markets](#markets)
- [Status](#status)
- [Options](#options)
- [Option Chain](#option-chain)
- [Expirations](#expirations)
- [Lookup](#lookup)
- [QuotesHigh Usage](#quoteshigh-usage)
- [Strikes](#strikes)
- [Rate Limits](#rate-limits)
- [SDKs](#sdks)
- [Stocks](#stocks)
- [Bulk Historical Candles](#bulk-historical-candles)
- [Market Data](#market-data)
- [Historical Candles](#historical-candles)
- [EarningsPremium](#earningspremium)
- [NewsBeta](#newsbeta)
- [Real-Time PricesHigh Usage](#real-time-priceshigh-usage)
- [Delayed Quotes](#delayed-quotes)
- [Tags](#tags)
- [One doc tagged with "API: Beta"](#one-doc-tagged-with-api-beta)
- [2 docs tagged with "API: High Usage"](#2-docs-tagged-with-api-high-usage)
- [One doc tagged with "API: Premium"](#one-doc-tagged-with-api-premium)
- [Troubleshooting](#troubleshooting)
- [Authentication](#authentication-2)
- [HTTP Status Codes](#http-status-codes)
- [Logging](#logging)
- [Multiple IP Addresses](#multiple-ip-addresses)
- [Service Outages](#service-outages)
- [URL Parameters](#url-parameters)
- [Columns](#columns)
- [Date Format](#date-format)
- [Data FeedPremium](#data-feedpremium)
- [Format](#format)
- [Headers](#headers)
- [Human Readable](#human-readable)
- [Limit](#limit)
- [Offset](#offset)
- [Token](#token)
- [Utilities](#utilities)
- [Headers](#headers-2)
- [API StatusNew](#api-statusnew)

---

# Introduction
<a id="introduction"></a>

<sub>Source: https://www.marketdata.app/docs/api</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Introduction

On this pageIntroductionThe Market Data API is designed around REST and supports standard HTTP response codes and methods. All responses are delivered via JSON for programmatic use of the information or via CSV files to load into your preferred spreadsheet application.

Root Endpoint[https://api.marketdata.app/](https://api.marketdata.app/)https://api.marketdata.app/

## Try Our API ​

The easiest way to try out our API is using our [Swagger User Interface](https://api.marketdata.app/)Swagger User Interface, which will allow you to try out your API requests directly from your browser.

tipOur endpoints have lots of optional parameters to allow users to sort and filter responses. It can be overwhelming to new users at first. When you're first getting started testing our API in Swagger, scroll to the required parameters and ignore all the optional ones. Most endpoints require only a ticker symbol as a required parameter.

#### Get Started Quick — No Registration Required! ​

You can try stock, option, index, and mutual fund endpoints with several different symbols that are unlocked and require no authorization token. That means these symbols can be used throughout our API with no registration required!

- Stock endpoints: Use AAPL.
- Options endpoints: Use any AAPL contract, for example: AAPL271217C00250000.
- Mutual fund endpoints: Use VFINX.

Once you would like to experiment with other symbols, [register a free account](https://www.marketdata.app/signup/)register a free account (no credit card required) and you be able to choose a free trial. After your trial ends, if you decide not to subscribe, you will still get 100 free requests per day. Make the decision to pay only after making a complete trial of our API.

Edit this pageNextSDKs- Try Our API

---

# Authentication
<a id="authentication"></a>

<sub>Source: https://www.marketdata.app/docs/api/authentication</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Authentication

On this pageAuthenticationThe Market Data API uses a Bearer Token for authentication. The token is a programmatic representation of your username and password credentials, so you must keep it secret just as you would your username and password. The token is required for each request you make to the API.

## Obtaining a Token ​

To obtain it, sign-in to your customer dashboard using your username and password and request a token. It will be delivered by email to the address you used to sign-in.

## Using the Token ​

There are two ways to pass this token to the API with your requests:

1. Header Authentication
2. URL Parameter Authentication

tipWe recommend using header-based authentication to ensure your token is not stored or cached. While Market Data makes a conscientious effort to delete tokens from our own server logs, we cannot guarantee that your token will not be stored by any of our third party cloud infrastructure partners.

## Header Authentication ​

Add the token to the `Authorization`Authorization header using the word `Bearer`Bearer.

### Code Examples ​

- HTTP
- Node.js
- Python
- Go

```http
GET /v1/stocks/quotes/SPY/ HTTP/1.1Host: api.marketdata.appAccept: application/jsonAuthorization: Bearer {token}
```

tipThe curly braces around token are a placeholder for this example. Do not actually wrap your token with curly braces.

```javascript
const https = require('https');// Your tokenconst token = 'your_token_here';// The API endpoint for retrieving stock quotes for SPYconst url = 'https://api.marketdata.app/v1/stocks/quotes/SPY/';// Making the GET request to the APIhttps.get(url, {    headers: {        'Accept': 'application/json',        'Authorization': `Bearer ${token}`    }}, (response) => {    let data = '';    // A chunk of data has been received.    response.on('data', (chunk) => {        data += chunk;    });    // The whole response has been received. Print out the result.    response.on('end', () => {        if (response.statusCode === 200 || response.statusCode === 203) {            console.log(JSON.parse(data));        } else {            console.log(`Failed to retrieve data: ${response.statusCode}`);        }    });}).on("error", (err) => {    console.log("Error: " + err.message);});
```

```python
import requests# Your tokentoken = 'your_token_here'# The API endpoint for retrieving stock quotes for SPYurl = 'https://api.marketdata.app/v1/stocks/quotes/SPY/'# Setting up the headers for authenticationheaders = {    'Accept': 'application/json',    'Authorization': f'Bearer {token}'}# Making the GET request to the APIresponse = requests.get(url, headers=headers)# Checking if the request was successfulif response. status_code in (200, 203):    # Parsing the JSON response    data = response.json()    print(data)else:    print(f'Failed to retrieve data: {response.status_code}')
```

```go
// Import the Market Data SDKimport api "github.com/MarketDataApp/sdk-go"func main() {    // Create a new Market Data client instance    marketDataClient := api.New()    // Set the token for authentication    // Replace "your_token_here" with your actual token    marketDataClient.Token("your_token_here")    // Now the client is ready to make authenticated requests to the Market Data API        // Use the client to create a StockQuoteRequest	sqr, err := api.StockQuote(marketDataClient).Symbol("SPY").Get()    if err != nil {		fmt.Println("Error fetching stock quotes:", err)		return	}	// Process the retrieved quote	for _, quote := range quotes {		fmt.Printf(quote)	}}
```

## URL Parameter Authentication ​

Add the token as a variable directly in the URL using the format `token=YOUR_TOKEN_HERE`token=YOUR_TOKEN_HERE. For example:

```text
https://api.marketdata.app/v1/stocks/quotes/SPY/?token={token}
```

tipThe curly braces around token are a placeholder for this example. Do not actually wrap your token with curly braces.

## Demo The API With No Authentication ​

You can try stock, option, and index endpoints with several different symbols that are unlocked and do not require a token. Please be aware that only historical data for these tickers is available without a token.

- Try any stock endpoint with AAPL, no token required.
- Try any option endpoint with any AAPL contract, for example: AAPL271217C00250000. No token required.

## IP Address Restrictions ​

Due to exchange regulations prohibiting data redistribution without a commercial license, Market Data strictly enforces a single device policy. This means:

1. Only one IP address is allowed per account at any given time
2. Multiple simultaneous connections from different IP addresses are not permitted
3. Account sharing or data redistribution is strictly prohibited

If your IP address changes, your account will be temporarily blocked for security reasons, even if you are authenticated. This is to prevent unauthorized data redistribution and ensure compliance with exchange regulations. Please wait 5 minutes before trying again.

warningAttempting to circumvent these restrictions by sharing accounts or redistributing data will result in permanent account suspension.

Edit this pagePreviousSDKsNextRate Limits- Obtaining a Token
- Using the Token
- Header Authentication
  - Code Examples
- URL Parameter Authentication
- Demo The API With No Authentication
- IP Address Restrictions

---

# Universal Parameters
<a id="universal-parameters"></a>

<sub>Source: https://www.marketdata.app/docs/api/category/universal-parameters</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters

Universal ParametersThe following parameters are universal and can be used with any endpoint unless otherwise indicated in that endpoint's documentation.

## 📄️ Token

The token parameter allows you to submit a read-only access token as a parameter. If your access token is write-enabled (authorized for trading), you may not use the token as a parameter, and must submit it in a header.

## 📄️ Format

The format parameter is used to specify the format for your data. We support JSON and CSV formats. The default format is JSON.

## 📄️ Date Format

The dateformat parameter allows you specify the format you wish to receive date and time information in.

## 📄️ Limit

The limit parameter allows you to limit the number of results for a particular API call or override an endpoint’s default limits to get more data.

## 📄️ Offset

The offset parameter is used together with limit to allow you to implement pagination in your application. Offset will allow you to return values starting at a certain value.

## 📄️ Columns

The columns parameter is used to limit the results of any endpoint to only the columns you need.

## 📄️ Headers

The headers parameter is used to turn off headers when using CSV output.

## 📄️ Human Readable

The human parameter will use human-readable attribute names in the JSON or CSV output instead of the standard camelCase attribute names. Use of this parameter will result in API output that can be loaded directly into a table or viewer and presented to an end-user with no further transformation required on the front-end.

## 📄️ Data Feed

The feed parameter allows the user to modify the data feed used for the API's response, forcing it to use cached data.

PreviousHeadersNextToken

---

# Dates and Times
<a id="dates-and-times"></a>

<sub>Source: https://www.marketdata.app/docs/api/dates-and-times</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Dates and Times

On this pageDates and TimesAll Market Data endpoints support advanced date-handling features to allow you to work with dates in a way that works best for your application. Our API will accept date inputs in any of the following formats:

- American Numeric Notation Dates and times in MM/DD/YYYY format. For example, closing bell on Dec 30, 2020 for the NYSE would be: 12/30/2020 4:00 PM.
- Timestamp An ISO 8601 timestamp in the format YYYY-MM-DD. For example, closing bell on Dec 30, 2020 for the NYSE would be: 2020-12-30 16:00:00.
- Unix Dates and times in unix format (seconds after the unix epoch). For example, closing bell on Dec 30, 2020 for the NYSE would be: 1609362000.
- Spreadsheet Dates and times in spreadsheet format (days after the Excel epoch). For example, closing bell on Dec 30, 2020 for the NYSE would be: 44195.66667
- Relative Dates and Times Keywords or key phrases that indicate specific days, relative to the current date. For example, "today" or "yesterday".
- Option Expiration Dates Keyphrase that select specific dates that correspond with dates in the US option expiration calendar.

## Relative Dates and Times ​

This feature allows you to use natural language to specify dates and times in a way that is easy for humans to read and understand, but can be tricky for machines to parse.

Relative dates allow Market Data endpoints to continually modify the date sent to the endpoint based on the current date. We have a lot of relative date keywords supported already and quite a few more planned for the future, so keep an eye out on this section for continual improvements to this feature.

- Time-based Parameters Time keyphrases let you select a specific time of day, relative to the current time. Time-based parameters are typically used to model intraday stock movements.
  - now Equivalent to the current time. Use this keyword to select the current open candle, for example.
  - -[number] minutes Use negative minutes to specify a time in the past n minutes before. When this is used alone, it is relative to the current time. When used in conjunction in from field (i.e. the starting date/time), it is relative to the to field (i.e. the ending date/time). For example, if the current time is 10:30 AM, but 10:00 AM is used in the to field and -10 minutes in the from field, then the starting time will be 9:50 AM. The query would return values from 9:50 AM to 10:00 AM. However, if the to field were to be omitted, then the same query would return data from 10:20 AM to 10:30 AM since -10 minutes would be relative to the current time of 10:30 AM.
  - [number] minutes ago The minutes ago keyword lets you select a relative time, n minutes before the current time. For example, if the time is 10:00 AM then 30 minutes ago would refer to 9:30 AM of the current day.
  - -[number] hours Use negative hours to specify a time in the past n hours before. When this is used alone, it is relative to the current time. When used in conjunction in from field (i.e. the starting date/time), it is relative to the to field (i.e. the ending date/time). For example, if the current time is 10:30 AM, but 10:00 AM is used in the to field and -1 hour in the from field, then the starting time will be 9:00 AM. The query would return values from 9:00 AM to 10:00 AM. However, if the to field were to be omitted, then the same query would return data from 9:30 AM to 10:30 AM since -1 hour would be relative to the current time of 10:30 AM.
  - [number] hours ago The hours ago keyword lets you select a relative time, n hours before the current time. For example, if the time is 4:00 PM then 4 hours ago would refer to 12:00 PM of the current day.
- Daily Parameters Daily keyphrases let you select a specific day, relative to the current day.
  - today Equivalent to today's date.
  - yesterday Yesterday's date.
  - -[number] days Use negative days to specify a time in the past n days before. When this is used alone, it is relative to the current day. When used in conjunction in from field (i.e. the starting date), it is relative to the to field (i.e. the ending date). For example, if the current date is January 20, but January 10 is used in the to field and -5 days in the from field, then the starting day will be January 5. The query would return values from January 5 to January 10. However, if the to field were to be omitted, then the same query would return data from January 15 to January 20 since -5 days would be relative to the current date of January 20.
  - [number] days ago The days ago keyword lets you select a relative day, n days before the current date. For example, if today is January 5, 2024, then using 2 days ago would select the date January 3, 2024.
- Weekly Parameters Weekly keyphrases let you select a day of the week in the current, previous, or following week.
  - -[number] weeks Use negative weeks to specify a date in the past n weeks before. When this is used alone, it is relative to the current day. When used in conjunction in from field (i.e. the starting date), it is relative to the date in the to field (i.e. the ending date). For example, if the current date is October 15, 2023 but October 8 is used in the to field and -1 week in the from field, then the starting day will be October 2, 2023. The query would return values from October 2 to October 8. However, if the to field were to be omitted, then the same query would return data from October 9 to October 15 since -5 days would be relative to the current date of January 20.
  - [number] weeks ago The weeks ago keyword lets you select a relative week, n weeks before the current date. For example, if today is January 1, 2024, then using 2 weeks ago would select the date January 3, 2024.
- Monthly Dates Monthly keyphrases let you select a specific day of a specific month.
  - -[number] months Use negative months to specify a date in the past n months before. When this is used alone, it is relative to the current day. When used in conjunction in from field (i.e. the starting date), it is relative to the date in the to field (i.e. the ending date). For example, if the current date is October 15 but October 8 is used in the to field and -1 month in the from field, then the starting day will be September 8. The query would return values from September 8 to October 8. However, if the to field were to be omitted, then the same query would return data from September 15 to October since -1 month would be relative to the current date of October 15.
  - [number] months ago The months ago keyword lets you select a relative date, n months before the current date. For example, if today is January 5, 2024, then using 3 months ago would select the date October 5, 2023.
- Yearly Dates Yearly keyphrases let you select a specific day of in the current, previous, or following year.
  - -[number] years Use negative years to specify a date in the past n years before. When this is used alone, it is relative to the current day. When used in conjunction in from field (i.e. the starting date), it is relative to the date in the to field (i.e. the ending date). For example, if the current date is October 15, 2023 but October 8, 2023 is used in the to field and -1 year in the from field, then the starting day will be September 8, 2022. The query would return values from September 8, 2022 to October 8, 2023. However, if the to field were to be omitted, then the same query would return data from September 15, 2022 to October 15, 2023 since -1 year would be relative to the current date of October 15, 2023.
  - [number] years ago The years ago keyword lets you select a relative date, 365 days before the current date. For example, if today is January 5, 2024, then using 2 years ago would select the date January 5, 2022.

Coming SoonThe following relative date parameters are planned for the future and have not yet been implemented.

- Time-based Parameters Time keyphrases let you select a specific time of day, relative to the current time. Time-based parameters are typically used to model intraday stock movements.
  - at open , opening bell , market open These keyphrases let you select the opening time for the market day. The phase is relative to each exchange's opening time. For example, if you were trading AAPL in the United States, using at open would set a time of 9:30 AM ET.
  - at close , closing bell , market close These keyphrases let you select the closing time for the market day. The phase is relative to each exchange's closing time. For example, if you were trading AAPL in the United States, using at close would set a time of 4:00 PM ET.
  - [number] [minutes|hours] before [open|close] These before keyword lets you select a relative time before market open or close. For example 30 minutes before close would select the time 3:30 PM ET if you are trading a stock on a U.S. exchange.
  - [number] [minutes|hours] after [open|close] These after keyword lets you select a relative time after market open or close. For example 1 hour after open would select the time 10:30 AM ET if you are trading a stock on a U.S. exchange.
- Weekly Parameters Weekly keyphrases let you select a day of the week in the current, previous, or following week.
  - this [day of the week] Works the same way as specifying the day without adding this . The day in the current week. For example, if today is Tuesday and the expression is this Monday , the date returned would be yesterday. If the expression were this Wednesday the date returned would be tomorrow. The word this is optional. If it is omitted, the keyword will still return the date in the current week that corresponds with the day mentioned.
  - last [day of the week] The day in the previous week. For example, if today is Tuesday and the expression used is last Monday , it would not refer to the Monday that occurred yesterday, but the Monday 8 days prior that occurred in the previous week.
  - next [day of the week] The day in the following week. For example, if today is Monday and the expression is next Tuesday it would not refer to tomorrow, but the Tuesday that occurs 8 days from now.
- Monthly Dates Monthly keyphrases let you select a specific day of a specific month.
  - [ordinal number] of [the|this] month - The nth day of the current month. For example, if today is September 10th and the phrase used is, 8th of this month the date returned would be September 8. The keyphrase of [the/this] month is optional. Using a single ordinal number 8th will also return the 8th of the current month.
  - [ordinal number] of last month - The nth day of the current month. For example, if today is December 15th and the phrase used is, 8th of last month the date returned would be November 8.
  - ordinal number] of next month - The nth day of the following month. For example, if today is December 15th and the phrase used is, 8th of next month the date returned would be January 8 of the following year.
  - last day of [the|this|last|next] month - Using the last day of keyword will always select the final day of the month. Since months can end on the 28th, 29th, 30th, or 31st, this keyword allows you to always select the final day of a month. For example: last day of this month , last day of next month . It can also be used to select the last day in February without needing to determine whether the current year is a leap year, last day of february .
  - ordinal number] [day of the week] of [the|this|last|next] month - Combine ordinal numbers and weekdays to specify a specific day of the week in the current, previous, or following month. For example, 3nd Friday of last month .
  - last [day of the week] of [the|this|last|next] month - Selects the last day of the week in a month relative to the current month. If the last Monday of the month is needed, instead of using the keyphrase 4th Monday of this month , it is safer to use last Monday of this month , since months can have 4 or 5 Mondays, depending on length.
  - last [day of the week] in [month - Selects the last day of the week in a specific month. For example, Memorial Day could be selected by using the keyphrase last Monday in May .
- Yearly Dates Yearly keyphrases let you select a specific day of in the current, previous, or following year.
  - [month] [number] A specific date in the current year. For example February 18 would return February 18 of the current year.
  - [month] [number] [this|last|next] year A specific date in the current, previous, or following year. For example, if today was Dec 31, 2022, February 18 next year would return February 18, 2023.

## Option Expiration Dates ​

Option expiration dates let you target the expiration dates for option contracts. Dates are based on the US option expirations calendar and are only meant for use with US markets.

cautionOption date parameters are planned for the future and have not yet been implemented.


---

Option-related keyphrases cannot be used to return expiration dates far in the future for options which have not yet been traded or for options in the past which have already expired. For example, if today is January 15, 2023, you couldn't use `November 2023's 1st weekly expiration`November 2023's 1st weekly expiration since weekly options for November would not exist yet. The formula will return a `No data`No data response if you try to request an expiration that does not exist, whether in the future or the past.

- Monthly Expirations - Target a relative month or specific month's option expiration date.
  - [month] [year] expiration - The standard monthly option expiration date for [month] during [year]. This is useful for targeting the expiration date for a specific month. Although options normally expire the 3rd Friday, sometimes market holidays can modify this schedule. Using an option expiration keyphrase will ensure that you always obtain the exact date that options expire in a specific month. For example, if today was January 1, 2022, using December expiration or December 2022 expiration would both return December 16, 2022 .
    - [year] is optional. If [month] is used without [year] the lookup is relative to the current date and expired options will not be returned. For example, if today is April 8, 2022, January expiration will return January 20, 2023 and not the options which expired in January of 2022.
  - this|last|next] month's expiration - Returns the monthly option expiration date for the current, previous, or following month relative to the current month. For example if today is October 5, 2022, and next month's expiration is used, the date returned would be November 18, 2022 .

tipNot all underlying tickers offer weekly or quarterly options. Before building an API request that uses them, ensure that your underlying offers weekly or quarterly option contracts.

- Weekly Expirations - Target a relative week or specific week's option expiration date.
  - [this|last|next] week's expiration - Returns the weekly option expiration date for the current, previous, or following week relative to the current week. For example if today is October 5, 2022, and next week's expiration is used, the date returned would be October 14, 2022 .
  - expiration in [number] weeks - Returns closest expiration that will occur [number] weeks from today without taking into account the current week. For example, if today is August 1, 2022 the phrase expiration in 6 weeks would return September 16, 2022.
  - [month] [year] [ordinal number] weekly expiration - Returns the nth option expiration date for [month] during [year]. When both a month and year are combined, this can be used to lookup a weekly option date for an expired or unexpired option. For example, March 2020's 2nd expiration would return March 14, 2020 .
- Quarterly Expirations - Returns a quarterly expiration date for a relative date or specifically targeted date.
  - [ordinal number] quarter's expiration - Returns the quarterly option expiration date for the 1st, 2nd, 3rd, or 4th quarter in the current financial year. For example if today is March 1, 2022, and 4th quarter's expiration is used, the date returned would be December 30, 2022 . This will lookup both expired and unexpired options.
  - [this|last|next] quarter's expiration - Returns the quarterly option expiration date for the current, previous, or following quarter relative to the current date. For example if today is March 1, 2026, and this quarter's expiration is used, the date returned would be March 31, 2026 .
  - [expiration in [number] quarters - Returns closest quarterly expiration that will occur [number] quarters from today without taking into account the current quarter. For example, if today is March 1, 2022 the phrase expiration in 2 quarters would return September 30, 2022.
  - [year] [ordinal number] quarter expiration - Returns the option expiration date for [nth] quarter during [year]. For example, 2020's 2nd quarter expiration would return June 30, 2020 .
- Specific Contract Expirations - Target a specific date based on when a contract is first traded or when it expires.
  - at expiration - Returns the expiration date for the option contract. This must be used in the context of a specific option contract. For example, if you used at expiration with AAPL230120C00150000, the date returned would be January 20, 2023.
  - first traded - Returns the date when the contract was traded for the first time. This must be used in the context of a specific option contract. For example, if you used first traded with AAPL230120C00150000, the date returned would be September 14, 2020.

Edit this pagePreviousRate LimitsNextMarkets- Relative Dates and Times
- Option Expiration Dates

---

# Mutual Funds
<a id="mutual-funds"></a>

<sub>Source: https://www.marketdata.app/docs/api/funds</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
  - Candles New
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Mutual Funds

On this pageMutual FundsThe mutual funds endpoints offer access to historical pricing data for mutual funds.

## Root Endpoint For Mutual Funds ​

```text
https://api.marketdata.app/v1/funds/
```

## Funds Endpoints ​

## 📄️ Candles

Get historical price candles for a mutual fund.

Edit this pagePreviousQuotesNextCandles- Root Endpoint For Mutual Funds
- Funds Endpoints

---

# CandlesNew
<a id="candlesnew"></a>

<sub>Source: https://www.marketdata.app/docs/api/funds/candles</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
  - Candles New
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Mutual Funds
- Candles

On this pageCandlesNewGet historical price candles for a mutual fund.

warningThis endpoint will be live on May 1, 2024. Before May 1, use the stocks/candles endpoint to query mutual fund candles.

## Endpoint ​

```text
https://api.marketdata.app/v1/funds/candles/{resolution}/{symbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/funds/candles/D/VFINX?from=2020-01-01&to=2020-01-10](https://api.marketdata.app/v1/funds/candles/D/VFINX?from=2020-01-01&to=2020-01-10)https://api.marketdata.app/v1/funds/candles/D/VFINX?from=2020-01-01&to=2020-01-10

fundCandles.js```js
fetch(  "https://api.marketdata.app/v1/funds/candles/D/VFINX?from=2020-01-01&to=2020-01-10")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

fundCandles.py```python
import requestsurl = "https://api.marketdata.app/v1/funds/candles/D/VFINX?from=2020-01-01&to=2020-01-10"response = requests.request("GET", url)print(response.text)
```

fundCandles.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleFundCandlesRequest() {  fcr, err := FundCandles().Resolution("D").Symbol("VFINX").From("2023-01-01").To("2023-01-06").Get()  if err != nil {    fmt.Print(err)    return  }  for _, candle := range fcr {    fmt.Println(candle)  }}
```

## Response Example ​

```json
{  "s":"ok",  "t":[1577941200,1578027600,1578286800,1578373200,1578459600,1578546000,1578632400],  "o":[300.69,298.6,299.65,298.84,300.32,302.39,301.53],  "h":[300.69,298.6,299.65,298.84,300.32,302.39,301.53],  "l":[300.69,298.6,299.65,298.84,300.32,302.39,301.53],  "c":[300.69,298.6,299.65,298.84,300.32,302.39,301.53]}
```

## Request Parameters ​

- Required

- resolution string
The duration of each candle.
  - Daily Resolutions: (daily, D, 1D, 2D, ...)
  - Weekly Resolutions: (weekly, W, 1W, 2W, ...)
  - Monthly Resolutions: (monthly, M, 1M, 2M, ...)
  - Yearly Resolutions:(yearly, Y, 1Y, 2Y, ...)
- symbol string
The mutual fund's ticker symbol.
- from date
The leftmost candle on a chart (inclusive). If you use countback , to is not required. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- to date
The rightmost candle on a chart (inclusive). Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- countback number
Will fetch a number of candles before (to the left of) to . If you use from , countback is not required.

## Response Attributes ​

- Success
- No Data
- Error

- s string
ll always be ok when there is data for the candles requested.
- o array[number]
Open price.
- h array[number]
High price.
- l array[number]
Low price.
- c array[number]
Close price.
- t array[number]
Candle time (Unix timestamp, Eastern Time Zone). Daily, weekly, monthly, yearly candles are returned without times.

- s string
Status will be no_data if no candles are found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousMutual FundsNextUtilities- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Markets
<a id="markets"></a>

<sub>Source: https://www.marketdata.app/docs/api/markets</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
  - Status
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Markets

On this pageMarketsThe Markets endpoints provide reference and status data about the markets covered by Market Data.

## Root Endpoint For Markets ​

```text
https://api.marketdata.app/v1/markets/
```

## Markets Endpoints ​

## 📄️ Status

Get the past, present, or future status for a stock market. The endpoint will respond with "open" for trading days or "closed" for weekends or market holidays.

Edit this pagePreviousDates and TimesNextStatus- Root Endpoint For Markets
- Markets Endpoints

---

# Status
<a id="status"></a>

<sub>Source: https://www.marketdata.app/docs/api/markets/status</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
  - Status
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Markets
- Status

On this pageStatusGet the past, present, or future status for a stock market. The endpoint will respond with "open" for trading days or "closed" for weekends or market holidays.

## Endpoint ​

```text
https://api.marketdata.app/v1/markets/status/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/markets/status/?from=2020-01-01&to=2020-12-31](https://api.marketdata.app/v1/markets/status/?from=2020-01-01&to=2020-12-31)https://api.marketdata.app/v1/markets/status/?from=2020-01-01&to=2020-12-31

GET [https://api.marketdata.app/v1/markets/status/?date=yesterday](https://api.marketdata.app/v1/markets/status/?date=yesterday)https://api.marketdata.app/v1/markets/status/?date=yesterday

app.js```js
fetch(  "https://api.marketdata.app/v1/markets/status/?from=2020-01-01&to=2020-12-31")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });fetch("https://api.marketdata.app/v1/markets/status/?date=yesterday")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl1 = "https://api.marketdata.app/v1/markets/status/?from=2020-01-01&to=2020-12-31"url2 = "https://api.marketdata.app/v1/markets/status/?date=yesterday"response1 = requests.request("GET", url1)response2 = requests.request("GET", url2)print(response1.text)print(response2.text)
```

marketstatus.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleMarketStatus() {	msr, err := api.MarketStatus().From("2020-01-01").To("2020-12-31").Get()	if err != nil {		fmt.Print(err)		return	}	for _, report := range msr {		fmt.Println(report)	}}func ExampleMarketStatus_relativeDates() {	msr, err := api.MarketStatus().Date("yesterday").Get()	if err != nil {		fmt.Print(err)		return	}	for _, report := range msr {		fmt.Println(report)	}}
```

## Response Example ​

```json
{  "s": "ok",  "date": [1680580800],  "status": ["open"]}
```

## Request Parameters ​

- Required
- Optional

- There are no required parameters for status. If no parameter is given, the request will return the market status in the United States for the current day.

- country string
Use to specify the country. Use the two digit ISO 3166 country code. If no country is specified, US will be assumed. Only countries that Market Data supports for stock price data are available (currently only the United States).
- date date
Consult whether the market was open or closed on the specified date. Accepted timestamp inputs: ISO 8601, unix, spreadsheet, relative date strings.
- from date
The earliest date (inclusive). If you use countback, from is not required. Accepted timestamp inputs: ISO 8601, unix, spreadsheet, relative date strings.
- to date
The last date (inclusive). Accepted timestamp inputs: ISO 8601, unix, spreadsheet, relative date strings.
- countback number
Countback will fetch a number of dates before to If you use from, countback is not required.

## Response Attributes ​

- Success
- No Data
- Error

- s string
ll always be ok when there is data for the dates requested.
- date array[dates]
The date.
- status array[string]
The market status. This will always be open or closed or null . Half days or partial trading days are reported as open . Requests for days further in the past or further in the future than our data will be returned as null .

- s string
Status will be no_data if no data is found for the request.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousMarketsNextStocks- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Options
<a id="options"></a>

<sub>Source: https://www.marketdata.app/docs/api/options</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options

On this pageOptionsThe Market Data API provides a comprehensive suite of options endpoints, designed to cater to various needs around options data. These endpoints are designed to be flexible and robust, supporting both real-time and historical data queries. They accommodate a wide range of optional parameters for detailed data retrieval, making the Market Data API a versatile tool for options traders and financial analysts.

## Root Endpoint For Options ​

```text
https://api.marketdata.app/v1/options/
```

## Options Endpoints ​

## 📄️ Expirations

Get a list of current or historical option expiration dates for an underlying symbol. If no optional parameters are used, the endpoint returns all expiration dates in the option chain.

## 📄️ Lookup

Generate a properly formatted OCC option symbol based on the user's human-readable description of an option. This endpoint converts text such as "AAPL 7/28/23 $200 Call" to OCC option symbol format: AAPL230728C00200000. The user input must be URL-encoded.

## 📄️ Strikes

Get a list of current or historical options strikes for an underlying symbol. If no optional parameters are used, the endpoint returns the strikes for every expiration in the chain.

## 📄️ Option Chain

Get a current or historical end of day options chain for an underlying ticker symbol. Optional parameters allow for extensive filtering of the chain. Use the optionSymbol returned from this endpoint to get quotes, greeks, or other information using the other endpoints.

## 📄️ Quotes

Get a current or historical end of day quote for a single options contract.

Edit this pagePreviousBulk Historical CandlesNextExpirations- Root Endpoint For Options
- Options Endpoints

---

# Option Chain
<a id="option-chain"></a>

<sub>Source: https://www.marketdata.app/docs/api/options/chain</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options
- Option Chain

On this pageOption ChainGet a current or historical end of day options chain for an underlying ticker symbol. Optional parameters allow for extensive filtering of the chain. Use the optionSymbol returned from this endpoint to get quotes, greeks, or other information using the other endpoints.

## Endpoint ​

```text
https://api.marketdata.app/v1/options/chain/{underlyingSymbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/options/chain/AAPL/?expiration=2025-01-17&side=call](https://api.marketdata.app/v1/options/chain/AAPL/?expiration=2025-01-17&side=call)https://api.marketdata.app/v1/options/chain/AAPL/?expiration=2025-01-17&side=call

app.js```js
fetch("https://api.marketdata.app/v1/options/chain/AAPL/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/options/chain/AAPL/"response = requests.request("GET", url)print(response.text)
```

optionChain.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleOptionChainRequest() {	AAPL, err := OptionChain().UnderlyingSymbol("AAPL").Get()	if err != nil {		fmt.Println("Error fetching option chain:", err)		return	}	for _, contract := range AAPL {		fmt.Println(contract)	}}
```

## Response Example ​

```json
{  "s": "ok",  "optionSymbol": [    "AAPL230616C00060000", "AAPL230616C00065000", "AAPL230616C00070000", "AAPL230616C00075000", "AAPL230616C00080000", "AAPL230616C00085000", "AAPL230616C00090000", "AAPL230616C00095000", "AAPL230616C00100000", "AAPL230616C00105000", "AAPL230616C00110000", "AAPL230616C00115000", "AAPL230616C00120000", "AAPL230616C00125000", "AAPL230616C00130000", "AAPL230616C00135000", "AAPL230616C00140000", "AAPL230616C00145000", "AAPL230616C00150000", "AAPL230616C00155000", "AAPL230616C00160000", "AAPL230616C00165000", "AAPL230616C00170000", "AAPL230616C00175000", "AAPL230616C00180000", "AAPL230616C00185000", "AAPL230616C00190000", "AAPL230616C00195000", "AAPL230616C00200000", "AAPL230616C00205000", "AAPL230616C00210000", "AAPL230616C00215000", "AAPL230616C00220000", "AAPL230616C00225000", "AAPL230616C00230000", "AAPL230616C00235000", "AAPL230616C00240000", "AAPL230616C00245000", "AAPL230616C00250000", "AAPL230616C00255000", "AAPL230616C00260000", "AAPL230616C00265000", "AAPL230616C00270000", "AAPL230616C00280000", "AAPL230616C00290000", "AAPL230616C00300000", "AAPL230616P00060000", "AAPL230616P00065000", "AAPL230616P00070000", "AAPL230616P00075000", "AAPL230616P00080000", "AAPL230616P00085000", "AAPL230616P00090000", "AAPL230616P00095000", "AAPL230616P00100000", "AAPL230616P00105000", "AAPL230616P00110000", "AAPL230616P00115000", "AAPL230616P00120000", "AAPL230616P00125000", "AAPL230616P00130000", "AAPL230616P00135000", "AAPL230616P00140000", "AAPL230616P00145000", "AAPL230616P00150000", "AAPL230616P00155000", "AAPL230616P00160000", "AAPL230616P00165000", "AAPL230616P00170000", "AAPL230616P00175000", "AAPL230616P00180000", "AAPL230616P00185000", "AAPL230616P00190000", "AAPL230616P00195000", "AAPL230616P00200000", "AAPL230616P00205000", "AAPL230616P00210000", "AAPL230616P00215000", "AAPL230616P00220000", "AAPL230616P00225000", "AAPL230616P00230000", "AAPL230616P00235000", "AAPL230616P00240000", "AAPL230616P00245000", "AAPL230616P00250000", "AAPL230616P00255000", "AAPL230616P00260000", "AAPL230616P00265000", "AAPL230616P00270000", "AAPL230616P00280000", "AAPL230616P00290000", "AAPL230616P00300000"  ],  "underlying": [    "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL", "AAPL"  ],  "expiration": [    1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600, 1686945600  ],  "side": [    "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "call", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put", "put"  ],  "strike": [    60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 280, 290, 300, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 280, 290, 300  ],  "firstTraded": [    1617197400, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616506200, 1616506200, 1616506200, 1616506200, 1616506200, 1616506200, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1617370200, 1617888600, 1618234200, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1626701400, 1626701400, 1626701400, 1626701400, 1617197400, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616506200, 1616506200, 1616506200, 1616506200, 1616506200, 1616506200, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1616592600, 1617370200, 1617888600, 1618234200, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1619184600, 1682083800, 1626701400, 1626701400, 1626701400, 1626701400  ],  "dte": [    26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26, 26  ],  "updated": [    1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875, 1684702875  ],  "bid": [    114.1, 108.6, 103.65, 98.6, 93.6, 88.9, 84.3, 80.2, 74.75, 70, 64.35, 59.4, 54.55, 50, 45.1, 40.45, 35.75, 30.8, 25.7, 20.6, 15.9, 11.65, 7.55, 4.15, 1.77, 0.57, 0.18, 0.07, 0.03, 0.02, 0.02, 0.01, 0.01, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.01, 0.01, 0.02, 0.02, 0.03, 0.04, 0.06, 0.07, 0.11, 0.14, 0.22, 0.32, 0.52, 0.92, 1.74, 3.3, 5.9, 9.8, 14.7, 19.3, 24.25, 28.7, 32.95, 38.65, 44.7, 48.4, 53.05, 58.8, 63.55, 68.05, 73.2, 78.5, 84.1, 88.05, 92.9, 103.15, 113.4, 123.05  ],  "bidSize": [    90, 90, 90, 90, 90, 90, 90, 98, 90, 102, 90, 90, 90, 90, 102, 90, 95, 95, 99, 258, 118, 202, 96, 38, 36, 30, 180, 310, 31, 319, 5, 822, 216, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 14, 64, 10, 163, 2, 5, 79, 31, 4, 1, 208, 30, 146, 5, 35, 1, 5, 6, 98, 90, 90, 90, 90, 90, 98, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90  ],  "mid": [    115.5, 110.38, 105.53, 100.5, 95.53, 90.28, 85.53, 80.68, 75.58, 70.75, 65.55, 60.67, 55.55, 50.9, 45.88, 40.7, 35.88, 30.93, 26.3, 20.93, 16.18, 11.78, 7.62, 4.2, 1.79, 0.58, 0.18, 0.08, 0.04, 0.03, 0.03, 0.01, 0.02, 0.09, 0.05, 0.09, 0.01, 0.08, 0.01, 0.08, 0.03, 0.23, 0.26, 0.51, 0.01, 0.01, 0.01, 0.01, 0.01, 0.03, 0.01, 0.08, 0.08, 0.01, 0.01, 0.01, 0.03, 0.07, 0.07, 0.04, 0.07, 0.08, 0.11, 0.16, 0.23, 0.33, 0.53, 0.94, 1.76, 3.33, 5.97, 10.2, 14.95, 20.52, 24.95, 30, 34.83, 39.88, 45, 49.83, 54.85, 59.85, 64.82, 69.75, 74.78, 80.12, 85.4, 89.9, 94.8, 104.95, 114.68, 124.82  ],  "ask": [    116.9, 112.15, 107.4, 102.4, 97.45, 91.65, 86.75, 81.15, 76.4, 71.5, 66.75, 61.95, 56.55, 51.8, 46.65, 40.95, 36, 31.05, 26.9, 21.25, 16.45, 11.9, 7.7, 4.25, 1.81, 0.6, 0.19, 0.08, 0.05, 0.04, 0.03, 0.02, 0.03, 0.17, 0.1, 0.17, 0.01, 0.16, 0.02, 0.16, 0.05, 0.46, 0.51, 1.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.02, 0.16, 0.16, 0.01, 0.02, 0.02, 0.04, 0.12, 0.1, 0.05, 0.07, 0.09, 0.12, 0.18, 0.23, 0.34, 0.54, 0.95, 1.78, 3.35, 6.05, 10.6, 15.2, 21.75, 25.65, 31.3, 36.7, 41.1, 45.3, 51.25, 56.65, 60.9, 66.1, 71.45, 76.35, 81.75, 86.7, 91.75, 96.7, 106.75, 115.95, 126.6  ],  "askSize": [    90, 90, 90, 90, 90, 90, 90, 102, 90, 96, 90, 90, 90, 90, 96, 102, 90, 95, 96, 114, 103, 126, 90, 156, 20, 98, 397, 563, 251, 528, 238, 1, 30, 117, 99, 173, 89, 151, 196, 90, 92, 90, 90, 248, 1, 340, 180, 75, 50, 156, 1, 174, 231, 50, 500, 48, 2, 222, 136, 229, 587, 411, 226, 1, 128, 105, 142, 188, 34, 61, 45, 120, 105, 109, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90  ],  "last": [    115, 107.82, 105.75, 100.45, 94.2, 90.66, 86, 81, 75.59, 71.08, 66.07, 61.64, 55.8, 50.77, 46.12, 41.05, 35.9, 30.81, 25.95, 21.3, 16.33, 11.8, 7.6, 4.2, 1.78, 0.59, 0.18, 0.08, 0.05, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, null, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.04, 0.05, 0.06, 0.08, 0.11, 0.16, 0.23, 0.33, 0.52, 0.93, 1.76, 3.27, 6, 10.1, 14.84, 20.74, 25.39, 30.65, 37.1, null, 44.8, 59.6, 55.35, null, 83.49, null, 101.5, null, 109.39, null, 120.55, 128.67, 139.85, 151.1  ],  "openInterest": [    21957, 3012, 2796, 1994, 1146, 558, 2598, 988, 6574, 509, 1780, 917, 2277, 1972, 10751, 6080, 35508, 17559, 33003, 32560, 49905, 75976, 56201, 62509, 59821, 39370, 24498, 51472, 17565, 921, 13428, 273, 6935, 518, 4496, 533, 8128, 10, 14615, 100, 6765, 0, 2481, 3831, 2474, 17228, 57338, 9503, 13614, 8027, 7938, 3752, 21276, 13550, 46981, 14401, 26134, 40858, 34215, 33103, 92978, 47546, 67687, 35527, 87587, 51117, 72338, 82643, 43125, 12822, 2955, 619, 112, 2, 44, 3, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ],  "volume": [    0, 0, 1, 4, 0, 8, 1, 43, 15, 49, 10, 5, 6, 5, 58, 72, 31, 427, 207, 104, 380, 1070, 3179, 7619, 10678, 5488, 1267, 718, 420, 73, 18, 1, 137, 348, 844, 27, 6, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 5, 0, 0, 0, 50, 23, 36, 32, 250, 142, 155, 135, 1969, 1068, 2005, 3018, 2641, 7861, 13154, 6299, 6389, 664, 101, 12, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ],  "inTheMoney": [    true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true  ],  "intrinsicValue": [    115.13, 110.13, 105.13, 100.13, 95.13, 90.13, 85.13, 80.13, 75.13, 70.13, 65.13, 60.13, 55.13, 50.13, 45.13, 40.13, 35.13, 30.13, 25.13, 20.13, 15.13, 10.13, 5.13, 0.13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4.87, 9.87, 14.87, 19.87, 24.87, 29.87, 34.87, 39.87, 44.87, 49.87, 54.87, 59.87, 64.87, 69.87, 74.87, 79.87, 84.87, 89.87, 94.87, 104.87, 114.87, 124.87  ],  "extrinsicValue": [    0.37, 0.25, 0.4, 0.37, 0.4, 0.15, 0.4, 0.55, 0.45, 0.62, 0.42, 0.55, 0.42, 0.77, 0.75, 0.57, 0.75, 0.8, 1.17, 0.8, 1.05, 1.65, 2.5, 4.07, 1.79, 0.58, 0.18, 0.08, 0.04, 0.03, 0.03, 0.01, 0.02, 0.09, 0.05, 0.09, 0.01, 0.08, 0.01, 0.08, 0.03, 0.23, 0.26, 0.51, 0.01, 0.01, 0.01, 0.01, 0.01, 0.03, 0.01, 0.08, 0.08, 0.01, 0.01, 0.01, 0.03, 0.07, 0.07, 0.04, 0.07, 0.08, 0.11, 0.16, 0.23, 0.33, 0.53, 0.94, 1.76, 3.33, 1.1, 0.33, 0.08, 0.65, 0.08, 0.13, 0.05, 0, 0.13, 0.05, 0.02, 0.02, 0.05, 0.12, 0.09, 0.25, 0.53, 0.03, 0.07, 0.08, 0.19, 0.05  ],  "underlyingPrice": [    175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13, 175.13  ],  "iv": [    1.629, 1.923, 1.829, 1.696, 1.176, 1.455, 1.023, 0.978, 0.929, 0.795, 0.757, 0.676, 0.636, 0.592, 0.546, 0.422, 0.393, 0.361, 0.331, 0.282, 0.257, 0.231, 0.21, 0.192, 0.176, 0.167, 0.171, 0.184, 0.2, 0.224, 0.254, 0.268, 0.296, 0.322, 0.347, 0.36, 0.384, 0.407, 0.429, 0.451, 0.472, 0.492, 0.512, 0.551, 0.589, 0.624, 1.268, 1.177, 1.093, 1.014, 0.942, 0.872, 0.807, 0.745, 0.708, 0.651, 0.628, 0.573, 0.539, 0.501, 0.469, 0.431, 0.395, 0.359, 0.325, 0.291, 0.26, 0.233, 0.212, 0.194, 0.177, 0.164, 0.223, 0.274, 0.322, 0.396, 0.432, 0.452, 0.476, 0.53, 0.66, 0.677, 0.661, 0.769, 0.776, 0.73, 0.873, 0.863, 0.974, 1.063, 1.013, 1.092  ],  "delta": [    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.998, 0.99, 0.971, 0.927, 0.849, 0.728, 0.549, 0.328, 0.147, 0.052, 0.014, 0.003, 0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.002, -0.01, -0.029, -0.073, -0.151, -0.272, -0.451, -0.672, -0.853, -0.948, -0.986, -0.997, -0.999, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1  ],  "gamma": [    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.001, 0.002, 0.006, 0.012, 0.021, 0.032, 0.043, 0.042, 0.028, 0.013, 0.004, 0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.001, 0.002, 0.006, 0.012, 0.021, 0.032, 0.043, 0.042, 0.028, 0.013, 0.004, 0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ],  "theta": [    -0.009, -0.009, -0.01, -0.011, -0.012, -0.012, -0.013, -0.014, -0.014, -0.015, -0.016, -0.017, -0.017, -0.018, -0.019, -0.02, -0.021, -0.023, -0.027, -0.036, -0.05, -0.067, -0.08, -0.08, -0.064, -0.038, -0.017, -0.006, -0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.009, -0.009, -0.01, -0.011, -0.012, -0.012, -0.013, -0.014, -0.014, -0.015, -0.016, -0.017, -0.017, -0.018, -0.019, -0.02, -0.021, -0.023, -0.027, -0.036, -0.05, -0.067, -0.08, -0.08, -0.064, -0.038, -0.017, -0.006, -0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ],  "vega": [    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.001, 0.003, 0.012, 0.035, 0.068, 0.113, 0.158, 0.192, 0.177, 0.114, 0.051, 0.016, 0.005, 0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.001, 0.003, 0.012, 0.035, 0.068, 0.113, 0.158, 0.192, 0.177, 0.114, 0.051, 0.016, 0.005, 0.001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ]}
```

## Request Parameters ​

- Required
- Optional
- Expiration Filters
- Strike Filters
- Price/Liquidity Filters
- Other Filters

- underlyingSymbol string
The underlying ticker symbol for the options chain you wish to lookup.

- date date
Use to lookup a historical end of day options chain from a specific trading day. If no date parameter is specified the chain will be the most current chain available during market hours. When the market is closed the chain will be from the previous session. Accepted date inputs: ISO 8601 , unix , spreadsheet .

- expiration date

caution Combining the all parameter with large options chains such as SPX, SPY, QQQ, etc. can cause you to consume your requests very quickly. The full SPX option chain has more than 20,000 contracts. A request is consumed for each contact you request with a price in the option chain.
  - Limits the option chain to a specific expiration date. Accepted date inputs: ISO 8601, unix, spreadsheet.
  - If omitted the next monthly expiration for real-time quotes or the next monthly expiration relative to the date parameter for historical quotes will be returned.
  - Use the keyword all to return the complete option chain.
- dte number
Days to expiry. Limit the option chain to a single expiration date closest to the dte provided. Should not be used together with from and to . Take care before combining with weekly , monthly , quarterly , since that will limit the expirations dte can return. If you are using the date parameter, dte is relative to the date provided.
- from date
Limit the option chain to expiration dates after from (inclusive). Should be combined with to to create a range. Accepted date inputs: ISO 8601 , unix , spreadsheet . If omitted all expirations will be returned.
- to date
Limit the option chain to expiration dates before to (inclusive). Should be combined with from to create a range. Accepted date inputs: ISO 8601 , unix , spreadsheet . If omitted all expirations will be returned.
- month number
Limit the option chain to options that expire in a specific month ( 1-12 ).
- year number
Limit the option chain to options that expire in a specific year .
- weekly boolean
Limit the option chain to weekly expirations by setting weekly to true . If set to false , no weekly expirations will be returned.
- monthly boolean
Limit the option chain to standard monthly expirations by setting monthly to true . If set to false , no monthly expirations will be returned.
- quarterly boolean
Limit the option chain to quarterly expirations by setting quarterly to true . If set to false , no quarterly expirations will be returned.

cautionWhen combining the `weekly`weekly, `monthly`monthly, and `quarterly`quarterly parameters, only identical boolean values will be honored. For example, `weekly=true&monthly=false`weekly=true&monthly=false will return an error. You must use these parameters to either include or exclude values, but you may not include and exclude at the same time. A valid use would be `monthly=true&quarterly=true`monthly=true&quarterly=true to return both monthly and quarterly expirations.

- strike string
  - Limit the option chain to options with the specific strike specified. (e.g. 400)
  - Limit the option chain to a specific set of strikes (e.g. 400,405)
  - Limit the option chain to an open interval of strikes using a logical expression (e.g. >400)
  - Limit the option chain to a closed interval of strikes by specifying both endpoints. (e.g. 400-410)
- delta number

tip Filter strikes using the absolute value of the delta. The values used will always return both sides of the chain (e.g. puts & calls). This means you must filter using side to exclude puts or calls. Delta cannot be used to filter the side of the chain, only the strikes.
  - Limit the option chain to a single strike closest to the delta provided. (e.g. .50)
  - Limit the option chain to a specific set of deltas (e.g. .60,.30)
  - Limit the option chain to an open interval of strikes using a logical expression (e.g. >.50)
  - Limit the option chain to a closed interval of strikes by specifying both endpoints. (e.g. .30-.60)
- strikeLimit number
Limit the number of total strikes returned by the option chain. For example, if a complete chain included 30 strikes and the limit was set to 10, the 20 strikes furthest from the money will be excluded from the response.
tip If strikeLimit is combined with the range or side parameter, those parameters will be applied first. In the above example, if the range were set to itm (in the money) and side set to call , all puts and out of the money calls would be first excluded by the range parameter and then strikeLimit will return a maximum of 10 in the money calls that are closest to the money.
If the side parameter has not been used but range has been specified, then strikeLimit will return the requested number of calls and puts for each side of the chain, but duplicating the number of strikes that are received.

Limit the option chain to strikes that are in the money, out of the money, at the money, or include all. If omitted all options will be returned. Valid inputs: itm , otm , all .
  - range string

- minBid number
Limit the option chain to options with a bid price greater than or equal to the number provided.
- maxBid number
Limit the option chain to options with a bid price less than or equal to the number provided.
- minAsk number
Limit the option chain to options with an ask price greater than or equal to the number provided.
- maxAsk number
Limit the option chain to options with an ask price less than or equal to the number provided.
- maxBidAskSpread number
Limit the option chain to options with a bid-ask spread less than or equal to the number provided.
- maxBidAskSpreadPct number
Limit the option chain to options with a bid-ask spread less than or equal to the percent provided (relative to the underlying). For example, a value of 0.5% would exclude all options trading with a bid-ask spread greater than $1.00 in an underlying that trades at $200.
- minOpenInterest number
Limit the option chain to options with an open interest greater than or equal to the number provided.
- minVolume number
Limit the option chain to options with a volume transacted greater than or equal to the number provided.

- nonstandard boolean
Include non-standard contracts by setting nonstandard to true . If set to false , no non-standard options expirations will be returned. If no parameter is provided, the output will default to false.
- side string
Limit the option chain to either call or put . If omitted, both sides will be returned.
- am boolean
Limit the option chain to A.M. expirations by setting am to true . If set to false , no A.M. expirations will be returned. This parameter is only applicable for index options such as SPX, NDX, etc. If no parameter is provided, both A.M. and P.M. expirations will be returned.
- pm boolean
Limit the option chain to P.M. expirations by setting pm to true . If set to false , no P.M. expirations will be returned. This parameter is only applicable for index options such as SPX, NDX, etc. If no parameter is provided, both A.M. and P.M. expirations will be returned.

cautionThe `am`am and `pm`pm parameters are only applicable for index options such as SPX, NDX, etc. If they are used for stocks or ETFs, a bad parameters error will be returned.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Status will always be ok when there is the quote requested.
- optionSymbol array[string]
The option symbol according to OCC symbology.
- underlying array[string]
The ticker symbol of the underlying security.
- expiration array[number]
The option's expiration date in Unix time.
- side array[string]
The response will be call or put .
- strike array[number]
The exercise price of the option.
- firstTraded array[date]
The date the option was first traded.
- dte array[number]
The number of days until the option expires.
- ask array[number]
The ask price.
- askSize array[number]
The number of contracts offered at the ask price.
- bid array[number]
The bid price.
- bidSize array[number]
The number of contracts offered at the bid price.
- mid array[number]
The midpoint price between the ask and the bid, also known as the mark price.
- last array[number]
The last price negotiated for this option contract at the time of this quote.
- volume array[number]
The number of contracts negotiated during the trading day at the time of this quote.
- openInterest array[number]
The total number of contracts that have not yet been settled at the time of this quote.
- underlyingPrice array[number]
The last price of the underlying security at the time of this quote.
- inTheMoney array[booleans]
Specifies whether the option contract was in the money true or false at the time of this quote.
- intrinsicValue array[number]
The intrinsic value of the option.
- extrinsicValue array[number]
The extrinsic value of the option.
- updated array[number]
The date and time of this quote snapshot in Unix time.
- iv array[number]
The implied volatility of the option.
- delta array[number]
The delta of the option.
- gamma array[number]
The gamma of the option.
- theta array[number]
The theta of the option.
- vega array[number]
The vega of the option.

- s string
Status will be no_data if no candles are found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.
- prevTime number optional
Unix time of the previous quote if there is no data in the requested period, but there is data in a previous period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

## Option Chain Endpoint Pricing ​

The cost of using the option chain API endpoint depends on the type of data feed you choose and your usage pattern. Here's a breakdown of the pricing:

| Data Feed Type | Cost Basis | Credits Required per Unit |
| --- | --- | --- |
| Real-Time Feed | Per option symbol | 1 credit |
| Cached Feed | Per API call | 1 credit |

### Examples ​

1. Real-Time Feed Usage
  - If you query all strikes and all expirations for SPX (which has 22,718 total option contracts) using the Real-Time Feed, it will cost you 22,718 credits.
2. Cached Feed Usage
  - A single API call to SPX using the Cached Feed, regardless of the number of option symbols queried, will cost you 1 credit.

Edit this pagePreviousStrikesNextQuotes- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes
- Option Chain Endpoint Pricing
  - Examples

---

# Expirations
<a id="expirations"></a>

<sub>Source: https://www.marketdata.app/docs/api/options/expirations</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options
- Expirations

On this pageExpirationsGet a list of current or historical option expiration dates for an underlying symbol. If no optional parameters are used, the endpoint returns all expiration dates in the option chain.

## Endpoint ​

```text
https://api.marketdata.app/v1/options/expirations/{underlyingSymbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/options/expirations/AAPL](https://api.marketdata.app/v1/options/expirations/AAPL)https://api.marketdata.app/v1/options/expirations/AAPL

app.js```js
fetch("https://api.marketdata.app/v1/options/expirations/AAPL")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/options/expirations/AAPL"response = requests.request("GET", url)print(response.text)
```

optionExpirations.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleOptionsExpirationsRequest() {	expirations, err := OptionsExpirations().UnderlyingSymbol("AAPL").Get()	if err != nil {		fmt.Print(err)		return	}	for _, expiration := range expirations {		fmt.Println(expiration)	}}
```

## Response Example ​

```json
{  "s": "ok",  "expirations": [    "2022-09-23",    "2022-09-30",    "2022-10-07",    "2022-10-14",    "2022-10-21",    "2022-10-28",    "2022-11-18",    "2022-12-16",    "2023-01-20",    "2023-02-17",    "2023-03-17",    "2023-04-21",    "2023-06-16",    "2023-07-21",    "2023-09-15",    "2024-01-19",    "2024-06-21",    "2025-01-17"  ],  "updated": 1663704000}
```

## Request Parameters ​

- Required
- Optional

- underlyingSymbol string
The underlying ticker symbol for the options chain you wish to lookup.

- strike number
Limit the lookup of expiration dates to the strike provided. This will cause the endpoint to only return expiration dates that include this strike.
- date date
Use to lookup a historical list of expiration dates from a specific previous trading day. If date is omitted the expiration dates will be from the current trading day during market hours or from the last trading day when the market is closed. Accepted date inputs: ISO 8601 , unix , spreadsheet .

## Response Attributes ​

- Success
- No Data
- Error

- s string
Status will always be ok when there is strike
data for the underlying/expirations requested.
- expirations array[date]
The expiration dates requested for the underlying with the option strikes for each expiration.
- updated date
The date and time of this list of options strikes was updated in Unix time. For historical strikes, this number should match the date parameter.

- s string
Status will be no_data if no data is found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.
- prevTime number optional
Unix time of the previous quote if there is no data in the requested period, but there is data in a previous period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousOptionsNextLookup- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Lookup
<a id="lookup"></a>

<sub>Source: https://www.marketdata.app/docs/api/options/lookup</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options
- Lookup

On this pageLookupGenerate a properly formatted OCC option symbol based on the user's human-readable description of an option. This endpoint converts text such as "AAPL 7/28/23 $200 Call" to OCC option symbol format: AAPL230728C00200000. The user input must be URL-encoded.

## Endpoint ​

```text
https://api.marketdata.app/v1/options/lookup/{userInput}
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/options/lookup/AAPL%207/28/2023%20200%20Call](https://api.marketdata.app/v1/options/lookup/AAPL%207/28/2023%20200%20Call)https://api.marketdata.app/v1/options/lookup/AAPL%207/28/2023%20200%20Call

app.js```js
fetch(  "https://api.marketdata.app/v1/options/lookup/AAPL%207/28/2023%20200%20Call")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/options/lookup/AAPL%207/28/2023%20200%20Call"response = requests.request("GET", url)print(response.text)
```

optionLookup.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleOptionLookupRequest() {	optionSymbol, err := OptionLookup().UserInput("AAPL 7/28/2023 200 Call").Get()	if err != nil {		fmt.Print(err)		return	}	fmt.Println(optionSymbol)}
```

## Response Example ​

```json
{  "s": "ok",  "optionSymbol": "AAPL230728C00200000"}
```

## Request Parameters ​

- Required

- userInput string
The human-readable string input that contains (1) stock symbol (2) strike (3) expiration date (4) option side (i.e. put or call). This endpoint will translate the user's input into a valid OCC option symbol.

## Response Attributes ​

- Success
- Error

- s string
Status will always be ok when the OCC option symbol is successfully generated.
- optionSymbol string
The generated OCC option symbol based on the user's input.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

## Notes ​

- This endpoint will return an error if the option symbol that would be formed by the user's input does not exist.

Edit this pagePreviousExpirationsNextStrikes- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes
- Notes

---

# QuotesHigh Usage
<a id="quoteshigh-usage"></a>

<sub>Source: https://www.marketdata.app/docs/api/options/quotes</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options
- Quotes

On this pageQuotesHigh UsageGet a current or historical end of day quote for a single options contract.

## Endpoint ​

```text
https://api.marketdata.app/v1/options/quotes/{optionSymbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/options/quotes/AAPL271217C00250000/](https://api.marketdata.app/v1/options/quotes/AAPL271217C00250000/)https://api.marketdata.app/v1/options/quotes/AAPL271217C00250000/

app.js```js
fetch("https://api.marketdata.app/v1/options/quotes/AAPL271217C00250000/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/options/quotes/AAPL271217C00250000/"response = requests.request("GET", url)print(response.text)
```

optionQuotes.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleOptionQuoteRequest() {	quotes, err := OptionQuote().OptionSymbol("AAPL271217C00250000").Get()	if err != nil {		fmt.Print(err)		return	}	for _, quote := range quotes {		fmt.Println(quote)	}}
```

## Response Example ​

```json
{  "s": "ok",  "optionSymbol": ["AAPL271217C00250000"],  "ask": [5.25],  "askSize": [57],  "bid": [5.15],  "bidSize": [994],  "mid": [5.2],  "last": [5.25],  "volume": [977],  "openInterest": [61289],  "underlyingPrice": [136.12],  "inTheMoney": [false],  "updated": [1665673292],  "iv": [0.3468],  "delta": [0.347],  "gamma": [0.015],  "theta": [-0.05],  "vega": [0.264],  "intrinsicValue": [13.88],  "extrinsicValue": [8.68]}
```

## Request Parameters ​

- Required
- Optional

- optionSymbol string
The option symbol (as defined by the OCC) for the option you wish to lookup. Use the current OCC option symbol format, even for historic options that quoted before the format change in 2010.

- date date
Use to lookup a historical end of day quote from a specific trading day. If no date is specified the quote will be the most current price available during market hours. When the market is closed the quote will be from the last trading day. Accepted date inputs: ISO 8601 , unix , spreadsheet .
- from date
Use to lookup a series of end of day quotes. From is the oldest (leftmost) date to return (inclusive). If from/to is not specified the quote will be the most current price available during market hours. When the market is closed the quote will be from the last trading day. Accepted date inputs: ISO 8601 , unix , spreadsheet .
- to date
Use to lookup a series of end of day quotes. From is the newest (rightmost) date to return (exclusive). If from/to is not specified the quote will be the most current price available during market hours. When the market is closed the quote will be from the last trading day. Accepted date inputs: ISO 8601 , unix , spreadsheet .

## Response Attributes ​

- Success
- No Data
- Error

- s string
Status will always be ok when there is data for the quote requested.
- optionSymbol array[string]
The option symbol according to OCC symbology.
- ask array[number]
The ask price.
- askSize array[number]
The number of contracts offered at the ask price.
- bid array[number]
The bid price.
- bidSize array[number]
The number of contracts offered at the bid price.
- mid array[number]
The midpoint price between the ask and the bid, also known as the mark price.
- last array[number]
The last price negotiated for this option contract at the time of this quote.
- volume array[number]
The number of contracts negotiated during the trading day at the time of this quote.
- openInterest array[number]
The total number of contracts that have not yet been settled at the time of this quote.
- underlyingPrice array[number]
The last price of the underlying security at the time of this quote.
- inTheMoney array[booleans]
Specifies whether the option contract was in the money true or false at the time of this quote.
- intrinsicValue array[number]
The instrinisc value of the option.
- extrnisicValue array[number]
The extrinsic value of the option.
- updated array[number]
The date and time of this quote snapshot in Unix time.
- iv array[number]
The implied volatility of the option.
- delta array[number]
The delta of the option.
- gamma array[number]
The gamma of the option.
- theta array[number]
The theta of the option.
- vega array[number]
The vega of the option.

- s string
Status will be no_data if no candles are found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.
- prevTime number optional
Unix time of the previous quote if there is no data in the requested period, but there is data in a previous period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Tags:- API: High Usage

Edit this pagePreviousOption ChainNextMutual Funds- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Strikes
<a id="strikes"></a>

<sub>Source: https://www.marketdata.app/docs/api/options/strikes</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
  - Expirations
  - Lookup
  - Strikes
  - Option Chain
  - Quotes High Usage
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Options
- Strikes

On this pageStrikesGet a list of current or historical options strikes for an underlying symbol. If no optional parameters are used, the endpoint returns the strikes for every expiration in the chain.

## Endpoint ​

```text
https://api.marketdata.app/options/strikes/{underlyingSymbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/options/strikes/AAPL/?date=2023-01-03&expiration=2023-01-20](https://api.marketdata.app/v1/options/strikes/AAPL/?date=2023-01-03&expiration=2023-01-20)https://api.marketdata.app/v1/options/strikes/AAPL/?date=2023-01-03&expiration=2023-01-20

app.js```js
fetch(  "https://api.marketdata.app/v1/options/strikes/AAPL/?date=2023-01-03&expiration=2023-01-20")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/options/strikes/AAPL/?date=2023-01-03&expiration=2023-01-20"response = requests.request("GET", url)print(response.text)
```

optionStrikes.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleOptionsStrikesRequest() {	expirations, err := OptionsStrikes().UnderlyingSymbol("AAPL").Date("2023-01-03").Expiration("2023-01-20").Get()	if err != nil {		fmt.Print(err)		return	}	for _, expiration := range expirations {		fmt.Println(expiration)	}}
```

## Response Example ​

```json
{  "s": "ok",  "updated": 1663704000,  "2023-01-20": [    30.0, 35.0, 40.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0,    95.0, 100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0,    150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0, 200.0,    205.0, 210.0, 215.0, 220.0, 225.0, 230.0, 235.0, 240.0, 245.0, 250.0, 260.0,    270.0, 280.0, 290.0, 300.0  ]}
```

## Request Parameters ​

- Required
- Optional

- underlyingSymbol string
The underlying ticker symbol for the options chain you wish to lookup.

- expiration date
Limit the lookup of strikes to options that expire on a specific expiration date. Accepted date inputs: ISO 8601 , unix , spreadsheet .
- date date
  - Use to lookup a historical list of strikes from a specific previous trading day.
  - If date is omitted the expiration dates will be from the current trading day during market hours or from the last trading day when the market is closed.
  - Accepted date inputs: ISO 8601, unix, spreadsheet.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Status will always be ok when there is strike
data for the underlying/expirations requested.
- dates array[number]
The expiration dates requested for the underlying with the option strikes for each expiration.
- updated array[number]
The date and time of this list of options strikes was updated in Unix time. For historical strikes, this number should match the date parameter.

- s string
Status will be no_data if no data is found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.
- prevTime number optional
Unix time of the previous quote if there is no data in the requested period, but there is data in a previous period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousLookupNextOption Chain- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Rate Limits
<a id="rate-limits"></a>

<sub>Source: https://www.marketdata.app/docs/api/rate-limiting</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Rate Limits

On this pageRate LimitsWe enforce rate limits to ensure our API remains accessible and efficient for all users. We have two types of rate limits: API credits (total requests per unit of time) and a concurrent request limit (simultaneous requests).

## API Credits ​

Normally each API call consumes a single credit. However, if the response includes more than a single symbol, it can consume multiple credits. Often, users can navigate around a rate limit by making the most of the diverse filters we provide (e.g. instead of retrieving an entire option chain, apply specific filters to narrow down the results).

The rate limit is a hard limit. Once the limit has been reached, you will no longer be able to make requests until the request counter resets. Requests in excess of the rate limit will generate 429 responses.

### Usage Counter Reset Time ​

The usage counter for all plans with a daily limit resets at 9:30 AM Eastern Time (NYSE opening bell). This reset timing is crucial for users to understand so they can plan their API usage efficiently without hitting the rate limit unexpectedly.

Managing Timezone ChangesTo handle the reset time accurately regardless of your local timezone, it's recommended to use the `America/New_York`America/New_York timezone identifier. This ensures that your application adjusts for any changes in Eastern Time, including daylight saving shifts, automatically.

By aligning your application's timing functions with the `America/New_York`America/New_York timezone, you can ensure that your usage of the API remains within the allocated rate limits, taking into account the precise reset timing at 9:30 AM Eastern Time.

## Concurrent Request Limit ​

To maintain the stability and performance of our API, we enforce a limit of no more than 50 concurrent requests across all subscription plans. This means that at any given time, you should not have more than 50 active API calls in progress. Requests in excess of the concurrency limit will generate 429 responses.

To adhere to this limit, it is advisable to implement a worker or thread pool mechanism in your application that does not exceed 50 workers. Each worker should handle no more than one API request at a time. This setup helps in efficiently managing API calls without breaching the concurrent request limit and ensures fair usage among all users.

## Rate Limits By Plan ​

Different plans have specific rate limits, with most plans enforcing a daily rate limit while our Prime Plan uses a per minute rate limit.

|  | Free Forever | Starter | Trader | Prime |
| --- | --- | --- | --- | --- |
| Daily API Credits | 100 | 10,000 | 100,000 | No Limit |
| Per Minute API Credits | No Limit | No Limit | No Limit | 60,000 |
| Concurrent Request Limit | 50 | 50 | 50 | 50 |

#### Summary ​

- Free Forever Plan: 100 credits per day.
- Starter Plan: 10,000 credits per day.
- Trader Plan: 100,000 credits per day.
- Prime Plan: 60,000 credits per minute.

## Credits ​

Each time you make a request to the API, the system will increase your credits counter. Normally each successful response will increase your counter by 1 and each call to our API will be counted as a single credit. However, if you request multiple symbols in a single API call using the bulkquotes, the bulkcandles, or the option chain endpoint, a request will be used for each symbol that is included in the response.

cautionFor users working with options, take care before repeatedly requesting quotes for an entire option chain. Each option symbol included in the response will consume a request. If you were to download the entire SPX option chain (which has 20,000+ option symbols), you would exhaust your request limit very quickly. Use our extensive option chain filtering parameters to request only the strikes/expirations you need.

## Headers to Manage the Rate Limit ​

We provide the following headers in our responses to help you manage the rate limit and throttle your applications when necessary:

- X-Api-Ratelimit-Limit: The maximum number of requests you're permitted to make (per day for Free/Starter/Trader plans or per minute for Prime users).
- X-Api-Ratelimit-Remaining: The number of requests remaining in the current rate day/period.
- X-Api-Ratelimit-Reset: The time at which the current rate limit window resets in UTC epoch seconds.
- X-Api-Ratelimit-Consumed: The quantity of requests that were consumed in the current request.

## Detailed Rate Limit Rules ​

- Each successful response increases the counter by a minimum of 1 request.
- Only status 200/203 responses consume requests.
- NULL responses are not counted.
- Error responses are not counted.
- Requests consume more than 1 credit if the response includes prices for more than 1 symbol (i.e. options/chain or stocks/bulkquotes endpoints).
- Responses that include more than one symbol, but do not include the bid, ask, mid, or last columns do not consume multiple credits and are counted as a single request.
- Certain free trial symbols like AAPL stock, AAPL options, the VIX index, and the VFINX mutual fund do not consume requests.

## Strategies To Avoid Rate Limiting ​

- Exclude the bid, ask, mid, and last columns from your option chain requests if the current price is not needed.
- Use the extensive option chain filters such as strikeLimit to exclude unnecessary strikes from your requests.
- Paying customers can make use of the reduced-price cached feed. Use the feed=cached parameter on the stocks/bulkquotes and options/chain endpoints to retrieve previously cached quotes instead of making a live request. This can save thousands of credits. For more details, refer to the feed parameter documentation.

Edit this pagePreviousAuthenticationNextDates and Times- API Credits
  - Usage Counter Reset Time
- Concurrent Request Limit
- Rate Limits By Plan
- Credits
- Headers to Manage the Rate Limit
- Detailed Rate Limit Rules
- Strategies To Avoid Rate Limiting

---

# SDKs
<a id="sdks"></a>

<sub>Source: https://www.marketdata.app/docs/api/sdk</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- SDKs

On this pageSDKs## Official Market Data SDKs ​

We offer SDKs for various programming languages and platforms to cater to a wide range of developers and applications:

[](/docs/sdk/postman)

### Postman Collection ​

[Comprehensive Postman Collection for easy API integration and testing.](/docs/sdk/postman)Comprehensive Postman Collection for easy API integration and testing.



### Python SDK ​

In development. Perfect for data analysis, backend services, and automation scripts.

[](/docs/sdk/php)

### PHP SDK ​

[Market Data integration for web applications and server-side processing.](/docs/sdk/php)Market Data integration for web applications and server-side processing.

[](/docs/sdk/go)

### Go SDK ​

[High performance Market Data SDK integration for enterprise-level backend systems.](/docs/sdk/go)High performance Market Data SDK integration for enterprise-level backend systems.

Each SDK is designed with simplicity in mind, ensuring you can get up and running with minimal setup.

## Unofficial Client Libraries ​

We encourage our users to open source their implementations of our API in the languages of their choice and we will link to those implementations on this page. Please let us know if you have developed a Market Data client library and we will be happy to add a link to it.

### Python ​

- guruappa/MarketDataApp
- marts01/market_data

### Ruby ​

- sebastialonso/market-data

Edit this pagePreviousIntroductionNextAuthentication- Official Market Data SDKs
  - Postman Collection
  - Python SDK
  - PHP SDK
  - Go SDK
- Unofficial Client Libraries
  - Python
  - Ruby

---

# Stocks
<a id="stocks"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks

On this pageStocksStock endpoints include numerous fundamental, technical, and pricing data.

## Root Endpoint For Stocks ​

```text
https://api.marketdata.app/v1/stocks/
```

## Stocks Endpoints ​

## 📄️ Real-Time Prices

This endpoint is currently in open beta. It is available to all users (including free trial users) during our open beta test. We welcome your feedback.

## 📄️ Delayed Quotes

Retrieve the most recent available quote for a stock, based on the user's entitlements. This may include a 15-minute delayed quote or an end-of-day quote, depending on the plan or access level.

## 📄️ Historical Candles

Get historical price candles for a stock.

## 📄️ Earnings

Get historical earnings per share data or a future earnings calendar for a stock.

## 📄️ News

The News endpoint is still in beta and has not yet been optimized for performance. Use caution before adding this endpoint in a prodution environment.

## 📄️ Bulk Historical Candles

Get bulk historical candle data for stocks. This endpoint returns bulk daily candle data for multiple stocks. Unlike the standard candles endpoint, this endpoint returns a single daily for each symbol provided.

Edit this pagePreviousStatusNextReal-Time Prices- Root Endpoint For Stocks
- Stocks Endpoints

---

# Bulk Historical Candles
<a id="bulk-historical-candles"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/bulkcandles</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- Bulk Historical Candles

On this pageBulk Historical CandlesGet bulk historical candle data for stocks. This endpoint returns bulk daily candle data for multiple stocks. Unlike the standard candles endpoint, this endpoint returns a single daily for each symbol provided.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/bulkcandles/{resolution}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/stocks/bulkcandles/D/?symbols=AAPL,META,MSFT](https://api.marketdata.app/v1/stocks/bulkcandles/D/?symbols=AAPL,META,MSFT)https://api.marketdata.app/v1/stocks/bulkcandles/D/?symbols=AAPL,META,MSFT

app.js```js
fetch(  "https://api.marketdata.app/v1/stocks/bulkcandles/D/?symbols=AAPL,META,MSFT")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/bulkcandles/D/?symbols=AAPL,META,MSFT"response = requests.request("GET", url)print(response.text)
```

bulkStockCandles.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleBulkStockCandlesRequest_get() {	symbols := []string{"AAPL", "META", "MSFT"}	candles, err := BulkStockCandles().Resolution("D").Symbols(symbols).Get()	if err != nil {		fmt.Print(err)		return	}  	for _, candle := range candles {		fmt.Println(candle)	}}
```

## Response Example ​

```json
{  "s": "ok",  "symbol": ["AAPL", "META", "MSFT"],  "o": [196.16, 345.58, 371.49],  "h": [196.95, 353.6, 373.26],  "l": [195.89, 345.12, 369.84],  "c": [196.94, 350.36, 373.26],  "v": [40714051, 17729362, 20593658],  "t": [1703048400,1703048400,1703048400]}
```

## Request Parameters ​

- Required
- Optional

- resolution string The duration of each candle. Only daily candles are supported at this time.
  - Daily Resolutions: (daily, D, 1D)
- symbols string The ticker symbols to return in the response, separated by commas. The symbols parameter may be omitted if the snapshot parameter is set to true .

- snapshot boolean Returns candles for all available symbols for the date indicated. The symbols parameter can be omitted if snapshot is set to true.
- date date The date of the candles to be returned. If no date is specified, during market hours the candles returned will be from the current session. If the market is closed the candles will be from the most recent session. Accepted date inputs: ISO 8601 , unix , spreadsheet .
- adjustsplits boolean Adjust historical data for for historical splits and reverse splits. Market Data uses the CRSP methodology for adjustment.
Daily candles default: true .

## Response Attributes ​

- Success
- No Data
- Error

- s string
Will always be ok when there is data for the candles requested.
- symbol string
The ticker symbol of the stock.
- o array[number]
Open price.
- h array[number]
High price.
- l array[number]
Low price.
- c array[number]
Close price.
- v array[number]
Volume.
- t array[number]
Candle time (Unix timestamp, Exchange Timezone). Daily candles are returned at 00:00:00 without times.

- s string
Status will be no_data if no candles are found for the request.

- s string
Status will be error if the request produces an error response.
- errmsg string
An error message.

## Notes ​

- The stocks/bulkcandles endpoint will consume one API credit for each symbol returned in the response.

Edit this pagePreviousNewsNextOptions- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes
- Notes

---

# Market Data
<a id="market-data"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/bulkquotes</sub>

![Market Data API](/docs/assets/images/api-317517116562041b09c86cf0e3520133.png)

![Market Data API](/docs/assets/images/api-darkmode-6092517f7e40a826ad7093382c120410.png)

### Market Data API

A complete reference of all Market Data API endpoints, authentication, and universal parameters.

![Google Sheets Add-On](data:image/png;base64,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ACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAAChQL/cAGLabD9wVX777ptwzVszPbNgeF2zYNtCvecP+vfGN/XsG+jXr7CVbnh07prfmngFDJQBove/cf3v8/rf/OPeMFXPl+a8eeAB87Z6b4+ob/3SgX7POpkZWCQBazyMAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAAChQL/cAGLZXnvX8eM4ZZ+eesWI2jq8d+Ne8ZPuF8bIzzx/4162rM1evyz0Bhk4A0HrToxMxPTqRe0ajbRyfio3jU7lnAAPkEQAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFEgAAECBBAAAFKiXewAM29fuuTk+tucruWesmF84+4J41dkXDPRrfmbfDfHpfTcM9GvW2SXbL4wXbd6RewYMlQCg9e489KP4TEEvXudOPSVeNeCveetDdxf1PfTiTwk8AgCAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAgkAACiQAACAAvVyD4BhO2N0Ip5zxlNzz1gxG8enhvI1S/oenjE6kXsCDJ0AoPVecdbz4xVnPT/3jEa7ZPuFccn2C3PPAAbIIwAAKJAAAIACCQAAKJAAAIACCQAAKJAAAIACCQAAKJAAAIACCQAAKJAAoFaOz87kngBD4WebuhEA1Mr+IwdzT4Ch2H/kodwT4BQCgFq589D+3BNgKPb52aZmBAC1csfD98VtB+/NPQMG6sHjh+Ob+/fmngGnEADUznU/uD73BBioT//ghjhZzeaeAacQANTOB7/3+fjRUWcBaIejJ0/EH9706dwz4HEEALVz+MTR+N1vfDyqqHJPgWV757c+Ffc8ciD3DHgcAUAtfXrfN+LdN16XewYsy65bvxQfueXPc8+AJyQAqK2rb7wufuv6j8YJfz9Nw1RRxfu++9m46q+uzT0FnlQv9wCYz8f3fCW+cd+t8Rs/9Y/iVWdfkHsOnNY3f7Q33vmtT8UNTv1TcwKA2tt78J7451+9JrauXhcv3/q8eM4ZZ8emVWtjTX889zSIIzPH44ePPBC3PPg38X/u+rY/Y6UxBACNcdfh++O/ff8LuWcAtIIzAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAABQIAEAAAUSAPObzT0AgCXzO3weAmB+j+QeAMCSHc49oM4EwHyqOJR7AgBL9nDuAXUmAOaT4mDuCQAsmQCYhwCYV7or9wIAliZFtS/3hjoTAPNIUX0/9wYAlqaK5Hf4PATAPGYFAECT+R0+DwEwj250vpV7AwBLVPkdPh8BMI+R/gNfr/wZCUDjVBGHx0bu/6vcO+pMAMzjpos/eTxF/GXuHQAsTor48k0Xf/J47h11JgBOI6X0mdwbAFicKqrP5t5QdwLgNE6crK6NiJO5dwCwYDOz/f7Hc4+oOwFwGj+4/Jq7I9Lnc+8AYKGqz91x8R/ek3tF3QmABajS7PtzbwBggar4QO4JTSAAFuC2W878k4i4KfcOAE6jipv37jnzf+Se0QQCYCGuumo2qvj93DMAmF+Vqv8QV13lGuAFEAALdNaZT9kV3gUAqLO/vq3/4Mdyj2gKAbBAX3zpVTOzs7NviYgq9xYAHqdKqboyLv6kv9paIAGwCLdf/oGvVFXsyr0DgMdKf7Tn0vd/KfeKJhEAizSTuldGxB25dwDwqH3H+jP/MveIphEAi7TvsvccmI3OP4kIHzEJkN+JlNIld138wQdyD2kaAbAEt1/23usjpbfn3gFQuiriX+y59H3ubFmCbu4BTXXgUzdcv+6Xfno8Ir049xaAMlXvuO2y9/9e7hVNlXIPaLQq0vZrd36gquINuacAFOYDey+9Zmckf5m1VB4BLEeKas+vXPPGiPSu3FMACnL13lufcoUX/+XxDsCAbN+1899UEe8I31OAYamiin+997XXeNt/ALxYDdD23Ve8uqqqD0XEutxbAFrm/qoT//S2X7nmf+Ue0hYCYMCe/uGdZ6dutTsivSj3FoA2qCK+3KlmL9vz2g/clXtLmwiAYagibdt9xeUR1bsiYkPuOQBNlCIemI3qd2+79cx3u+Bn8ATAED1j9871J2er346U3hgR47n3ADTEIynFNUd7J/+9D/gZHgGwAp62+42bOtF5W1SxMyLW5t4DUFMHUhXvq2Y7/2nv6957X+4xbScAVtA5H/rVsd7IyKtnIy5PEa+MiJHcmwAyOxZR/e8qxUc6a8eu2/ML7z6We1ApBEAmP/Xhy1c/0hl/UaTqZbORXpgidoTzAkD77a8ibu5U8RcnO+nPjj1cfe2HV1zzSO5RJRIANbL1E792xvjJ7rkzVZrsVtXa2ZQmUhX93LsAlqJKcaJTVYdmozpQRffgyUi37rvsPQdy72LO/we8shVmg9G/yAAAAABJRU5ErkJggg==)

![Google Sheets Add-On](data:image/png;base64,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)

### Google Sheets Add-On

Learn how to use each Market Data formula in our Add-On with practical examples.

![Accounts & Billing](/docs/assets/images/billing-61eb1643aa2006525a5b9eb08d7cbdb3.png)

![Accounts & Billing](/docs/assets/images/billing-darkmode-250914bc70fba2e26703fd5c10727be8.png)

### Accounts & Billing

Frequently asked questions about your account, our billing rules, and administrative information.

---

# Historical Candles
<a id="historical-candles"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/candles</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- Historical Candles

On this pageHistorical CandlesGet historical price candles for a stock.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/candles/{resolution}/{symbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/stocks/candles/D/AAPL?from=2020-01-01&to=2020-12-31](https://api.marketdata.app/v1/stocks/candles/D/AAPL?from=2020-01-01&to=2020-12-31)https://api.marketdata.app/v1/stocks/candles/D/AAPL?from=2020-01-01&to=2020-12-31

app.js```js
fetch(  "https://api.marketdata.app/v1/stocks/candles/D/AAPL?from=2020-01-01&to=2020-12-31")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/candles/D/AAPL?from=2020-01-01&to=2020-12-31"response = requests.request("GET", url)print(response.text)
```

stockCandles.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleStockCandlesRequest() {	candles, err := StockCandles().Resolution("D").Symbol("AAPL").From("2020-01-01").To("2020-12-31").Get()	if err != nil {		fmt.Print(err)		return	}	for _, candle := range candles {		fmt.Println(candle)	}}
```

## Response Example ​

```json
{  "s": "ok",  "c": [217.68, 221.03, 219.89],  "h": [222.49, 221.5, 220.94],  "l": [217.19, 217.1402, 218.83],  "o": [221.03, 218.55, 220],  "t": [1569297600, 1569384000, 1569470400],  "v": [33463820, 24018876, 20730608]}
```

## Request Parameters ​

- Required
- Dates
- Optional

- resolution string
The duration of each candle.
  - Minutely Resolutions: (minutely, 1, 3, 5, 15, 30, 45, ...)
  - Hourly Resolutions: (hourly, H, 1H, 2H, ...)
  - Daily Resolutions: (daily, D, 1D, 2D, ...)
  - Weekly Resolutions: (weekly, W, 1W, 2W, ...)
  - Monthly Resolutions: (monthly, M, 1M, 2M, ...)
  - Yearly Resolutions:(yearly, Y, 1Y, 2Y, ...)
- symbol string
The company's ticker symbol.

All `date`date parameters are optional. By default the most recent candle is returned if no date parameters are provided.

- from date
The leftmost candle on a chart (inclusive). From and countback are mutually exclusive. If you use countback , from must be omitted. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- to date
The rightmost candle on a chart (inclusive). Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- countback number
Will fetch a specific number of candles before (to the left of) to . From and countback are mutually exclusive. If you use from , countback must be omitted.

noteThere is no maximum date range limit on daily candles. When requesting intraday candles of any resolution, no more than 1 year of data can be requested in a single request.

- extended boolean
Include extended hours trading sessions when returning intraday candles. Daily resolutions never return extended hours candles.
  - Daily candles default: false.
  - Intraday candles default: false.
- adjustsplits boolean
Adjust historical data for stock splits. Market Data uses the CRSP methodology for adjustment.
  - Daily candles default: true.
  - Intraday candles default: false.

## Response Attributes ​

- Success
- No Data
- Error

- s string
ll always be ok when there is data for the candles requested.
- o array[number]
Open price.
- h array[number]
High price.
- l array[number]
Low price.
- c array[number]
Close price.
- v array[number]
Volume.
- t array[number] Candle time (Unix timestamp, UTC). Daily, weekly, monthly, yearly candles are returned without times.

- s string
Status will be no_data if no candles are found for the request.
- nextTime number optional
Unix time of the next quote if there is no data in the requested period, but there is data in a subsequent period.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousDelayed QuotesNextEarnings- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# EarningsPremium
<a id="earningspremium"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/earnings</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- Earnings

On this pageEarningsPremiumGet historical earnings per share data or a future earnings calendar for a stock.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/earnings/{symbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/stocks/earnings/AAPL/](https://api.marketdata.app/v1/stocks/earnings/AAPL/)https://api.marketdata.app/v1/stocks/earnings/AAPL/

app.js```js
fetch("https://api.marketdata.app/v1/stocks/earnings/AAPL/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/earnings/AAPL/"response = requests.request("GET", url)print(response.text)
```

stockEarnings.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleStockEarningsRequest() {	earningsReports, err := StockEarnings().Symbol("AAPL").Get()	if err != nil {		fmt.Print(err)		return	}	for _, report := range earningsReports {		fmt.Println(report)	}}
```

## Response Example ​

```json
{  "s": "ok",  "symbol": ["AAPL"],  "fiscalYear": [2023],  "fiscalQuarter": [1],  "date": [1672462800],  "reportDate": [1675314000],  "reportTime": ["before market open"],  "currency": ["USD"],  "reportedEPS": [1.88],  "estimatedEPS": [1.94],  "surpriseEPS": [-0.06],  "surpriseEPSpct": [-3.0928],  "updated": [1701690000]}
```

## Request Parameters ​

- Required
- Optional

- symbol string
The company's ticker symbol.

- from date
The earliest earnings report to include in the output. If you use countback, from is not required. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- to date
The latest earnings report to include in the output. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- countback number
Countback will fetch a specific number of earnings reports before to . If you use from , countback is not required.
- date date
Retrieve a specific earnings report by date. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- report datekey
Retrieve a specific earnings report by date and quarter. Example: 2023-Q4 . This allows you to retrieve a 4th quarter value without knowing the company's specific fiscal year.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Will always be ok when there is data for the symbol requested.
- symbol array[string]
The symbol of the stock.
- fiscalYear array[number]
The fiscal year of the earnings report. This may not always align with the calendar year.
- fiscalQuarter array[number]
The fiscal quarter of the earnings report. This may not always align with the calendar quarter.
- date array[date]
The last calendar day that corresponds to this earnings report.
- reportDate array[date]
The date the earnings report was released or is projected to be released.
- reportTime array[string]
The value will be either before market open , after market close , or during market hours .
- currency array[string]
The currency of the earnings report.
- reportedEPS array[number]
The earnings per share reported by the company. Earnings reported are typically non-GAAP unless the company does not report non-GAAP earnings.
tip GAAP (Generally Accepted Accounting Principles) earnings per share (EPS) count all financial activities except for discontinued operations and major changes in accounting methods. Non-GAAP EPS, on the other hand, typically doesn't include losses or devaluation of assets, and often leaves out irregular expenses like significant restructuring costs, large tax or legal charges, especially for companies not in the financial sector.
- estimatedEPS array[number]
The average consensus estimate by Wall Street analysts.
- surpriseEPS array[number]
The difference (in earnings per share) between the estimated earnings per share and the reported earnings per share.
- surpriseEPSpct array[number]
The difference in percentage terms between the estimated EPS and the reported EPS, expressed as a decimal. For example, if the estimated EPS is 1.00 and the reported EPS is 1.20, the surpriseEPSpct would be 0.20 (or 20%).
- updated array[date]
The date/time the earnings data for this ticker was last updated.

- s string
Status will be no_data if no earnings data can be found for the symbol.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Tags:- API: Premium

Edit this pagePreviousHistorical CandlesNextNews- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# NewsBeta
<a id="newsbeta"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/news</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- News

On this pageNewsBetaBeta EndpointThe News endpoint is still in beta and has not yet been optimized for performance. Use caution before adding this endpoint in a prodution environment.

Get news for a stock.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/news/{symbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/stocks/news/AAPL/](https://api.marketdata.app/v1/stocks/news/AAPL/)https://api.marketdata.app/v1/stocks/news/AAPL/

app.js```js
fetch("https://api.marketdata.app/v1/stocks/news/AAPL/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/news/AAPL/"response = requests.request("GET", url)print(response.text)
```

stockNews.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleStockNewsRequest_get() {	news, err := StockNews().Symbol("AAPL").Get()	if err != nil {		fmt.Print(err)		return	}	for _, article := range news {		fmt.Println(article)	}}
```

## Response Example ​

```json
{  "s":"ok",  "symbol": "AAPL",  "headline": "Whoa, There! Let Apple Stock Take a Breather Before Jumping in Headfirst.",  "content": "Apple is a rock-solid company, but this doesn't mean prudent investors need to buy AAPL stock at any price.",  "source": "https://investorplace.com/2023/12/whoa-there-let-apple-stock-take-a-breather-before-jumping-in-headfirst/",  "updated": 1703041200}
```

## Request Parameters ​

- Required
- Optional

- symbol string
The company's ticker symbol.

- from date
The earliest news to include in the output. If you use countback, from is not required. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- to date
The latest news to include in the output. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.
- countback number
Countback will fetch a specific number of news before to . If you use from , countback is not required.
- date date
Retrieve news for a specific day. Accepted timestamp inputs: ISO 8601, unix, spreadsheet.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Will always be ok when there is data for the symbol requested.
- symbol array[string]
The symbol of the stock.
- headline array[string]
The headline of the news article.
- content array[string]
The content of the article, if available.
tip Please be aware that this may or may not include the full content of the news article. Additionally, it may include captions of images, copyright notices, syndication information, and other elements that may not be suitable for reproduction without additional filtering.
- source array[url]
The source URL where the news appeared.
- publicationDate array[date]
The date the news was published on the source website.

- s string
Status will be no_data if no news can be found for the symbol.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Tags:- API: Beta

Edit this pagePreviousEarningsNextBulk Historical Candles- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Real-Time PricesHigh Usage
<a id="real-time-priceshigh-usage"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/prices</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- Real-Time Prices

On this pageReal-Time PricesHigh UsagetipThis endpoint is currently in open beta. It is available to all users (including free trial users) during our open beta test. We welcome your feedback.

Get real-time midpoint prices for one or more stocks. This endpoint returns real-time prices for stocks, using the [SmartMid](https://www.marketdata.app/smart-mid/)SmartMid model.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/prices/{symbol}/
```

or

```text
https://api.marketdata.app/v1/stocks/prices/?symbols={symbol1},{symbol2},...
```

#### Method ​

```text
GET
```

## Request Examples ​

- Single Symbol
- Multiple Symbols

- HTTP
- NodeJS
- Python

GET [https://api.marketdata.app/v1/stocks/prices/AAPL/](https://api.marketdata.app/v1/stocks/prices/AAPL/)https://api.marketdata.app/v1/stocks/prices/AAPL/

app.js```js
fetch("https://api.marketdata.app/v1/stocks/prices/AAPL/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/prices/AAPL/"response = requests.request("GET", url)print(response.text)
```

- HTTP
- NodeJS
- Python

GET [https://api.marketdata.app/v1/stocks/prices/?symbols=AAPL,META,MSFT](https://api.marketdata.app/v1/stocks/prices/?symbols=AAPL,META,MSFT)https://api.marketdata.app/v1/stocks/prices/?symbols=AAPL,META,MSFT

app.js```js
fetch("https://api.marketdata.app/v1/stocks/prices/?symbols=AAPL,META,MSFT")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/prices/"params = {"symbols": "AAPL,META,MSFT"}response = requests.request("GET", url, params=params)print(response.text)
```

## Response Example ​

```json
{  "s": "ok",  "symbol": ["AAPL", "META", "MSFT"],  "mid": [149.07, 320.45, 380.12],  "updated": [1663958092, 1663958092, 1663958092]}
```

## Request Parameters ​

- Required

You can provide the symbol(s) in one of two ways:

1. As part of the URL path:
  - symbol string
The company's ticker symbol.
2. As a query parameter:
  - symbols string
Comma-separated list of ticker symbols.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Will always be ok when there is data for the symbols requested.
- symbol array[string]
Array of ticker symbols that were requested.
- mid array[number]
Array of midpoint prices, as calculated by the SmartMid model.
- updated array[date]
Array of date/times for each stock price.

- s string
Status will only be no_data if no prices can be found for all of the symbols. If a price for any symbol can be returned, the request will be successful.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Tags:- API: High Usage

Edit this pagePreviousStocksNextDelayed Quotes- Endpoint
- Request Examples
- Response Example
- Request Parameters
- Response Attributes

---

# Delayed Quotes
<a id="delayed-quotes"></a>

<sub>Source: https://www.marketdata.app/docs/api/stocks/quotes</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
  - Real-Time Prices High Usage
  - Delayed Quotes
  - Historical Candles
  - Earnings Premium
  - News Beta
  - Bulk Historical Candles
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting

- 
- Stocks
- Delayed Quotes

On this pageDelayed QuotesRetrieve the most recent available quote for a stock, based on the user's entitlements. This may include a 15-minute delayed quote or an end-of-day quote, depending on the plan or access level.

## Endpoint ​

```text
https://api.marketdata.app/v1/stocks/quotes/{symbol}/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python
- Go

GET [https://api.marketdata.app/v1/stocks/quotes/AAPL/](https://api.marketdata.app/v1/stocks/quotes/AAPL/)https://api.marketdata.app/v1/stocks/quotes/AAPL/

app.js```js
fetch("https://api.marketdata.app/v1/stocks/quotes/AAPL/")  .then((res) => {    console.log(res);  })  .catch((err) => {    console.log(err);  });
```

app.py```python
import requestsurl = "https://api.marketdata.app/v1/stocks/quotes/AAPL/"response = requests.request("GET", url)print(response.text)
```

stockQuote.go```go
import (  "fmt"  api "github.com/MarketDataApp/sdk-go")func ExampleStockQuoteRequest() {	quotes, err := StockQuote().Symbol("AAPL").Get()	if err != nil {		fmt.Print(err)		return	}	for _, quote := range quotes {		fmt.Println(quote)	}}
```

## Response Example ​

```json
{  "s": "ok",  "symbol": ["AAPL"],  "ask": [149.08],  "askSize": [200],  "bid": [149.07],  "bidSize": [600],  "mid": [149.07],  "last": [149.09],  "volume": [66959442],  "updated": [1663958092]}
```

## Request Parameters ​

- Required
- Optional

- symbol string
The company's ticker symbol.

- 52week boolean
Enable the output of 52-week high and 52-week low data in the quote output. By default this parameter is false if omitted.
- extended boolean
Control the inclusion of extended hours data in the quote output. Defaults to true if omitted.
  - When set to true, the most recent quote is always returned, without regard to whether the market is open for primary trading or extended hours trading.
  - When set to false, only quotes from the primary trading session are returned. When the market is closed or in extended hours, a historical quote from the last closing bell of the primary trading session is returned instead of an extended hours quote.

## Response Attributes ​

- Success
- No Data
- Error

- s string
Will always be ok when there is data for the symbol requested.
- symbol array[string]
The symbol of the stock.
- ask array[number]
The ask price of the stock.
- askSize array[number]
The number of shares offered at the ask price.
- bid array[number]
The bid price.
- bidSize array[number]
The number of shares that may be sold at the bid price.
- mid array[number]
The midpoint price between the ask and the bid.
- last array[number]
The last price the stock traded at.
- change array[number]
The difference in price in currency units compared to the closing price of the previous primary trading session.
- changepct array[number]
The difference in price in percent, expressed as a decimal, compared to the closing price of the previous day. For example, a 3% change will be represented as 0.3.

note- When the market is open for primary trading, change and changepct are always calculated using the last traded price and the last primary session close. When the market is closed or in extended hours, this criteria is also used as long as extended is omitted or set to true.
- When extended is set to false, and the market is closed or in extended hours, quotes from extended hours are not considered. The values for change and changepct will be calculated using the last two closing prices instead.

- 52weekHigh array[number]
The 52-week high for the stock. This parameter is omitted unless the optional 52week request parameter is set to true.
- 52weekLow array[number]
The 52-week low for the stock. This parameter is omitted unless the optional 52week request parameter is set to true.
- volume array[number]
The number of shares traded during the current session.
- updated array[date]
The date/time of the current stock quote.

- s string
Status will be no_data if no quote can be found for the symbol.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

Edit this pagePreviousReal-Time PricesNextHistorical Candles- Endpoint
- Request Example
- Response Example
- Request Parameters
- Response Attributes

---

# Tags
<a id="tags"></a>

<sub>Source: https://www.marketdata.app/docs/api/tags</sub>

## A ​

- API: Beta 1
- API: High Usage 2
- API: Premium 1


---

---

# One doc tagged with "API: Beta"
<a id="one-doc-tagged-with-api-beta"></a>

<sub>Source: https://www.marketdata.app/docs/api/tags/api-beta</sub>

One doc tagged with "API: Beta"View All Tags## News tg b

The News endpoint is still in beta and has not yet been optimized for performance. Use caution before adding this endpoint in a prodution environment.

---

# 2 docs tagged with "API: High Usage"
<a id="2-docs-tagged-with-api-high-usage"></a>

<sub>Source: https://www.marketdata.app/docs/api/tags/api-high-usage</sub>

2 docs tagged with "API: High Usage"View All Tags## Quotes tg h

Get a current or historical end of day quote for a single options contract.

## Real-Time Prices tg h

This endpoint is currently in open beta. It is available to all users (including free trial users) during our open beta test. We welcome your feedback.

---

# One doc tagged with "API: Premium"
<a id="one-doc-tagged-with-api-premium"></a>

<sub>Source: https://www.marketdata.app/docs/api/tags/api-premium</sub>

One doc tagged with "API: Premium"View All Tags## Earnings tg p

Get historical earnings per share data or a future earnings calendar for a stock.

---

# Troubleshooting
<a id="troubleshooting"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting

Troubleshooting## 📄️ Authentication

Authentication issues usually arise due to incorrect headers, omission of the authorization header, or problems with URL parameters. If you encounter a 401 error, it's usually related to issues with your Authorization header. The most common issues are:

## 📄️ HTTP Status Codes

The Market Data API uses standard HTTP status codes to respond to each request. By preparing your application to utilize these status codes, you can often times solve common errors, or retry failed requests.

## 📄️ Logging

Why Logging is Important

## 📄️ URL Parameters

Introduction to URL Parameters

## 📄️ Multiple IP Addresses

If your account is blocked, you do not need to contact support. The block will automatically resolve after 5 minutes if you stop making API requests. Simply wait 5 minutes without making any requests from the blocked IP address, then resume with a single device or IP address.

## 📄️ Service Outages

Market Data, as stated in our terms of service, makes no representation as to the reliability, availability, or timeliness of our service. This is not just a standard disclaimer. We have not yet been able to achieve 99.9% reliability, which is a metric we consider a minimum level of reliability that is needed to operate without a backup provider.

Edit this pagePreviousData FeedNextAuthentication

---

# Authentication
<a id="authentication-2"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/authentication</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- Authentication

On this pageAuthenticationAuthentication issues usually arise due to incorrect headers, omission of the authorization header, or problems with URL parameters. If you encounter a 401 error, it's usually related to issues with your `Authorization`Authorization header. The most common issues are:

- Incorrect token
- Invalid characters to separate the query string from the path
- Invalid characters to separate query parameters from each other

Troubleshooting authentication issues is crucial for ensuring uninterrupted access to our API services. Most authentication issues are related to header-based authentication, but URL parameter authentication can also be troublesome to users who are getting started with Market Data as their first REST API. This guide aims to provide you with steps to resolve common problems.

tipEven though it is more complex to set-up, we encourage all users to take the extra time required to configure header-based authentication for our API, as this is the most secure method of authentication.

### Troubleshooting URL Parameter Authentication ​

Usually URL parameter authentication goes wrong because customers use invalid characters to separate the query string from the path. The correct character to use is `?`? and the correct character to use to separate query parameters is `&`&. If you use the wrong characters, the API will not be able to parse the query string correctly and will be unable to authenticate your request. Learn more about the correct format of the URL parameters [here](/docs/api/troubleshooting/url-parameters)here.

For example, suppose your token was `token1234`token1234 and you were also using the `dateformat`dateformat parameter to request a timestamp as the output format for the time. For a stocks/quotes request, the correct URL would be:

```http
https://api.marketdata.app/v1/stocks/quotes/SPY/?token=token1234&dateformat=timestamp
```

- Note how the token is separated from the path by a ? and the dateformat parameter is separated from the token by a &.

The ordering of the parameters is not important. You do not need to put `token`token as the first parameter. It would also be perfectly valid to use the following URL:

```http
https://api.marketdata.app/v1/stocks/quotes/SPY/?dateformat=timestamp&token=token1234
```

No matter the order of the parameters, the API will be able to parse the query string and authenticate your request as long as the correct characters are used to separate the query string from the path and the query parameters from each other.

### Troubleshooting Header Authentication ​

The most common issues customers face with header-based authentication are:

- Omission of the header
- Incorrect header name
- Invalid header format
- Incorrect token

#### Steps for Troubleshooting 401 Errors ​

1. Test the Token with URL Parameter Authentication
curl -X GET "https://api.marketdata.app/v1/stocks/quotes/SPY/?token=YOUR_TOKEN"

Use CURL to test your token using URL parameter authentication. If it works, you know that your token is valid. If you are using a token that is not valid, you will receive a 401 error. If you are using a token that is valid, you will receive a `200 OK`200 OK response along with a stock quote.

1. Inspect Request Headers

To inspect the headers your application is sending, especially the `Authorization`Authorization header, use our dedicated [headers endpoint](/docs/api/utilities/headers)headers endpoint. This will help you identify any discrepancies in the headers that might be causing authentication issues.

```bash
curl -X GET "https://api.marketdata.app/headers/" -H "Authorization: Token YOUR_TOKEN"
```

Make a request to [https://api.marketdata.app/headers/](https://api.marketdata.app/headers/)https://api.marketdata.app/headers/ from your application and save the headers. This endpoint will return a JSON response of the headers your application is sending, with sensitive headers like `Authorization`Authorization partially redacted for security. Compare the headers from your application's request to the expected headers.

If your application's `Authorization`Authorization header is different from what you expect, there may be an issue with how your application is setting headers. If the headers match your expectations, the issue may lie elsewhere, possibly with the token itself.

1. Log Response Headers and Submit a Helpdesk Ticket
curl -X GET "https://api.marketdata.app/v1/stocks/quotes/SPY/" -H "Authorization: Token YOUR_TOKEN" -i

Finally, we'll now make a header-authentication request using your token. Make a request using the CURL command above. If you receive a 401 error, the issue is with your token. If you receive a `200 OK`200 OK response, the issue is with your application's code.

tipIf the issue persists, include the log data and the Ray ID (listed in the CF-Ray header) when you submit a helpdesk ticket. This will help our support team locate your specific request in our server logs and assist you more effectively.

## Opening a Support Ticket ​

### When to Open a Ticket ​

Open a ticket if you experience persistent issues or errors that cannot be resolved through this troubleshooting guide.

### What to Include ​

Include the log data and the Ray ID for faster resolution. By attaching this information to your support ticket, it becomes much easier for our staff to understand and solve your ticket.

Edit this pagePreviousTroubleshootingNextHTTP Status Codes- Troubleshooting URL Parameter Authentication
- Troubleshooting Header Authentication
- Opening a Support Ticket
  - When to Open a Ticket
  - What to Include

---

# HTTP Status Codes
<a id="http-status-codes"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/http-status-codes</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- HTTP Status Codes

On this pageHTTP Status CodesThe Market Data API uses standard HTTP status codes to respond to each request. By preparing your application to utilize these status codes, you can often times solve common errors, or retry failed requests.

## Successful Requests (2xx) ​

These are requests that are answered successfully.

cautionSome libraries are not prepared to handle HTTP 203 response codes as successful requests. Ensure the library you are using can accept a 203 response code the same way as a 200 response code.

- 200 OK - Successfully answered the request.
- 203 NON-AUTHORITATIVE INFORMATION - Successfully served the request from our caching server. Treat this result the same as STATUS 200.
- 204 NO CONTENT - Indicates a successful request for explicitly requested cached data, but our cache server lacks cached data for the symbol requested. Resend the request using the live data feed.

## Client Errors (4xx) ​

Client errors occur when Market Data cannot respond to a request due to a problem with the request. The request will need to be modified in order to get a different response.

tipIf you believe your request is correct and you received a 4xx reply in error, please ensure you log our complete response to your request, including the full response headers along with the complete JSON error message we deliver in our reply. Open a ticket at our help desk and provide this information to our support staff and we will investigate further.

- 400 BAD REQUEST - The API endpoint is not being used properly, often due to a parameter that cannot be parsed correctly (e.g., sending a string instead of a number or vice versa).
- 401 UNAUTHORIZED - The token supplied with the request is missing, invalid, or cannot be used.
- 402 PAYMENT REQUIRED - The requested action cannot be performed with your current plan, such as attempting to access historical data with a free plan or very old historical data with a Starter plan.
- 403 FORBIDDEN - Access denied. Only one device is permitted to access the API at a time. Your IP address has changed, and your account is temporarily blocked for security reasons. Please wait 5 minutes before trying again.
- 404 NOT FOUND - No data exists for the requested symbol or time period. Consider trying a different symbol or time frame.
- 413 PAYLOAD TOO LARGE - The request payload is too large. This is often due to requesting a time frame longer than 1 year for candle data. Resubmit the request with a time frame of 1 year or less.
- 429 TOO MANY REQUESTS - The daily request limit for your account has been exceeded. New requests will be allowed at 9:30 AM ET (opening bell).
- 429 TOO MANY REQUESTS - Concurrent request limit reached. You've reached the limit of 50 requests running simultaneously on our server. Please wait until they are finished to make more.

## Server Errors (5xx) ​

Server errors are used to indicate problems with Market Data's service. They are requests that appear to be properly formed, but can't be responded to due to some kind of problem with our servers.

### Permanent Failures ​

- 500 INTERNAL SERVER ERROR - An unknown server issue prevents Market Data from responding to your request. Open a ticket with the helpdesk and include the Ray ID of the request.

### Temporary Failures ​

Most 5xx errors are temporary and resolve themselves on their own. Please retry requests that receive 5xx errors at a later time and they will probably be successful.

- 502 BAD GATEWAY - Market Data's API server does not respond to the gateway, indicating the API is offline or unreachable. This error is normally sporadic and due to network issues and will typically resolve itself within 1-2 minutes.
- 503 SERVICE UNAVAILABLE - Market Data's API server is accessible but cannot fulfill the request, usually due to server overload. Retry the request in a few minutes.
- 504 GATEWAY TIMEOUT - Market Data's load balancer received no response from the API, suggesting the request is taking too long to resolve. Retry in 1-2 minutes and report to the helpdesk if the issue persists.
- 509 API ENDPOINT OVERLOADED - The endpoint is currently overloaded. Retry in a few minutes and report to the helpdesk if the issue continues for more than 15 minutes.
- 524 A TIMEOUT OCCURRED - The Market Data API failed to provide an HTTP response before the default 100-second connection timeout, possibly due to server overload or resource struggles. Contact support if this continues for more than 15 minutes.
- 529 DATABASE OFFLINE - The database is offline, overloaded, or not responding. Contact support or submit a ticket if this error persists for more than 15 minutes.
- 530 DATABASE ERROR - The request resulted in a database error. Contact support or submit a ticket with your API request details.
- 540 API ENDPOINT OFFLINE - The Market Data API endpoint expected to respond is offline. Report to the helpdesk if this persists for more than 15 minutes.
- 598 API GATEWAY OFFLINE - The gateway server is not responding or is unavailable. Report to the helpdesk if this issue continues for more than 15 minutes.

Edit this pagePreviousAuthenticationNextLogging- Successful Requests (2xx)
- Client Errors (4xx)
- Server Errors (5xx)
  - Permanent Failures
  - Temporary Failures

---

# Logging
<a id="logging"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/logging</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- Logging

On this pageLogging## Why Logging is Important ​

Logging our API's responses is crucial for monitoring the behavior of your application and troubleshooting problems, either with our API or your usage of the API.

### What Should Be Logged ​

Market Data responds to successful requests with either a 200 or 203 status code. Therefore, we recommend you log any response that doesn't have a 2xx status code. Successful responses may be logged if you wish, but normally this is not necessary.

When logging errors, the log should include the exact request made, Market Data's response, and the CF-Ray header.

## Logging Examples ​

- NodeJS
- Python

logger.js```js
const axios = require("axios");const fs = require("fs");// Make the API requestaxios  .get("https://api.marketdata.app/v1/your_endpoint_here")  .then((response) => {    // Do nothing for successful responses  })  .catch((error) => {    if (error.response.status !== 200 && error.response.status !== 203) {      const logData = {        request: error.config.method.toUpperCase() + " " + error.config.url,        response: error.response.data,        cfRayHeader: error.response.headers["cf-ray"] || "Not available",      };      // Save to a logfile      fs.appendFileSync("api_error_log.json", JSON.stringify(logData) + "\n");    }  });
```

logger.py```python
import requestsimport json# Make the API requestresponse = requests.get("https://api.marketdata.app/v1/any_endpoint_here")# Check if the response is not 200 or 203if response.status_code not in [200, 203]:    log_data = {        "request": response.request.method + " " + response.request.url,        "response": response.content.decode("utf-8"),        "cf_ray_header": response.headers.get("CF-Ray", "Not available")    }    # Save to a logfile    with open("api_error_log.json", "a") as logfile:        logfile.write(json.dumps(log_data) + "\n")
```

## The CF-Ray Header ​

### What is the CF-Ray Header ​

The CF-Ray header (otherwise known as a Ray ID) is a hashed value that encodes information about the Cloudflare data center and the request. Every request that travels through the Cloudflare network is assigned a unique Ray ID for tracking.

### Why It's Important ​

Since Market Data operates on the Cloudflare network, we log each of our API responses with Cloudflare's Ray ID. This allows us to have a unique identifier for each and every API request made to our systems. Additionally, we can also trace all requests through the Cloudflare network from our servers to your application.

tipWhen opening a ticket at the customer helpdesk, if a Ray ID is provided to our support staff, we'll be able to identify the exact request you made and find why it produced an error.

## Opening a Support Ticket ​

### When to Open a Ticket ​

Open a ticket if you experience persistent issues or errors that cannot be resolved through logging. For example, if you are making properly formatted requests to our systems and you are getting INTERNAL SERVER ERROR messages.

### What to Include ​

Include the log data and the CF-Ray header value for faster resolution. By attaching your log data to your support ticket, it becomes much easier for our staff to understand and solve your ticket.

Edit this pagePreviousHTTP Status CodesNextURL Parameters- Why Logging is Important
  - What Should Be Logged
- Logging Examples
- The CF-Ray Header
  - What is the CF-Ray Header
  - Why It's Important
- Opening a Support Ticket
  - When to Open a Ticket
  - What to Include

---

# Multiple IP Addresses
<a id="multiple-ip-addresses"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/multiple-ip-addresses</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- Multiple IP Addresses

On this pageMultiple IP AddressesAutomatic ResolutionIf your account is blocked, you do not need to contact support. The block will automatically resolve after 5 minutes if you stop making API requests. Simply wait 5 minutes without making any requests from the blocked IP address, then resume with a single device or IP address.

During the block, you can continue making requests from the previously authorized IP address.

If you encounter an issue where your account is temporarily blocked due to accessing the API from multiple devices, follow these steps to resolve it:

## Problem ​

Your account is blocked because it was accessed from multiple IP addresses in a pattern that suggests simultaneous device usage. While changing IP addresses is permitted, rapidly switching back and forth between previously used IP addresses indicates multiple active devices, which is against our policy.

When this occurs, you'll receive an error response that includes detailed information to help you identify the source of the conflict:

```json
{  "s": "error",  "errmsg": "Access denied. Only one device is permitted. Your IP address has changed, and your account is temporarily blocked for security reasons. Please wait 5 minutes before trying again.",  "authorizedIP": "107.178.202.2",  "blockedIP": "44.116.21.32",  "troubleshootingGuide": "https://www.marketdata.app/docs/api/troubleshooting/multiple-ip-addresses"}
```

The error response includes:

- The IP address of your previous request (authorizedIP)
- The IP address of your current request (blockedIP)

You can use these IP addresses to:

1. Identify which devices or services are making the conflicting requests.
2. Check if the IPs match known ISPs, VPNs, cloud services, or other servers you're using.
3. Compare with your network configuration to determine if load balancing, round-robin outgoing requests, or failover is causing the issue.

### How It Works ​

When you access the API:

- Each new IP address you connect from is recorded
- If you connect from IP address A, then switch to IP address B, that's permitted.
- However, if you then switch back to IP address A while IP address B is still active within 5 minutes, this suggests two devices are being used simultaneously.
- This pattern triggers an automatic temporary block on your account.
- During the block, you can continue making requests from your previously authorized IP address.
- After the block expires, you can switch to a different IP address again, but should avoid switching back to recently used IPs.

### Common Scenarios ​

1. VPN Usage : If you connect to a VPN, then disconnect, your IP address may change back and forth rapidly. This can happen if you frequently switch between a VPN and your regular network.
2. Wi-Fi Network Changes : Switching between different Wi-Fi networks in a short period can result in different IP addresses being used within a single five minute period.
3. Load Balancing : Servers making outgoing requests might use multiple IP addresses, especially if they are part of a load-balanced setup, round-robin configuration, or if they use multiple network interfaces.
4. Proxy Usage : Using proxies or rotating proxies can cause your requests to appear from different IP addresses even if you are using the same device.
5. Cloud Functions : Cloud services like Amazon Web Services, Google Cloud, or Azure may send requests from ephemeral instances that change IP addresses frequently.
6. Google Apps Script : Using UrlFetch in Google Apps Script can result in requests coming from different IP addresses simultaneously, as Google's infrastructure will rotate requests through various servers.

## Solution ​

1. Wait for 5 Minutes : The block is temporary. Wait for 5 minutes before attempting to access the API again. During this time, ensure all your devices stop their API access.
2. Use a Single Active Device : While you can change devices or IP addresses:
  - Make sure to completely stop API access from your previous device before switching.
  - Do not switch devices more than once every 5 minutes.
  - Do not attempt to connect using multiple devices.
3. For Cloud Systems : If you're running cloud systems that make API calls:
  - Use a single cloud instance to make API calls.
  - Ensure old instances are fully terminated before starting new ones.
  - Purchase a dedicated IP address for your cloud instance if it will be starting and stopping frequently.

## Important Note ​

The system is designed to detect patterns of simultaneous access, not just IP changes. While you are permitted to change devices, attempting to maintain multiple active connections from different computers will result in account blocks.

For further assistance, please contact our support team.

Edit this pagePreviousURL ParametersNextService Outages- Problem
  - How It Works
  - Common Scenarios
- Solution
- Important Note

---

# Service Outages
<a id="service-outages"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/service-outages</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- Service Outages

On this pageService OutagesMarket Data, as stated in our [terms of service](https://www.marketdata.app/terms/)terms of service, makes no representation as to the reliability, availability, or timeliness of our service. This is not just a standard disclaimer. We have not yet been able to achieve 99.9% reliability, which is a metric we consider a minimum level of reliability that is needed to operate without a backup provider.

Market Data is a low cost provider and we have determined that cost, rather than reliability, is our key driver. While we hope to achieve 99.9% reliability in the future, our focus will remain on keeping down costs and avoiding price increases for our users.

RecommendationWe highly encourage users with mission critical applications to have a backup provider or utilize Market Data as their secondary provider.

## How To Confirm Downtime ​

We utilize the service UptimeRobot to independently monitor our real-time and historical APIs and the results of this monitoring is made available to the public at our [status page](https://www.marketdata.app/status/)status page.

- Status Page: https://www.marketdata.app/status/

### Confirm Downtime Programmatically ​

Use the [/utilities/status/ endpoint](/docs/api/utilities/status)/utilities/status/ endpoint to confirm the status of all Market Data services, including our APIs. This endpoint will remain online during outages and will send a JSON response that includes the status of all Market Data services.

tipThis endpoint is ideal to allow for automatic switching between Market Data and your backup provider.

- NodeJS
- Python

status.js```js
// Importing the required libraryconst axios = require('axios');// URL to the new JSON dataconst url = "https://api.marketdata.app/status/";// Service names for Historical Data API and Real-time Data APIconst historicalDataApiName = "Historical Data API";const realTimeDataApiName = "Real-time Data API";// Function to check the status of the given service nameasync function checkApiStatus(serviceName) {    try {        const response = await axios.get(url);        const jsonData = response.data;        if (jsonData.service.includes(serviceName)) {            const index = jsonData.service.indexOf(serviceName);            return jsonData.online[index] ? "Online" : "Offline";        } else {            return "Service name not found";        }    } catch (error) {        console.error("Error fetching API status:", error);        return "Failed to fetch API status";    }}// Checking the status of Historical Data API and Real-time Data APIasync function checkStatuses() {    const historicalStatus = await checkApiStatus(historicalDataApiName);    const realTimeStatus = await checkApiStatus(realTimeDataApiName);    console.log(`Historical Data API: ${historicalStatus}`);    console.log(`Real-time Data API: ${realTimeStatus}`);}checkStatuses();
```

status.py```python
# Importing the required libraryimport requests# URL to the new JSON dataurl = "https://api.marketdata.app/status/"json_data = requests.get(url).json()# Service names for Historical Data API and Real-time Data APIhistorical_data_api_name = "Historical Data API"real_time_data_api_name = "Real-time Data API"# Function to check the status of the given service namedef check_api_status(service_name):    if service_name in json_data["service"]:        index = json_data["service"].index(service_name)        return "Online" if json_data["online"][index] else "Offline"    else:        return "Service name not found"# Checking the status of Historical Data API and Real-time Data APIhistorical_status = check_api_status(historical_data_api_name)real_time_status = check_api_status(real_time_data_api_name)print(f"Historical Data API: {historical_status}")print(f"Real-time Data API: {real_time_status}")
```

## What To Do During Downtime ​

It is not necessary to advise us of downtime or service outages. We monitor the status of our systems and we investigate and respond to all service outages. During Market Data service outages, we encourage you to switch your systems over to your back-up provider until our systems come back online.

Edit this pagePreviousMultiple IP Addresses- How To Confirm Downtime
  - Confirm Downtime Programmatically
- What To Do During Downtime

---

# URL Parameters
<a id="url-parameters"></a>

<sub>Source: https://www.marketdata.app/docs/api/troubleshooting/url-parameters</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
- Troubleshooting
  - Authentication
  - HTTP Status Codes
  - Logging
  - URL Parameters
  - Multiple IP Addresses
  - Service Outages

- 
- Troubleshooting
- URL Parameters

On this pageURL Parameters## Introduction to URL Parameters ​

URL parameters, also known as query strings, are a way to pass information to a server as part of a URL. They are often used to filter or customize the response from the server. Understanding how to correctly build URL parameters is crucial for interacting with Market Data's APIs effectively.

### Structure of URL Parameters ​

A URL with parameters has the following structure:

```
https://api.marketdata.app/v1/stocks/quotes/SPY/?token=token1234&dateformat=timestamp
```

- Protocol: https://
- Host: api.marketdata.app
- Path (or Endpoint): /v1/stocks/quotes/SPY/
- Query String: Begins with a ? and includes token=token1234&dateformat=timestamp
  - token and dateformat are the names of the parameters.
  - token1234 and timestamp are the values assigned to those parameters.
  - & is used to separate multiple parameters.

### Common Uses of URL Parameters in Market Data's APIs ​

- Filtering: Retrieve a subset of data based on specific criteria.
- Formatting: Change the format of the data returned by the API.
- Authentication: Send credentials or tokens to access API data.

## How to Build URL Parameters ​

When building URL parameters, follow these guidelines to ensure they are structured correctly:

1. Start with the Endpoint URL: Identify the base URL of the API endpoint you are interacting with.
2. Add a Question Mark: Follow the base URL with a ? to start the query string.
3. Append Parameters: Add parameters in the format key=value. Use & to separate multiple parameters.
4. Encode Special Characters: Use URL encoding to handle special characters in keys or values.

### Example ​

Suppose you want to request stock quotes for `SPY`SPY with a specific date format and token authentication:

```text
https://api.marketdata.app/v1/stocks/quotes/SPY/?token=token1234&dateformat=timestamp
```

### Troubleshooting Common Mistakes ​

- Incorrect Character Usage: Ensure you use ? to start and & to separate parameters.
- Unencoded Characters: Encode special characters like spaces (%20), plus (%2B), etc, using URL encoding.

Edit this pagePreviousLoggingNextMultiple IP Addresses- Introduction to URL Parameters
  - Structure of URL Parameters
  - Common Uses of URL Parameters in Market Data's APIs
- How to Build URL Parameters
  - Example
  - Troubleshooting Common Mistakes

---

# Columns
<a id="columns"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/columns</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Columns

On this pageColumnsThe columns parameter is used to limit the results of any endpoint to only the columns you need.

## Parameter ​

## Use Example ​

```text
https://api.marketdata.app/v1/stocks/quotes/AAPL/?columns=ask,bid
```

## Response Example ​

```json
{ "ask": [152.14], "bid": [152.12] }
```

## Values ​

### string ​

Use a list of columns names separated by commas to limit the response to just the columns requested.

cautionWhen using the columns parameter the `s`s status output is suppressed from the response.

Edit this pagePreviousOffsetNextHeaders- Parameter
- Use Example
- Response Example
- Values
  - string

---

# Date Format
<a id="date-format"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/date-format</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Date Format

On this pageDate FormatThe dateformat parameter allows you specify the format you wish to receive date and time information in.

## Parameter ​

dateformat=<timestamp|unix|spreadsheet>

## Use Example ​

/candles/daily/AAPL?dateformat=timestamp

/candles/daily/AAPL?dateformat=unix

/candles/daily/AAPL?dateformat=spreadsheet

## Values ​

### timestamp ​

Receive dates and times as a timestamp. Market Data will return time stamped data in the timezone of the exchange. For example, closing bell on Dec 30, 2020 for the NYSE would be: 2020-12-30 16:00:00 -05:00.

### unix ​

Receive dates and times in unix format (seconds after the unix epoch). Market Data will return unix date and time data. For example, closing bell on Dec 30, 2020 for the NYSE would be: 1609362000.

### spreadsheet ​

Receive dates and times in spreadsheet format (days after the Excel epoch). For example, closing bell on Dec 30, 2020 for the NYSE would be: 44195.66667. Spreadsheet format does not support time zones. All times will be returned in the local timezone of the exchange.

Edit this pagePreviousFormatNextLimit- Parameter
- Use Example
- Values
  - timestamp
  - unix
  - spreadsheet

---

# Data FeedPremium
<a id="data-feedpremium"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/feed</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Data Feed

On this pageData FeedPremiumThe `feed`feed parameter allows the user to modify the data feed used for the API's response, forcing it to use cached data.

Our API offers three types of data feeds: `live`live, `cached`cached, and `delayed`delayed. These options are designed to meet diverse user needs, balancing between the immediacy of data and cost efficiency. Below is a detailed overview of each feed type, including examples and use-cases to help you choose the best option for your requirements.

Premium ParameterThis parameter can only be used with paid plans. Free plans and trial plans do not have the ability to control their data feed. Free plans will always receive delayed data.

## Live Feed ​

The `live`live feed provides real-time data, delivering the most current market information available. This option is ideal for scenarios requiring the latest data for immediate decision-making.

### Pricing for Live Feed ​

- Quotes: 1 credit per symbol included in the response that has quote data (bid/ask/mid/last price).
- Candles: 1 credit per 1,000 candles included in the response.
- Bulk Candles: 1 credit per symbol* included in the response.
- Other Endpoints: 1 credit per response.

### Requesting Live Data ​

To request real-time data, append `feed=live`feed=live to your API call or do nothing at all. If you omit the feed query parameter the live feed is used by default. Here's an example:

```http
GET https://api.marketdata.app/v1/options/chain/SPY/?feed=liveGET https://api.marketdata.app/v1/options/chain/SPY/
```

Both of these requests are equally valid and return the latest data for the specified symbol, ensuring you have up-to-the-second information.

## Cached Feed ​

The `cached`cached feed provides data that could be a few seconds to a few minutes old, offering a cost-effective solution for accessing large volumes of quote data. When you use cached data, there is no guarantee of how fresh the data will be. Tickers that are popular with Market Data customers are refreshed more often.

### Pricing for Cached Feed ​

- Quotes: 1 credit per request, regardless of the number of symbols. This makes it an economical choice for bulk data retrieval using endpoints like Option Chain and Bulk Stock Quotes.
- Historical Quotes: Unavailable
- Candles: Unavailable
- Bulk Candles: Unavailable
- Other Endpoints: Unavailable

### Use-Case for Cached Feed ​

The `cached`cached feed is perfect for users who need to access recent quote data across multiple symbols without the need for immediate pricing. It allows for significant cost savings, particularly when retrieving data for multiple symbols in a single request.

### Requesting Cached Data ​

To access the cached data, include `feed=cached`feed=cached in your API request. For example:

```http
GET https://api.marketdata.app/v1/options/chain/SPY/?feed=cached
```

This query retrieves data from our cache, offering an affordable way to gather extensive data with a single credit.

### Cached Feed Response Codes ​

When the `feed=cached`feed=cached parameter is added, the API's response codes are modified slightly. You will no longer get `200 OK`200 OK responses, but instead 203 and 204 responses:

- 203 NON-AUTHORITATIVE INFORMATION - This response indicates the response was successful and served from our cache server. You can treat this the same as a 200 response.
- 204 NO CONTENT - This response indicates that the request was correct and would ordinarily return a success response, but our caching server does not have any cache data for the symbol requested. Make a live request to fetch real-time data for this symbol.

## Delayed Feed ​

The `delayed`delayed feed provides data that is delayed by at least 15 minutes. All free and trial accounts receive delayed data by default. Paid accounts can also request delayed data if they wish.

### Pricing for Delayed Feed ​

- Pricing is the same as the live feed.

### Requesting Delayed Data ​

To access delayed data, include `feed=delayed`feed=delayed in your API request. For example:

```http
GET https://api.marketdata.app/v1/options/chain/SPY/?feed=delayed
```

This query retrieves data that is at least 15 minutes old.

## Feed Comparison ​

| Feature | Live Feed | Cached Feed | Delayed Feed |
| --- | --- | --- | --- |
| Data Timeliness | Real-time, up-to-the-second data | Seconds to minutes old | Delayed by 15 minutes |
| Pricing | 1 credit per symbol with quote data | 1 credit per request, regardless of symbol count | Same as live feed |
| Ideal Use-Case | Time-sensitive decisions requiring the latest data | Large volumes of data at lower cost | Non-time-sensitive applications |
| Default Option | Yes for Paid accounts (if feed parameter is omitted) | No (must specify feed=cached ) | Yes for Free and Trial accounts (cannot change feed) |
| Paid Accounts Access | ✅ | ✅ | ✅ |
| Free/Trial Accounts Access | ❌ | ❌ | ✅ |

- Opt for the live feed when you require the most current data for each symbol, and the immediate freshness of the data justifies the additional credits.
- Select the cached feed for bulk data retrieval or when working with a larger set of symbols, to capitalize on the cost efficiency of retrieving extensive data at a lower price.
- Choose the delayed feed for scenarios where data timeliness is less critical.

Edit this pagePreviousHuman ReadableNextTroubleshooting- Live Feed
  - Pricing for Live Feed
  - Requesting Live Data
- Cached Feed
  - Pricing for Cached Feed
  - Use-Case for Cached Feed
  - Requesting Cached Data
  - Cached Feed Response Codes
- Delayed Feed
  - Pricing for Delayed Feed
  - Requesting Delayed Data
- Feed Comparison

---

# Format
<a id="format"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/format</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Format

On this pageFormatThe format parameter is used to specify the format for your data. We support JSON and CSV formats. The default format is JSON.

## Parameter ​

format=<json|csv>

## Use Example ​

/candles/daily/AAPL?format=json

/candles/daily/AAPL?format=csv

## Values ​

### json (default) ​

Use JSON to format the data in Javascript Object Notation (JSON) format. This format is ideal for programmatic use of the data.

### csv ​

Use CSV to format the data in lightweight comma separated value (CSV) format. This format is ideal for importing the data into spreadsheets.

Edit this pagePreviousTokenNextDate Format- Parameter
- Use Example
- Values
  - json (default)
  - csv

---

# Headers
<a id="headers"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/headers</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Headers

On this pageHeadersThe headers parameter is used to turn off headers when using CSV output.

## Parameter ​

headers=<true|false>

## Use Example ​

/candles/daily/AAPL?headers=false&format=csv

## Values ​

### true (default) ​

If the headers argument is not used, by default headers are turned on.

### false ​

Turns headers off and returns just the data points.

Edit this pagePreviousColumnsNextHuman Readable- Parameter
- Use Example
- Values
  - true (default)
  - false

---

# Human Readable
<a id="human-readable"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/human-readable</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Human Readable

On this pageHuman ReadableThe human parameter will use human-readable attribute names in the JSON or CSV output instead of the standard camelCase attribute names. Use of this parameter will result in API output that can be loaded directly into a table or viewer and presented to an end-user with no further transformation required on the front-end.

## Parameter ​

human=<true|false>

## Use Example ​

[https://api.marketdata.app/v1/stocks/quotes/AAPL/?human=true](https://api.marketdata.app/v1/stocks/quotes/AAPL/?human=true)https://api.marketdata.app/v1/stocks/quotes/AAPL/?human=true

## Response Example ​

```json
{  "Symbol": ["AAPL"],  "Ask": [152.63],  "Ask Size": [400],  "Bid": [152.61],  "Bid Size": [600],  "Mid": [152.62],  "Last": [152.63],  "Volume": [35021819],  "Date": [1668531422]}
```

## Values ​

### True ​

The API will output human-readable attribute names instead of the standard camelCase attribute names. The output will be capitalized as a title, with the first letter of each major word capitalized. The `s`s status response is also surpressed.

### False (default) ​

Output of attribute names will be according to API specifications using camelCase. If the `human`human attribute is omitted, the default behavior is `false`false.

Edit this pagePreviousHeadersNextData Feed- Parameter
- Use Example
- Response Example
- Values
  - True
  - False (default)

---

# Limit
<a id="limit"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/limit</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Limit

On this pageLimitThe `limit`limit parameter allows you to limit the number of results for a particular API call or override an endpoint’s default limits to get more data.

- Default Limit: 10,000
- Maximum Limit: 50,000

In the example below, the daily candle endpoint by default returns the last 252 daily bars. By using limit you could modify the behavior return the last two weeks or 10 years of data.

## Parameter ​

limit=<number>

## Use Example ​

/candles/daily/AAPL?limit=10

/candles/daily/AAPL?limit=2520

## Values ​

### integer (required) ​

The limit parameter accepts any positive integer as an input.

Edit this pagePreviousDate FormatNextOffset- Parameter
- Use Example
- Values
  - integer (required)

---

# Offset
<a id="offset"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/offset</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Offset

On this pageOffsetThe offset parameter is used together with limit to allow you to implement pagination in your application. Offset will allow you to return values starting at a certain value.

## Parameter ​

offset=<number>

## Use Example ​

/candles/daily/AAPL?limit=10&offset=10

## Values ​

### integer (required) ​

The limit parameter accepts any positive integer as an input.

Edit this pagePreviousLimitNextColumns- Parameter
- Use Example
- Values
  - integer (required)

---

# Token
<a id="token"></a>

<sub>Source: https://www.marketdata.app/docs/api/universal-parameters/token</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
- Universal Parameters
  - Token
  - Format
  - Date Format
  - Limit
  - Offset
  - Columns
  - Headers
  - Human Readable
  - Data Feed Premium
- Troubleshooting

- 
- Universal Parameters
- Token

On this pageTokenThe token parameter allows you to submit a read-only access token as a parameter. If your access token is write-enabled (authorized for trading), you may not use the token as a parameter, and must submit it in a header.

Security WarningWhen submitting your token in a URL, your token is exposed in server logs, cached in your browser, or otherwise made available. We do not recommend using your token as a parameter. This should only be used as a last resort in when you are unable to submit your token in a header.

## Parameter ​

token=<token>

## Use Example ​

[https://api.marketdata.app/v1/stocks/quotes/SPY/?token=put-your-token-here](https://api.marketdata.app/v1/stocks/quotes/SPY/?token=put-your-token-here)https://api.marketdata.app/v1/stocks/quotes/SPY/?token=put-your-token-here

## Values ​

### token ​

Submit your read-only access token as a value.

Edit this pagePreviousUniversal ParametersNextFormat- Parameter
- Use Example
- Values
  - token

---

# Utilities
<a id="utilities"></a>

<sub>Source: https://www.marketdata.app/docs/api/utilities</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
  - API Status New
  - Headers
- Universal Parameters
- Troubleshooting

- 
- Utilities

On this pageUtilitiesThese endpoints are designed to assist with API-related service issues, including checking the online status and uptime.

## Root Endpoint For Utilities ​

```text
https://api.marketdata.app/
```

## Utilities Endpoints ​

## 📄️ API Status

Check the current status of Market Data services and historical uptime. The status of the Market Data API is updated every 5 minutes. Historical uptime is available for the last 30 and 90 days.

## 📄️ Headers

This endpoint allows users to retrieve a JSON response of the headers their application is sending, aiding in troubleshooting authentication issues, particularly with the Authorization header.

Edit this pagePreviousCandlesNextAPI Status- Root Endpoint For Utilities
- Utilities Endpoints

---

# Headers
<a id="headers-2"></a>

<sub>Source: https://www.marketdata.app/docs/api/utilities/headers</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
  - API Status New
  - Headers
- Universal Parameters
- Troubleshooting

- 
- Utilities
- Headers

On this pageHeadersThis endpoint allows users to retrieve a JSON response of the headers their application is sending, aiding in troubleshooting authentication issues, particularly with the Authorization header.

tipThe values in sensitive headers such as `Authorization`Authorization are partially redacted in the response for security purposes.

## Endpoint ​

```text
https://api.marketdata.app/headers/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python

GET [https://api.marketdata.app/headers/](https://api.marketdata.app/headers/)https://api.marketdata.app/headers/

headersCheck.js```js
fetch("https://api.marketdata.app/headers/")  .then((res) => res.json())  .then((json) => console.log(json))  .catch((err) => console.log(err));
```

headersCheck.py```python
import requestsurl = "https://api.marketdata.app/headers/"response = requests.get(url)print(response.text)
```

## Response Example ​

```json
{    "accept": "*/*",    "accept-encoding": "gzip",    "authorization": "Bearer *******************************************************YKT0",    "cache-control": "no-cache",    "cf-connecting-ip": "132.43.100.7",    "cf-ipcountry": "US",    "cf-ray": "85bc0c2bef389lo9",    "cf-visitor": "{\"scheme\":\"https\"}",    "connection": "Keep-Alive",    "host": "api.marketdata.app",    "postman-token": "09efc901-97q5-46h0-930a-7618d910b9f8",    "user-agent": "PostmanRuntime/7.36.3",    "x-forwarded-proto": "https",    "x-real-ip": "53.43.221.49"}
```

## Response Attributes ​

- Success
- Error

- Headers object
A JSON object representing the headers received from the user's request. This object includes standard and custom headers along with their respective values.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

This endpoint is particularly useful for debugging issues related to authentication by allowing users to see exactly what headers are being sent to the API.

Edit this pagePreviousAPI StatusNextUniversal Parameters- Endpoint
- Request Example
- Response Example
- Response Attributes

---

# API StatusNew
<a id="api-statusnew"></a>

<sub>Source: https://www.marketdata.app/docs/api/utilities/status</sub>

- Introduction
- SDKs
- Authentication
- Rate Limits
- Dates and Times
- Markets
- Stocks
- Options
- Mutual Funds
- Utilities
  - API Status New
  - Headers
- Universal Parameters
- Troubleshooting

- 
- Utilities
- API Status

On this pageAPI StatusNewCheck the current status of Market Data services and historical uptime. The status of the Market Data API is updated every 5 minutes. Historical uptime is available for the last 30 and 90 days.

tipThis endpoint will continue to respond with the current status of the Market Data API, even if the API is offline. This endpoint is public and does not require a token.

## Endpoint ​

```text
https://api.marketdata.app/status/
```

#### Method ​

```text
GET
```

## Request Example ​

- HTTP
- NodeJS
- Python

GET [https://api.marketdata.app/status/](https://api.marketdata.app/status/)https://api.marketdata.app/status/

statusCheck.js```js
fetch("https://api.marketdata.app/status/")  .then((res) => res.json())  .then((json) => console.log(json))  .catch((err) => console.log(err));
```

statusCheck.py```python
import requestsurl = "https://api.marketdata.app/status/"response = requests.get(url)print(response.text)
```

## Response Example ​

```json
{  "s": "ok",  "service": [    "/v1/funds/candles/",    "/v1/indices/candles/",    "/v1/indices/quotes/",    "/v1/markets/status/",    "/v1/options/chain/",    "/v1/options/expirations/",    "/v1/options/lookup/",    "/v1/options/quotes/",    "/v1/options/strikes/",    "/v1/stocks/bulkcandles/",    "/v1/stocks/bulkquotes/",    "/v1/stocks/candles/",    "/v1/stocks/earnings/",    "/v1/stocks/news/",    "/v1/stocks/quotes/"  ],  "status": [    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online",    "online"  ],  "online": [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true],  "uptimePct30d": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  "uptimePct90d": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  "updated": [1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832, 1734036832]}
```

## Response Attributes ​

- Success
- Error

- s string
Will always be ok when the status information is successfully retrieved.
- service array[string]
The list of services being monitored.
- status array[string]
The current status of each service ( online or offline ).
- online array[boolean]
Boolean indicators for the online status of each service.
- uptimePct30d array[number]
The uptime percentage of each service over the last 30 days.
- uptimePct90d array[number]
The uptime percentage of each service over the last 90 days.
- updated array[date]
The timestamp of the last update for each service's status.

- s string
Status will be error if the request produces an error response.
- errmsg string An error message.

For more details on the API's status, visit the [Market Data API Status Page](https://www.marketdata.app/status/)Market Data API Status Page.

Edit this pagePreviousUtilitiesNextHeaders- Endpoint
- Request Example
- Response Example
- Response Attributes
