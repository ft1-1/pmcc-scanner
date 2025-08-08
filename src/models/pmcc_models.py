"""
Data models for PMCC (Poor Man's Covered Call) strategy analysis.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.models.api_models import OptionContract, StockQuote


@dataclass
class RiskMetrics:
    """Risk metrics for PMCC position."""
    max_loss: Decimal  # Maximum possible loss
    max_profit: Optional[Decimal]  # Maximum profit if applicable
    breakeven: Decimal  # Breakeven price at expiration
    probability_of_profit: Optional[Decimal]  # Estimated probability
    
    # Greeks for the overall position
    net_delta: Optional[Decimal] = None
    net_gamma: Optional[Decimal] = None
    net_theta: Optional[Decimal] = None
    net_vega: Optional[Decimal] = None
    
    # Risk ratios
    risk_reward_ratio: Optional[Decimal] = None
    capital_at_risk: Optional[Decimal] = None  # As percentage of account


@dataclass
class PMCCAnalysis:
    """Analysis of a PMCC position."""
    long_call: OptionContract  # LEAPS call
    short_call: OptionContract  # Short-term call
    underlying: StockQuote
    
    # Position details
    net_debit: Decimal  # Cost to establish position
    credit_received: Optional[Decimal] = None  # Credit from short call
    
    # Risk analysis
    risk_metrics: RiskMetrics = None
    
    # Position health indicators
    liquidity_score: Optional[Decimal] = None  # 0-100 score
    iv_rank: Optional[Decimal] = None  # IV percentile
    
    # Analysis metadata
    analyzed_at: datetime = None
    
    @property
    def days_to_short_expiration(self) -> Optional[int]:
        """Days until short call expires."""
        return self.short_call.dte
    
    @property
    def days_to_long_expiration(self) -> Optional[int]:
        """Days until LEAPS expires."""
        return self.long_call.dte
    
    @property
    def strike_width(self) -> Decimal:
        """Width between long and short strikes."""
        return self.short_call.strike - self.long_call.strike
    
    @property
    def is_valid_pmcc(self) -> bool:
        """Check if this represents a valid PMCC structure."""
        return (
            self.long_call.side.value == "call" and
            self.short_call.side.value == "call" and
            self.long_call.strike < self.short_call.strike and
            (self.long_call.dte or 0) > (self.short_call.dte or 0)
        )
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate risk metrics for this PMCC position."""
        if not self.is_valid_pmcc:
            raise ValueError("Invalid PMCC structure")
        
        # Max loss is the net debit paid (cost to establish)
        max_loss = self.net_debit
        
        # Max profit occurs when short call expires ITM at short strike
        # and we can sell the LEAPS for intrinsic value
        max_profit = None
        if self.long_call.strike and self.short_call.strike:
            intrinsic_at_short_strike = self.short_call.strike - self.long_call.strike
            max_profit = intrinsic_at_short_strike - self.net_debit
        
        # Breakeven is long strike + net debit
        breakeven = self.long_call.strike + self.net_debit
        
        # Calculate net Greeks
        net_delta = None
        net_gamma = None
        net_theta = None
        net_vega = None
        
        if (self.long_call.delta is not None and 
            self.short_call.delta is not None):
            net_delta = self.long_call.delta - self.short_call.delta
        
        if (self.long_call.gamma is not None and 
            self.short_call.gamma is not None):
            net_gamma = self.long_call.gamma - self.short_call.gamma
        
        if (self.long_call.theta is not None and 
            self.short_call.theta is not None):
            net_theta = self.long_call.theta - self.short_call.theta
        
        if (self.long_call.vega is not None and 
            self.short_call.vega is not None):
            net_vega = self.long_call.vega - self.short_call.vega
        
        # Calculate risk/reward ratio
        risk_reward_ratio = None
        if max_profit and max_loss > 0:
            risk_reward_ratio = max_profit / max_loss
        
        return RiskMetrics(
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=breakeven,
            probability_of_profit=None,  # Would need statistical model
            net_delta=net_delta,
            net_gamma=net_gamma,
            net_theta=net_theta,
            net_vega=net_vega,
            risk_reward_ratio=risk_reward_ratio
        )
    
    def calculate_liquidity_score(self) -> Decimal:
        """Calculate liquidity score (0-100) based on bid-ask spreads and volume."""
        score = Decimal('0')
        factors = 0
        
        # Factor 1: Bid-ask spread on LEAPS (weight: 40%)
        if (self.long_call.bid and self.long_call.ask and 
            self.long_call.mid and self.long_call.mid > 0):
            spread_pct = (self.long_call.ask - self.long_call.bid) / self.long_call.mid * 100
            # Lower spread is better
            spread_score = max(0, 100 - spread_pct * 10)  # Each 1% spread reduces score by 10
            score += Decimal(str(spread_score)) * Decimal('0.4')
            factors += 1
        
        # Factor 2: Bid-ask spread on short call (weight: 30%)
        if (self.short_call.bid and self.short_call.ask and 
            self.short_call.mid and self.short_call.mid > 0):
            spread_pct = (self.short_call.ask - self.short_call.bid) / self.short_call.mid * 100
            spread_score = max(0, 100 - spread_pct * 10)
            score += Decimal(str(spread_score)) * Decimal('0.3')
            factors += 1
        
        # Factor 3: Volume and open interest (weight: 30%)
        volume_score = Decimal('0')
        if self.long_call.volume and self.short_call.volume:
            # Score based on combined volume
            total_volume = self.long_call.volume + self.short_call.volume
            # Logarithmic scale for volume scoring
            import math
            volume_score = min(100, math.log10(max(1, total_volume)) * 25)
            volume_score = Decimal(str(volume_score))
        
        if self.long_call.open_interest and self.short_call.open_interest:
            total_oi = self.long_call.open_interest + self.short_call.open_interest
            import math
            oi_score = min(100, math.log10(max(1, total_oi)) * 25)
            volume_score = (volume_score + Decimal(str(oi_score))) / 2
        
        score += volume_score * Decimal('0.3')
        factors += 1
        
        if factors > 0:
            return min(100, max(0, score))
        
        return Decimal('0')


@dataclass
class PMCCCandidate:
    """A candidate PMCC position identified by the scanner."""
    symbol: str
    underlying_price: Decimal
    analysis: PMCCAnalysis
    
    # Screening criteria scores
    liquidity_score: Decimal
    volatility_score: Optional[Decimal] = None
    technical_score: Optional[Decimal] = None
    fundamental_score: Optional[Decimal] = None
    
    # Overall ranking
    total_score: Optional[Decimal] = None
    rank: Optional[int] = None
    
    # Complete option chain data for AI analysis
    complete_option_chain: Optional['OptionChain'] = None
    
    # AI Analysis Results (added to preserve Claude AI insights)
    ai_insights: Optional[Dict[str, Any]] = None
    claude_score: Optional[float] = None
    combined_score: Optional[float] = None
    claude_reasoning: Optional[str] = None
    ai_recommendation: Optional[str] = None
    claude_confidence: Optional[float] = None
    ai_analysis_timestamp: Optional[datetime] = None
    
    # Metadata
    discovered_at: datetime = None
    
    @property
    def is_profitable(self) -> bool:
        """Check if the PMCC has positive expected profit."""
        if self.analysis.risk_metrics and self.analysis.risk_metrics.max_profit:
            return self.analysis.risk_metrics.max_profit > 0
        return False
    
    @property
    def risk_reward_ratio(self) -> Optional[Decimal]:
        """Get risk/reward ratio."""
        if self.analysis.risk_metrics:
            return self.analysis.risk_metrics.risk_reward_ratio
        return None
    
    def calculate_total_score(self, weights: Optional[dict] = None) -> Decimal:
        """
        Calculate total weighted score for ranking.
        
        Args:
            weights: Dictionary of weights for different scores
                   Default: {'liquidity': 0.4, 'volatility': 0.3, 'technical': 0.2, 'fundamental': 0.1}
        """
        if weights is None:
            weights = {
                'liquidity': 0.4,
                'volatility': 0.3,
                'technical': 0.2,
                'fundamental': 0.1
            }
        
        total = Decimal('0')
        total_weight = Decimal('0')
        
        if self.liquidity_score is not None:
            total += self.liquidity_score * Decimal(str(weights.get('liquidity', 0)))
            total_weight += Decimal(str(weights.get('liquidity', 0)))
        
        if self.volatility_score is not None:
            total += self.volatility_score * Decimal(str(weights.get('volatility', 0)))
            total_weight += Decimal(str(weights.get('volatility', 0)))
        
        if self.technical_score is not None:
            total += self.technical_score * Decimal(str(weights.get('technical', 0)))
            total_weight += Decimal(str(weights.get('technical', 0)))
        
        if self.fundamental_score is not None:
            total += self.fundamental_score * Decimal(str(weights.get('fundamental', 0)))
            total_weight += Decimal(str(weights.get('fundamental', 0)))
        
        if total_weight > 0:
            self.total_score = total / total_weight
            return self.total_score
        
        return Decimal('0')
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization with complete option data."""
        def safe_float(value):
            """Safely convert Decimal to float."""
            return float(value) if value is not None else None
        
        def option_to_dict(option: OptionContract) -> dict:
            """Convert option contract to complete dictionary."""
            return {
                # Basic contract info
                'option_symbol': option.option_symbol,
                'underlying': option.underlying,
                'strike': safe_float(option.strike),
                'expiration': option.expiration.isoformat(),
                'side': option.side.value,
                'dte': option.dte,
                
                # Pricing data
                'bid': safe_float(option.bid),
                'ask': safe_float(option.ask),
                'mid': safe_float(option.mid),
                'last': safe_float(option.last),
                'spread': safe_float(option.spread),
                'spread_percentage': safe_float(option.spread_percentage),
                
                # Size data
                'bid_size': option.bid_size,
                'ask_size': option.ask_size,
                
                # Market data
                'volume': option.volume,
                'open_interest': option.open_interest,
                
                # ALL Greeks and analytics
                'delta': safe_float(option.delta),
                'gamma': safe_float(option.gamma),
                'theta': safe_float(option.theta),
                'vega': safe_float(option.vega),
                'iv': safe_float(option.iv),
                
                # Additional calculated values
                'intrinsic_value': safe_float(option.intrinsic_value),
                'extrinsic_value': safe_float(option.extrinsic_value),
                'underlying_price': safe_float(option.underlying_price),
                'in_the_money': option.in_the_money,
                'moneyness': option.moneyness,
                'is_leaps': option.is_leaps,
                
                # Time data
                'first_traded': option.first_traded.isoformat() if option.first_traded else None,
                'updated': option.updated.isoformat() if option.updated else None
            }
        
        # Create comprehensive result dictionary
        result = {
            # Basic position info
            'symbol': self.symbol,
            'underlying_price': safe_float(self.underlying_price),
            
            # Complete option contract data
            'long_call': option_to_dict(self.analysis.long_call),
            'short_call': option_to_dict(self.analysis.short_call),
            
            # Position economics
            'net_debit': safe_float(self.analysis.net_debit),
            'credit_received': safe_float(self.analysis.credit_received),
            
            # Risk metrics with ALL Greeks
            'risk_metrics': {
                'max_loss': safe_float(self.analysis.risk_metrics.max_loss) if self.analysis.risk_metrics else None,
                'max_profit': safe_float(self.analysis.risk_metrics.max_profit) if self.analysis.risk_metrics else None,
                'breakeven': safe_float(self.analysis.risk_metrics.breakeven) if self.analysis.risk_metrics else None,
                'probability_of_profit': safe_float(self.analysis.risk_metrics.probability_of_profit) if self.analysis.risk_metrics else None,
                'capital_at_risk': safe_float(self.analysis.risk_metrics.capital_at_risk) if self.analysis.risk_metrics else None,
                'risk_reward_ratio': safe_float(self.analysis.risk_metrics.risk_reward_ratio) if self.analysis.risk_metrics else None,
                # Net position Greeks
                'net_delta': safe_float(self.analysis.risk_metrics.net_delta) if self.analysis.risk_metrics else None,
                'net_gamma': safe_float(self.analysis.risk_metrics.net_gamma) if self.analysis.risk_metrics else None,
                'net_theta': safe_float(self.analysis.risk_metrics.net_theta) if self.analysis.risk_metrics else None,
                'net_vega': safe_float(self.analysis.risk_metrics.net_vega) if self.analysis.risk_metrics else None
            },
            
            # Position health metrics
            'liquidity_score': safe_float(self.liquidity_score),
            'iv_rank': safe_float(self.analysis.iv_rank),
            
            # Position validation and characteristics
            'is_valid_pmcc': self.analysis.is_valid_pmcc,
            'is_profitable': self.is_profitable,
            'days_to_short_expiration': self.analysis.days_to_short_expiration,
            'days_to_long_expiration': self.analysis.days_to_long_expiration,
            'strike_width': safe_float(self.analysis.strike_width),
            
            # Scoring and ranking
            'volatility_score': safe_float(self.volatility_score),
            'technical_score': safe_float(self.technical_score),
            'fundamental_score': safe_float(self.fundamental_score),
            'total_score': safe_float(self.total_score),
            'rank': self.rank,
            
            # AI Analysis Results (preserving Claude AI insights)
            'ai_insights': self.ai_insights,
            'claude_score': self.claude_score,
            'combined_score': self.combined_score,
            'claude_reasoning': self.claude_reasoning,
            'ai_recommendation': self.ai_recommendation,
            'claude_confidence': self.claude_confidence,
            'ai_analysis_timestamp': self.ai_analysis_timestamp.isoformat() if self.ai_analysis_timestamp else None,
            
            # Complete option chain data for AI analysis
            'complete_option_chain': {
                'underlying': self.complete_option_chain.underlying,
                'underlying_price': safe_float(self.complete_option_chain.underlying_price),
                'updated': self.complete_option_chain.updated.isoformat() if self.complete_option_chain.updated else None,
                'contracts': [option_to_dict(contract) for contract in self.complete_option_chain.contracts]
            } if self.complete_option_chain else None,
            
            # Analysis metadata
            'analyzed_at': self.analysis.analyzed_at.isoformat() if self.analysis.analyzed_at else None,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None
        }
        
        return result