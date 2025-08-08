    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks using EODHD's native screener API with market cap range splitting.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"[EnhancedEODHDProvider.screen_stocks] Called with criteria limit: {criteria.limit}")
            logger.info("Performing stock screening using official EODHD library")
            
            # Default to US exchanges if not specified
            exchanges = criteria.exchanges or ['NYSE', 'NASDAQ']
            
            all_results = []
            
            # Determine market cap ranges to query
            min_cap = int(criteria.min_market_cap) if criteria.min_market_cap else 50000000
            max_cap = int(criteria.max_market_cap) if criteria.max_market_cap else 5000000000
            
            # Split into market cap ranges to bypass the 1000 result limit
            market_cap_ranges = []
            if max_cap >= 4000000000:
                market_cap_ranges.append((4000000000, min(max_cap, 5000000000)))
            if max_cap >= 3000000000 and min_cap < 4000000000:
                market_cap_ranges.append((max(min_cap, 3000000000), min(max_cap, 4000000000)))
            if max_cap >= 2000000000 and min_cap < 3000000000:
                market_cap_ranges.append((max(min_cap, 2000000000), min(max_cap, 3000000000)))
            if max_cap >= 1000000000 and min_cap < 2000000000:
                market_cap_ranges.append((max(min_cap, 1000000000), min(max_cap, 2000000000)))
            if max_cap >= 500000000 and min_cap < 1000000000:
                market_cap_ranges.append((max(min_cap, 500000000), min(max_cap, 1000000000)))
            if max_cap >= 250000000 and min_cap < 500000000:
                market_cap_ranges.append((max(min_cap, 250000000), min(max_cap, 500000000)))
            if max_cap >= 100000000 and min_cap < 250000000:
                market_cap_ranges.append((max(min_cap, 100000000), min(max_cap, 250000000)))
            if min_cap < 100000000:
                market_cap_ranges.append((min_cap, min(max_cap, 100000000)))
            
            logger.info(f"Screening stocks in {len(market_cap_ranges)} market cap ranges to bypass API limits")
            
            for range_min, range_max in market_cap_ranges:
                range_label = f"${range_min/1000000:.0f}M-${range_max/1000000:.0f}M"
                
                for exchange in exchanges:
                    try:
                        # Build filters for this specific market cap range and exchange
                        range_filters = [
                            ['market_capitalization', '>=', range_min],
                            ['market_capitalization', '<=', range_max]
                        ]
                        if criteria.min_volume:
                            range_filters.append(['avgvol_200d', '>=', criteria.min_volume])
                        range_filters.append(['exchange', '=', exchange])
                        
                        logger.info(f"Screening {exchange} stocks in {range_label} range...")
                        
                        offset = 0
                        max_per_request = 100  # Use smaller batches
                        range_results = []
                        
                        while offset <= 999:  # EODHD API has a maximum offset of 999
                            # Call the method with keyword arguments via lambda
                            response = await asyncio.get_event_loop().run_in_executor(
                                None, 
                                lambda: self.client.stock_market_screener(
                                    sort='market_capitalization.desc',
                                    filters=range_filters,
                                    limit=max_per_request,
                                    offset=offset
                                )
                            )
                            
                            if response and isinstance(response, dict) and 'data' in response:
                                batch_results = response['data']
                                if not batch_results:
                                    break  # No more results
                                
                                for stock_data in batch_results:
                                    try:
                                        from src.models.api_models import EODHDScreenerResult
                                        result = EODHDScreenerResult.from_api_response(stock_data)
                                        range_results.append(result)
                                    except Exception as e:
                                        logger.warning(f"Error parsing screener result: {e}")
                                        continue
                                
                                # Check if we should continue
                                if len(batch_results) < max_per_request:
                                    break  # No more results available
                                    
                                offset += len(batch_results)
                                
                                # Small delay between requests to avoid rate limiting
                                await asyncio.sleep(0.1)
                            else:
                                break
                        
                        if range_results:
                            logger.info(f"  Found {len(range_results)} stocks in {exchange} {range_label}")
                            all_results.extend(range_results)
                        
                    except Exception as e:
                        logger.warning(f"Error screening {exchange} in range {range_label}: {e}")
                        continue
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(exchanges) * len(market_cap_ranges)
            
            if all_results:
                logger.info(f"Total stocks retrieved across all ranges: {len(all_results)}")
                
                # Sort by market cap descending
                all_results.sort(
                    key=lambda x: x.market_capitalization or Decimal('0'), 
                    reverse=True
                )
                
                # Apply final limit if specified
                if criteria.limit and len(all_results) > criteria.limit:
                    logger.info(f"Trimming results from {len(all_results)} to {criteria.limit}")
                    all_results = all_results[:criteria.limit]
                
                screener_response = EODHDScreenerResponse(
                    results=all_results,
                    total_count=len(all_results)
                )
                
                metadata = ProviderMetadata.for_enhanced_eodhd(latency_ms)
                
                return APIResponse(
                    status=APIStatus.OK,
                    data=screener_response,
                    metadata=metadata
                )
            else:
                logger.warning("No stocks found matching criteria")
                return APIResponse(
                    status=APIStatus.NO_DATA,
                    error=APIError(404, "No stocks found matching screening criteria")
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Error in screen_stocks: {e}")
            
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(500, f"Screening error: {str(e)}"),
                metadata=ProviderMetadata.for_enhanced_eodhd(latency_ms)
            )