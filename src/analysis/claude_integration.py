"""
Claude AI integration utilities for PMCC Scanner.

This module provides utilities for integrating Claude AI analysis with existing
PMCC analysis workflows, including data merging and result enhancement.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

if TYPE_CHECKING:
    from src.config.settings import ScanConfig

from src.models.api_models import (
    EnhancedStockData, ClaudeAnalysisResponse, PMCCOpportunityAnalysis,
    APIResponse, APIStatus
)

logger = logging.getLogger(__name__)


class ClaudeIntegrationManager:
    """
    Manager for integrating Claude AI analysis with PMCC workflows.
    
    This class handles the integration between Claude's AI analysis and the
    existing PMCC analysis system, providing methods to merge results and
    enhance existing data structures.
    """
    
    def __init__(self, settings: Optional['ScanConfig'] = None):
        """Initialize the Claude integration manager.
        
        Args:
            settings: Optional ScanConfig object for scoring weights
        """
        self.analysis_history: List[ClaudeAnalysisResponse] = []
        self.settings = settings
        self._stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'opportunities_analyzed': 0,
            'high_confidence_recommendations': 0
        }
    
    def merge_claude_analysis_with_pmcc_data(
        self, 
        pmcc_opportunities: List[Dict[str, Any]],
        claude_response: ClaudeAnalysisResponse,
        enhanced_stock_data: List[EnhancedStockData]
    ) -> List[Dict[str, Any]]:
        """
        Merge Claude AI analysis with existing PMCC opportunity data.
        
        This method combines traditional PMCC scoring with Claude's AI insights
        to create enhanced opportunity rankings and recommendations.
        
        Args:
            pmcc_opportunities: List of existing PMCC opportunities
            claude_response: Claude AI analysis response
            enhanced_stock_data: Original enhanced stock data
            
        Returns:
            List of enhanced PMCC opportunities with AI insights
        """
        logger.info(f"Merging Claude analysis for {len(pmcc_opportunities)} PMCC opportunities")
        
        # Create a lookup for Claude analysis by symbol
        claude_analysis_lookup = {
            analysis.symbol: analysis 
            for analysis in claude_response.opportunities
        }
        
        # Create enhanced stock data lookup
        stock_data_lookup = {
            stock.symbol: stock 
            for stock in enhanced_stock_data
        }
        
        enhanced_opportunities = []
        
        for opportunity in pmcc_opportunities:
            symbol = opportunity.get('symbol', '')
            
            # Start with original PMCC data
            enhanced_opportunity = {**opportunity}  # Copy original data
            
            # Add Claude AI insights if available
            claude_analysis = claude_analysis_lookup.get(symbol)
            if claude_analysis:
                enhanced_opportunity.update(self._integrate_claude_insights(
                    enhanced_opportunity, claude_analysis, stock_data_lookup.get(symbol)
                ))
            else:
                # Mark as not analyzed by Claude
                enhanced_opportunity.update({
                    'claude_analyzed': False,
                    'claude_score': None,
                    'claude_reasoning': 'Not analyzed by Claude AI',
                    'ai_recommendation': None
                })
            
            enhanced_opportunities.append(enhanced_opportunity)
        
        # Sort opportunities by combined score (if available)
        enhanced_opportunities.sort(
            key=lambda x: x.get('combined_score', x.get('pmcc_score', 0)), 
            reverse=True
        )
        
        # Update statistics
        self._update_integration_stats(claude_response, enhanced_opportunities)
        
        return enhanced_opportunities
    
    def _integrate_claude_insights(
        self, 
        pmcc_opportunity: Dict[str, Any], 
        claude_analysis: PMCCOpportunityAnalysis,
        stock_data: Optional[EnhancedStockData]
    ) -> Dict[str, Any]:
        """
        Integrate Claude AI insights with a single PMCC opportunity.
        
        Args:
            pmcc_opportunity: Original PMCC opportunity data
            claude_analysis: Claude AI analysis for this stock
            stock_data: Enhanced stock data if available
            
        Returns:
            Dictionary with integrated AI insights
        """
        # Extract original PMCC score
        original_pmcc_score = pmcc_opportunity.get('pmcc_score', 0)
        claude_score = float(claude_analysis.score)
        
        # Calculate combined score (weighted average)
        # Use configurable weights from settings, fallback to default 60%/40%
        pmcc_weight = self.settings.traditional_pmcc_weight if self.settings else 0.6
        ai_weight = self.settings.ai_analysis_weight if self.settings else 0.4
        combined_score = (original_pmcc_score * pmcc_weight) + (claude_score * ai_weight)
        
        # Determine overall recommendation
        recommendation = self._determine_combined_recommendation(
            pmcc_opportunity.get('recommendation', 'neutral'),
            claude_analysis.recommendation,
            claude_analysis.confidence
        )
        
        # Create integrated insights
        integrated_data = {
            'claude_analyzed': True,
            'claude_score': claude_score,
            'claude_reasoning': claude_analysis.reasoning,
            'claude_confidence': float(claude_analysis.confidence) if claude_analysis.confidence else None,
            'combined_score': combined_score,
            'ai_recommendation': recommendation,
            
            # Detailed AI insights
            'ai_insights': {
                'risk_score': float(claude_analysis.risk_score) if claude_analysis.risk_score else None,
                'fundamental_health_score': float(claude_analysis.fundamental_health_score) if claude_analysis.fundamental_health_score else None,
                'technical_setup_score': float(claude_analysis.technical_setup_score) if claude_analysis.technical_setup_score else None,
                'calendar_risk_score': float(claude_analysis.calendar_risk_score) if claude_analysis.calendar_risk_score else None,
                'pmcc_quality_score': float(claude_analysis.pmcc_quality_score) if claude_analysis.pmcc_quality_score else None,
                'key_strengths': claude_analysis.key_strengths or [],
                'key_risks': claude_analysis.key_risks or [],
            },
            
            # Analysis metadata
            'analysis_timestamp': datetime.now().isoformat(),
            'model_used': 'claude-3-5-sonnet',  # Could be dynamic based on response
        }
        
        # Add market context insights if available
        if hasattr(claude_analysis, 'market_assessment') and claude_analysis.market_assessment:
            integrated_data['market_context'] = claude_analysis.market_assessment
        
        return integrated_data
    
    def _determine_combined_recommendation(
        self, 
        pmcc_recommendation: str, 
        claude_recommendation: Optional[str],
        claude_confidence: Optional[Decimal]
    ) -> str:
        """
        Determine combined recommendation from PMCC and Claude analysis.
        
        Args:
            pmcc_recommendation: Original PMCC recommendation
            claude_recommendation: Claude AI recommendation
            claude_confidence: Claude's confidence level
            
        Returns:
            Combined recommendation string
        """
        if not claude_recommendation:
            return pmcc_recommendation
        
        # Map recommendations to numerical scores for comparison
        rec_scores = {
            'strong_sell': -2,
            'sell': -1,
            'avoid': -1,
            'neutral': 0,
            'hold': 0,
            'buy': 1,
            'strong_buy': 2
        }
        
        pmcc_score = rec_scores.get(pmcc_recommendation.lower(), 0)
        claude_score = rec_scores.get(claude_recommendation.lower(), 0)
        
        # Weight by confidence (higher confidence = more influence)
        confidence_weight = float(claude_confidence) / 100.0 if claude_confidence else 0.5
        
        # Calculate weighted average
        weighted_score = (pmcc_score * (1 - confidence_weight)) + (claude_score * confidence_weight)
        
        # Map back to recommendation
        if weighted_score >= 1.5:
            return 'strong_buy'
        elif weighted_score >= 0.5:
            return 'buy'
        elif weighted_score <= -1.5:
            return 'strong_sell'
        elif weighted_score <= -0.5:
            return 'sell'
        else:
            return 'hold'
    
    def create_enhanced_opportunity_summary(
        self, 
        enhanced_opportunities: List[Dict[str, Any]],
        claude_response: ClaudeAnalysisResponse
    ) -> Dict[str, Any]:
        """
        Create a summary of enhanced opportunities with AI insights.
        
        Args:
            enhanced_opportunities: List of enhanced opportunities
            claude_response: Original Claude analysis response
            
        Returns:
            Summary dictionary with key insights and statistics
        """
        total_opportunities = len(enhanced_opportunities)
        claude_analyzed = len([opp for opp in enhanced_opportunities if opp.get('claude_analyzed', False)])
        
        # Get top recommendations
        strong_buy_count = len([opp for opp in enhanced_opportunities if opp.get('ai_recommendation') == 'strong_buy'])
        buy_count = len([opp for opp in enhanced_opportunities if opp.get('ai_recommendation') == 'buy'])
        
        # Calculate average scores
        claude_scores = [opp.get('claude_score', 0) for opp in enhanced_opportunities if opp.get('claude_score')]
        combined_scores = [opp.get('combined_score', 0) for opp in enhanced_opportunities if opp.get('combined_score')]
        
        avg_claude_score = sum(claude_scores) / len(claude_scores) if claude_scores else 0
        avg_combined_score = sum(combined_scores) / len(combined_scores) if combined_scores else 0
        
        # Get top opportunities
        top_10_opportunities = enhanced_opportunities[:10]
        
        # Extract key insights
        all_strengths = []
        all_risks = []
        for opp in enhanced_opportunities:
            insights = opp.get('ai_insights', {})
            all_strengths.extend(insights.get('key_strengths', []))
            all_risks.extend(insights.get('key_risks', []))
        
        # Count common themes
        strength_counts = {}
        risk_counts = {}
        for strength in all_strengths:
            strength_counts[strength] = strength_counts.get(strength, 0) + 1
        for risk in all_risks:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        # Get top themes
        top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_risks = sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        summary = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_opportunities': total_opportunities,
                'claude_analyzed_count': claude_analyzed,
                'analysis_coverage': claude_analyzed / total_opportunities if total_opportunities > 0 else 0,
                'market_assessment': claude_response.market_assessment
            },
            
            'recommendation_distribution': {
                'strong_buy': strong_buy_count,
                'buy': buy_count,
                'hold': total_opportunities - strong_buy_count - buy_count,
                'avoid': 0  # Assuming no sell recommendations for PMCC
            },
            
            'score_analysis': {
                'average_claude_score': round(avg_claude_score, 2),
                'average_combined_score': round(avg_combined_score, 2),
                'score_improvement': round(avg_combined_score - avg_claude_score, 2)
            },
            
            'top_opportunities': [
                {
                    'symbol': opp.get('symbol'),
                    'combined_score': opp.get('combined_score'),
                    'ai_recommendation': opp.get('ai_recommendation'),
                    'claude_reasoning': opp.get('claude_reasoning', '')[:100] + '...' if len(opp.get('claude_reasoning', '')) > 100 else opp.get('claude_reasoning', '')
                }
                for opp in top_10_opportunities
            ],
            
            'market_themes': {
                'common_strengths': [(theme, count) for theme, count in top_strengths],
                'common_risks': [(theme, count) for theme, count in top_risks]
            },
            
            'performance_metrics': {
                'analysis_time_ms': claude_response.processing_time_ms,
                'model_used': claude_response.model_used,
                'input_tokens': claude_response.input_tokens,
                'output_tokens': claude_response.output_tokens
            }
        }
        
        return summary
    
    def _update_integration_stats(
        self, 
        claude_response: ClaudeAnalysisResponse, 
        enhanced_opportunities: List[Dict[str, Any]]
    ):
        """Update integration statistics."""
        self._stats['total_analyses'] += 1
        self._stats['successful_analyses'] += 1
        self._stats['opportunities_analyzed'] += len(claude_response.opportunities)
        
        high_confidence_count = len([
            opp for opp in enhanced_opportunities 
            if opp.get('claude_confidence', 0) >= 75
        ])
        self._stats['high_confidence_recommendations'] += high_confidence_count
        
        # Store analysis history (keep last 100)
        self.analysis_history.append(claude_response)
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-100:]
        
        logger.info(f"Integration stats updated: {self._stats}")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        success_rate = (
            self._stats['successful_analyses'] / self._stats['total_analyses'] 
            if self._stats['total_analyses'] > 0 else 0
        )
        
        return {
            **self._stats,
            'success_rate': success_rate,
            'average_opportunities_per_analysis': (
                self._stats['opportunities_analyzed'] / self._stats['successful_analyses']
                if self._stats['successful_analyses'] > 0 else 0
            ),
            'analysis_history_size': len(self.analysis_history)
        }
    
    def filter_opportunities_by_ai_criteria(
        self, 
        enhanced_opportunities: List[Dict[str, Any]],
        min_combined_score: float = 70.0,
        min_confidence: float = 60.0,
        required_recommendation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter opportunities based on AI analysis criteria.
        
        Args:
            enhanced_opportunities: List of enhanced opportunities
            min_combined_score: Minimum combined score threshold
            min_confidence: Minimum Claude confidence threshold
            required_recommendation: Required AI recommendation (e.g., 'buy', 'strong_buy')
            
        Returns:
            Filtered list of opportunities
        """
        filtered = []
        
        for opp in enhanced_opportunities:
            # Check combined score
            if opp.get('combined_score', 0) < min_combined_score:
                continue
            
            # Check confidence
            if opp.get('claude_confidence', 0) < min_confidence:
                continue
            
            # Check recommendation
            if required_recommendation and opp.get('ai_recommendation') != required_recommendation:
                continue
            
            filtered.append(opp)
        
        logger.info(f"Filtered {len(filtered)} opportunities from {len(enhanced_opportunities)} based on AI criteria")
        return filtered
    
    def prepare_opportunities_for_claude(self, opportunities) -> Dict[str, Any]:
        """
        Prepare PMCC opportunities data for Claude AI analysis.
        
        This method takes PMCC opportunity data (either PMCCCandidate objects or dictionaries)
        and formats it into a structure suitable for Claude API consumption, including 
        complete options data, Greeks, and PMCC position details.
        
        Args:
            opportunities: List of PMCCCandidate objects or dictionaries
            
        Returns:
            Dictionary containing formatted data for Claude analysis
        """
        from src.models.pmcc_models import PMCCCandidate
        
        logger.info(f"Preparing {len(opportunities)} opportunities for Claude analysis")
        
        if not opportunities:
            logger.warning("No opportunities provided for Claude preparation")
            return {
                'opportunities': [],
                'market_context': {},
                'analysis_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'opportunity_count': 0,
                    'prepared_for_claude': True
                }
            }
        
        prepared_opportunities = []
        symbols_analyzed = set()
        
        for opp in opportunities:
            try:
                # Handle both PMCCCandidate objects and dictionary formats
                if isinstance(opp, PMCCCandidate):
                    symbol = opp.symbol
                    underlying_price = float(opp.underlying_price)
                    pmcc_score = float(opp.total_score) if opp.total_score else 0
                    liquidity_score = float(opp.liquidity_score)
                    
                    # Extract PMCC analysis details
                    analysis = opp.analysis
                    if analysis:
                        net_debit = float(analysis.net_debit) if analysis.net_debit else 0
                        credit_received = float(analysis.credit_received) if analysis.credit_received else 0
                        
                        # Risk metrics
                        risk_metrics = analysis.risk_metrics
                        max_profit = float(risk_metrics.max_profit) if risk_metrics and risk_metrics.max_profit else 0
                        max_loss = float(risk_metrics.max_loss) if risk_metrics and risk_metrics.max_loss else 0
                        breakeven = float(risk_metrics.breakeven) if risk_metrics and risk_metrics.breakeven else 0
                        risk_reward_ratio = float(risk_metrics.risk_reward_ratio) if risk_metrics and risk_metrics.risk_reward_ratio else 0
                        
                        # LEAPS option details (long call)
                        long_call = analysis.long_call
                        leaps_data = {
                            'option_symbol': long_call.option_symbol,
                            'strike': float(long_call.strike),
                            'expiration': long_call.expiration.isoformat(),
                            'dte': long_call.dte,
                            'delta': float(long_call.delta) if long_call.delta else None,
                            'gamma': float(long_call.gamma) if long_call.gamma else None,
                            'theta': float(long_call.theta) if long_call.theta else None,
                            'vega': float(long_call.vega) if long_call.vega else None,
                            'iv': float(long_call.iv) if long_call.iv else None,
                            'bid': float(long_call.bid) if long_call.bid else None,
                            'ask': float(long_call.ask) if long_call.ask else None,
                            'mid': float(long_call.mid) if long_call.mid else None,
                            'last': float(long_call.last) if long_call.last else None,
                            'volume': long_call.volume,
                            'open_interest': long_call.open_interest,
                            'bid_size': long_call.bid_size,
                            'ask_size': long_call.ask_size
                        }
                        
                        # Short call option details
                        short_call = analysis.short_call
                        short_data = {
                            'option_symbol': short_call.option_symbol,
                            'strike': float(short_call.strike),
                            'expiration': short_call.expiration.isoformat(),
                            'dte': short_call.dte,
                            'delta': float(short_call.delta) if short_call.delta else None,
                            'gamma': float(short_call.gamma) if short_call.gamma else None,
                            'theta': float(short_call.theta) if short_call.theta else None,
                            'vega': float(short_call.vega) if short_call.vega else None,
                            'iv': float(short_call.iv) if short_call.iv else None,
                            'bid': float(short_call.bid) if short_call.bid else None,
                            'ask': float(short_call.ask) if short_call.ask else None,
                            'mid': float(short_call.mid) if short_call.mid else None,
                            'last': float(short_call.last) if short_call.last else None,
                            'volume': short_call.volume,
                            'open_interest': short_call.open_interest,
                            'bid_size': short_call.bid_size,
                            'ask_size': short_call.ask_size
                        }
                    else:
                        # Fallback if no analysis available
                        net_debit = credit_received = max_profit = max_loss = breakeven = risk_reward_ratio = 0
                        leaps_data = short_data = {}
                    
                    discovered_at = opp.discovered_at.isoformat() if opp.discovered_at else datetime.now().isoformat()
                    
                elif isinstance(opp, dict):
                    # Handle dictionary format (from JSON exports)
                    symbol = opp.get('symbol', '')
                    underlying_price = opp.get('underlying_price', 0)
                    # Map total_score to pmcc_score for JSON exports
                    pmcc_score = opp.get('pmcc_score', opp.get('total_score', 0))
                    liquidity_score = opp.get('liquidity_score', 0)
                    net_debit = opp.get('net_debit', 0)
                    credit_received = opp.get('credit_received', 0)
                    max_profit = opp.get('max_profit', 0)
                    max_loss = opp.get('max_loss', 0)
                    breakeven = opp.get('breakeven', 0)
                    risk_reward_ratio = opp.get('risk_reward_ratio', 0)
                    
                    # Extract complete options data from JSON export
                    long_call_raw = opp.get('long_call', {})
                    short_call_raw = opp.get('short_call', {})
                    
                    # Create comprehensive options data with ALL Greeks
                    leaps_data = {
                        'option_symbol': long_call_raw.get('option_symbol', ''),
                        'strike': long_call_raw.get('strike', 0),
                        'expiration': long_call_raw.get('expiration', ''),
                        'dte': long_call_raw.get('dte', 0),
                        # ALL Greeks, not just delta
                        'delta': long_call_raw.get('delta'),
                        'gamma': long_call_raw.get('gamma'),
                        'theta': long_call_raw.get('theta'),
                        'vega': long_call_raw.get('vega'),
                        'iv': long_call_raw.get('iv'),
                        # Market data
                        'bid': long_call_raw.get('bid'),
                        'ask': long_call_raw.get('ask'),
                        'mid': long_call_raw.get('mid'),
                        'last': long_call_raw.get('last'),
                        'volume': long_call_raw.get('volume'),
                        'open_interest': long_call_raw.get('open_interest'),
                        'bid_size': long_call_raw.get('bid_size'),
                        'ask_size': long_call_raw.get('ask_size'),
                        # Additional calculated values
                        'intrinsic_value': long_call_raw.get('intrinsic_value'),
                        'extrinsic_value': long_call_raw.get('extrinsic_value'),
                        'underlying_price': long_call_raw.get('underlying_price'),
                        'in_the_money': long_call_raw.get('in_the_money'),
                        'moneyness': long_call_raw.get('moneyness'),
                        'is_leaps': long_call_raw.get('is_leaps')
                    }
                    
                    short_data = {
                        'option_symbol': short_call_raw.get('option_symbol', ''),
                        'strike': short_call_raw.get('strike', 0),
                        'expiration': short_call_raw.get('expiration', ''),
                        'dte': short_call_raw.get('dte', 0),
                        # ALL Greeks, not just delta
                        'delta': short_call_raw.get('delta'),
                        'gamma': short_call_raw.get('gamma'),
                        'theta': short_call_raw.get('theta'),
                        'vega': short_call_raw.get('vega'),
                        'iv': short_call_raw.get('iv'),
                        # Market data
                        'bid': short_call_raw.get('bid'),
                        'ask': short_call_raw.get('ask'),
                        'mid': short_call_raw.get('mid'),
                        'last': short_call_raw.get('last'),
                        'volume': short_call_raw.get('volume'),
                        'open_interest': short_call_raw.get('open_interest'),
                        'bid_size': short_call_raw.get('bid_size'),
                        'ask_size': short_call_raw.get('ask_size'),
                        # Additional calculated values
                        'intrinsic_value': short_call_raw.get('intrinsic_value'),
                        'extrinsic_value': short_call_raw.get('extrinsic_value'),
                        'underlying_price': short_call_raw.get('underlying_price'),
                        'in_the_money': short_call_raw.get('in_the_money'),
                        'moneyness': short_call_raw.get('moneyness'),
                        'is_leaps': short_call_raw.get('is_leaps')
                    }
                    
                    discovered_at = opp.get('discovered_at', datetime.now().isoformat())
                else:
                    logger.warning(f"Unsupported opportunity format: {type(opp)}")
                    continue
                
                if not symbol:
                    logger.warning("Opportunity missing symbol, skipping")
                    continue
                
                symbols_analyzed.add(symbol)
                
                # Create comprehensive prepared opportunity with all available data
                prepared_opp = {
                    'symbol': symbol,
                    'underlying_price': underlying_price,
                    'pmcc_score': pmcc_score,
                    'liquidity_score': liquidity_score,
                    
                    # Comprehensive strategy details
                    'strategy_details': {
                        'net_debit': net_debit,
                        'credit_received': credit_received,
                        'max_profit': max_profit,
                        'max_loss': max_loss,
                        'breakeven_price': breakeven,
                        'risk_reward_ratio': risk_reward_ratio,
                        'strategy_type': 'Poor_Mans_Covered_Call'
                    },
                    
                    # Complete LEAPS option details with ALL Greeks and market data
                    'leaps_option': leaps_data,
                    
                    # Complete short call option details with ALL Greeks and market data
                    'short_option': short_data,
                    
                    # Analysis metadata
                    'analysis_timestamp': discovered_at,
                    'total_score': pmcc_score,
                    
                    # Include risk metrics if available from dictionaries
                    'risk_metrics': opp.get('risk_metrics', {}) if isinstance(opp, dict) else None,
                    
                    # Include complete option chain data if available
                    'complete_option_chain': opp.get('complete_option_chain', {}) if isinstance(opp, dict) else None
                }
                
                prepared_opportunities.append(prepared_opp)
                
            except Exception as e:
                logger.warning(f"Error preparing opportunity data for {getattr(opp, 'symbol', opp.get('symbol', 'unknown')) if hasattr(opp, 'symbol') or isinstance(opp, dict) else 'unknown'}: {e}")
                continue
        
        # Calculate market context metrics
        if prepared_opportunities:
            scores = [opp['pmcc_score'] for opp in prepared_opportunities]
            underlying_prices = [opp['underlying_price'] for opp in prepared_opportunities]
            
            market_context = {
                'total_opportunities': len(prepared_opportunities),
                'unique_symbols': len(symbols_analyzed),
                'score_statistics': {
                    'average_pmcc_score': round(sum(scores) / len(scores), 2) if scores else 0,
                    'highest_pmcc_score': max(scores) if scores else 0,
                    'lowest_pmcc_score': min(scores) if scores else 0
                },
                'price_statistics': {
                    'average_underlying_price': round(sum(underlying_prices) / len(underlying_prices), 2) if underlying_prices else 0,
                    'price_range': {
                        'min': min(underlying_prices) if underlying_prices else 0,
                        'max': max(underlying_prices) if underlying_prices else 0
                    }
                }
            }
        else:
            market_context = {}
        
        # Create final prepared data structure
        prepared_data = {
            'opportunities': prepared_opportunities,
            'market_context': market_context,
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'opportunity_count': len(prepared_opportunities),
                'symbols_analyzed': sorted(list(symbols_analyzed)),
                'prepared_for_claude': True,
                'preparation_version': '1.0'
            }
        }
        
        logger.info(f"Successfully prepared {len(prepared_opportunities)} opportunities for Claude analysis")
        return prepared_data
    
    def integrate_claude_analysis(self, opportunities: List[Dict[str, Any]], claude_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Integrate Claude AI analysis results with PMCC opportunities.
        
        This method takes existing PMCC opportunities and a Claude AI analysis response,
        then merges them to create enhanced opportunity data with AI insights.
        
        Args:
            opportunities: List of PMCC opportunity dictionaries
            claude_response: Claude AI analysis response dictionary
            
        Returns:
            List of integrated opportunities with AI insights
        """
        logger.info(f"Integrating Claude analysis with {len(opportunities)} opportunities")
        
        if not opportunities:
            logger.warning("No opportunities provided for Claude integration")
            return []
        
        if not claude_response:
            logger.warning("No Claude response provided for integration")
            return opportunities  # Return original opportunities if no Claude data
        
        integrated_opportunities = []
        
        # Extract Claude's top picks for quick lookup
        top_picks = claude_response.get('top_picks', [])
        top_picks_lookup = {pick.get('symbol', ''): pick for pick in top_picks}
        
        for opp in opportunities:
            try:
                symbol = opp.get('symbol', '')
                if not symbol:
                    logger.warning("Opportunity missing symbol, skipping integration")
                    continue
                
                # Start with original opportunity data
                integrated_opp = {**opp}  # Copy original data
                
                # Add Claude AI insights if available for this symbol
                claude_pick = top_picks_lookup.get(symbol)
                if claude_pick:
                    # Symbol was analyzed by Claude - add AI insights
                    integrated_opp.update({
                        'claude_analyzed': True,
                        'ai_score': claude_pick.get('ai_score', 0),
                        'ai_reasoning': claude_pick.get('reasoning', ''),
                        'claude_recommendation': claude_pick.get('recommendation', 'neutral'),
                        
                        # Calculate combined score (weighted average)
                        'combined_score': self._calculate_combined_score(
                            opp.get('pmcc_score', 0), 
                            claude_pick.get('ai_score', 0)
                        ),
                        
                        # Add market context
                        'market_context': {
                            'market_outlook': claude_response.get('market_outlook', ''),
                            'analysis_summary': claude_response.get('summary', '')
                        }
                    })
                else:
                    # Symbol not specifically analyzed by Claude
                    integrated_opp.update({
                        'claude_analyzed': False,
                        'ai_score': None,
                        'ai_reasoning': 'Not specifically analyzed by Claude',
                        'claude_recommendation': 'neutral',
                        'combined_score': opp.get('pmcc_score', 0),  # Use original score
                        
                        # Still add general market context
                        'market_context': {
                            'market_outlook': claude_response.get('market_outlook', ''),
                            'analysis_summary': claude_response.get('summary', '')
                        }
                    })
                
                # Add integration metadata
                integrated_opp['integration_metadata'] = {
                    'integrated_at': datetime.now().isoformat(),
                    'claude_response_included': bool(claude_pick),
                    'integration_version': '1.0'
                }
                
                integrated_opportunities.append(integrated_opp)
                
            except Exception as e:
                logger.warning(f"Error integrating Claude analysis for {opp.get('symbol', 'unknown')}: {e}")
                # Include original opportunity even if integration failed
                integrated_opportunities.append(opp)
                continue
        
        # Sort by combined score (or original score if no Claude data)
        integrated_opportunities.sort(
            key=lambda x: x.get('combined_score', x.get('pmcc_score', 0)), 
            reverse=True
        )
        
        logger.info(f"Successfully integrated Claude analysis for {len(integrated_opportunities)} opportunities")
        return integrated_opportunities
    
    def _calculate_combined_score(self, pmcc_score: float, ai_score: float, 
                                 pmcc_weight: Optional[float] = None, ai_weight: Optional[float] = None) -> float:
        """
        Calculate combined score from PMCC and AI scores.
        
        Args:
            pmcc_score: Original PMCC analysis score
            ai_score: Claude AI analysis score
            pmcc_weight: Weight for PMCC score (uses settings if not provided)
            ai_weight: Weight for AI score (uses settings if not provided)
            
        Returns:
            Combined weighted score
        """
        if ai_score is None or ai_score == 0:
            return pmcc_score
        
        # Use provided weights or fall back to settings or defaults
        if pmcc_weight is None:
            pmcc_weight = self.settings.traditional_pmcc_weight if self.settings else 0.6
        if ai_weight is None:
            ai_weight = self.settings.ai_analysis_weight if self.settings else 0.4
        
        # Use configurable weights for scoring combination
        return (pmcc_score * pmcc_weight) + (ai_score * ai_weight)
    
    async def analyze_single_opportunity_with_claude(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        claude_provider,
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single PMCC opportunity using Claude AI.
        
        This method takes one PMCC opportunity with its complete data package
        and returns Claude's analysis with a 0-100 score.
        
        Args:
            opportunity_data: Single PMCC opportunity data
            enhanced_stock_data: Complete enhanced stock data package (8 EODHD data types)
            claude_provider: Claude provider instance for API calls
            market_context: Optional market context information
            
        Returns:
            Dictionary with Claude analysis integrated with original opportunity data
        """
        symbol = opportunity_data.get('symbol', 'Unknown')
        logger.info(f"Analyzing single opportunity with Claude: {symbol}")
        
        try:
            # Call Claude provider for single opportunity analysis
            response = await claude_provider.analyze_single_pmcc_opportunity(
                opportunity_data, enhanced_stock_data, market_context
            )
            
            if not response.is_success:
                logger.error(f"Claude analysis failed for {symbol}: {response.error}")
                return self._create_failed_analysis_result(opportunity_data)
            
            claude_analysis = response.data
            
            # Integrate Claude's analysis with the original opportunity
            integrated_opportunity = self._integrate_single_claude_analysis(
                opportunity_data, claude_analysis
            )
            
            # Update statistics
            self._stats['total_analyses'] += 1
            self._stats['successful_analyses'] += 1
            self._stats['opportunities_analyzed'] += 1
            
            if claude_analysis.get('confidence_level', 0) >= 75:
                self._stats['high_confidence_recommendations'] += 1
            
            logger.info(f"Successfully analyzed {symbol} with Claude (score: {claude_analysis.get('pmcc_score', 'N/A')})")
            return integrated_opportunity
            
        except Exception as e:
            logger.error(f"Error in single opportunity Claude analysis for {symbol}: {e}")
            self._stats['total_analyses'] += 1
            return self._create_failed_analysis_result(opportunity_data)
    
    def _integrate_single_claude_analysis(
        self,
        opportunity_data: Dict[str, Any], 
        claude_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Integrate Claude AI analysis with a single PMCC opportunity.
        
        Args:
            opportunity_data: Original PMCC opportunity data
            claude_analysis: Claude's analysis response
            
        Returns:
            Dictionary with integrated Claude insights
        """
        # Start with original opportunity data
        integrated_opportunity = {**opportunity_data}
        
        # Extract Claude scores and insights
        claude_score = claude_analysis.get('pmcc_score', 0)
        original_pmcc_score = opportunity_data.get('pmcc_score', opportunity_data.get('total_score', 0))
        
        # Calculate combined score using configurable weights
        pmcc_weight = self.settings.traditional_pmcc_weight if self.settings else 0.6
        ai_weight = self.settings.ai_analysis_weight if self.settings else 0.4
        combined_score = (original_pmcc_score * pmcc_weight) + (claude_score * ai_weight)
        
        # Add Claude analysis data
        integrated_opportunity.update({
            # Claude analysis results
            'claude_analyzed': True,
            'claude_score': claude_score,
            'claude_analysis_summary': claude_analysis.get('analysis_summary', ''),
            'claude_detailed_reasoning': claude_analysis.get('detailed_reasoning', ''),
            'claude_recommendation': claude_analysis.get('recommendation', 'neutral'),
            'claude_confidence': claude_analysis.get('confidence_level', 0),
            
            # Combined scoring
            'combined_score': combined_score,
            'ai_enhanced': True,
            
            # Detailed Claude scores breakdown
            'claude_scores_breakdown': {
                'risk_score': claude_analysis.get('risk_score', 0),
                'fundamental_score': claude_analysis.get('fundamental_score', 0),
                'technical_score': claude_analysis.get('technical_score', 0),
                'calendar_score': claude_analysis.get('calendar_score', 0),
                'strategy_score': claude_analysis.get('strategy_score', 0)
            },
            
            # Claude insights
            'ai_insights': {
                'key_strengths': claude_analysis.get('key_strengths', []),
                'key_risks': claude_analysis.get('key_risks', []),
                'profit_probability': claude_analysis.get('profit_probability', 0),
                'early_assignment_risk': claude_analysis.get('early_assignment_risk', 'unknown'),
                'optimal_management': claude_analysis.get('optimal_management', '')
            },
            
            # Analysis metadata
            'claude_analysis_metadata': {
                'analyzed_at': claude_analysis.get('analysis_timestamp', datetime.now().isoformat()),
                'model_used': claude_analysis.get('model_used', 'claude-3-5-sonnet'),
                'processing_time_ms': claude_analysis.get('processing_time_ms', 0),
                'usage': claude_analysis.get('usage', {}),
                'provider_metadata': claude_analysis.get('provider_metadata', {})
            }
        })
        
        return integrated_opportunity
    
    def _create_failed_analysis_result(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a result structure for failed Claude analysis.
        
        Args:
            opportunity_data: Original opportunity data
            
        Returns:
            Dictionary with failed analysis markers
        """
        return {
            **opportunity_data,
            'claude_analyzed': False,
            'claude_score': None,
            'claude_analysis_summary': 'Analysis failed',
            'claude_detailed_reasoning': 'Claude analysis could not be completed',
            'claude_recommendation': 'neutral',
            'claude_confidence': 0,
            'combined_score': opportunity_data.get('pmcc_score', opportunity_data.get('total_score', 0)),
            'ai_enhanced': False,
            'claude_scores_breakdown': {
                'risk_score': 0,
                'fundamental_score': 0,
                'technical_score': 0,
                'calendar_score': 0,
                'strategy_score': 0
            },
            'ai_insights': {
                'key_strengths': [],
                'key_risks': ['Analysis unavailable'],
                'profit_probability': 0,
                'early_assignment_risk': 'unknown',
                'optimal_management': 'Standard PMCC management applies'
            },
            'claude_analysis_metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'analysis_failed': True
            }
        }
    
    async def analyze_opportunities_individually(
        self,
        opportunities: List[Dict[str, Any]],
        enhanced_stock_data_lookup: Dict[str, Dict[str, Any]],
        claude_provider,
        market_context: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple PMCC opportunities individually using Claude.
        
        This method processes each opportunity separately to provide focused analysis.
        Includes rate limiting and error handling for batch processing.
        
        Args:
            opportunities: List of PMCC opportunities to analyze
            enhanced_stock_data_lookup: Lookup dict of symbol -> enhanced stock data
            claude_provider: Claude provider instance
            market_context: Optional market context
            max_concurrent: Maximum concurrent API calls to Claude
            
        Returns:
            List of opportunities with individual Claude analysis
        """
        logger.info(f"Starting individual Claude analysis for {len(opportunities)} opportunities")
        
        if not opportunities:
            logger.warning("No opportunities provided for individual Claude analysis")
            return []
        
        import asyncio
        
        # Create semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_single_with_semaphore(opportunity):
            """Analyze single opportunity with concurrency control."""
            async with semaphore:
                symbol = opportunity.get('symbol', 'Unknown')
                enhanced_data = enhanced_stock_data_lookup.get(symbol)
                
                if not enhanced_data:
                    logger.warning(f"No enhanced stock data found for {symbol}")
                    return self._create_failed_analysis_result(opportunity)
                
                return await self.analyze_single_opportunity_with_claude(
                    opportunity, enhanced_data, claude_provider, market_context
                )
        
        # Process all opportunities concurrently (with semaphore limiting)
        try:
            analyzed_opportunities = await asyncio.gather(
                *[analyze_single_with_semaphore(opp) for opp in opportunities],
                return_exceptions=True
            )
            
            # Handle any exceptions that occurred
            final_results = []
            for i, result in enumerate(analyzed_opportunities):
                if isinstance(result, Exception):
                    logger.error(f"Exception analyzing opportunity {i}: {result}")
                    final_results.append(self._create_failed_analysis_result(opportunities[i]))
                else:
                    final_results.append(result)
            
            # Sort by combined score (highest first)
            final_results.sort(
                key=lambda x: x.get('combined_score', x.get('pmcc_score', 0)), 
                reverse=True
            )
            
            # Log summary
            successful_analyses = len([r for r in final_results if r.get('claude_analyzed', False)])
            logger.info(f"Individual Claude analysis completed: {successful_analyses}/{len(opportunities)} successful")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in individual Claude analysis batch processing: {e}")
            # Return original opportunities with failed analysis markers
            return [self._create_failed_analysis_result(opp) for opp in opportunities]