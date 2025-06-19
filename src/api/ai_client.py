import google.generativeai as genai
import asyncio
import json
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.config import settings
from core.models import Market, TradingSignal, MarketAnalysis, TradeSide

logger = logging.getLogger(__name__)

class AIAnalyst:
    def __init__(self):
        self.has_api = settings.has_google_api
        self.model = None
        
        if self.has_api:
            try:
                genai.configure(api_key=settings.google_api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Google AI (Gemini Pro) initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google AI: {e}. Using local fallback.")
                self.has_api = False
        else:
            logger.info("No Google API key found. Using local analysis fallback.")
    
    async def analyze_market(self, market: Dict) -> MarketAnalysis:
        """Analyze a market and provide insights"""
        if self.has_api:
            try:
                return await self._analyze_with_ai(market)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}. Using fallback analysis.")
                return self._fallback_analysis(market)
        else:
            return self._fallback_analysis(market)
    
    async def _analyze_with_ai(self, market: Dict) -> MarketAnalysis:
        """Use Google AI for market analysis"""
        prompt = f"""
        Analyze this prediction market and provide trading insights:
        
        Market: {market['question']}
        Category: {market.get('category', 'Unknown')}
        Current Yes Price: ${market['yes_price']:.3f}
        Current No Price: ${market['no_price']:.3f}
        Volume: ${market['volume']:,.0f}
        Liquidity: ${market['liquidity']:,.0f}
        End Date: {market.get('end_date', 'Unknown')}
        
        Please provide:
        1. Fair value estimate (0.0-1.0)
        2. Volatility assessment (0.0-1.0)
        3. Trend direction (bullish/bearish/neutral)
        4. Confidence level (0.0-1.0)
        5. Key factors affecting the outcome
        6. Support and resistance levels
        
        Format your response as JSON with these exact keys:
        {{
            "fair_value": 0.55,
            "volatility": 0.3,
            "trend": "bullish",
            "confidence": 0.7,
            "key_factors": ["factor1", "factor2", "factor3"],
            "price_targets": {{"support": 0.45, "resistance": 0.65}}
        }}
        """
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            # Extract JSON from response
            response_text = response.text
            
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                analysis_data = json.loads(json_str)
                
                return MarketAnalysis(
                    market_id=market['id'],
                    fair_value=analysis_data.get('fair_value', market['yes_price']),
                    volatility=analysis_data.get('volatility', 0.2),
                    trend=analysis_data.get('trend', 'neutral'),
                    confidence=analysis_data.get('confidence', 0.5),
                    key_factors=analysis_data.get('key_factors', ['Market dynamics']),
                    price_targets=analysis_data.get('price_targets', {
                        'support': market['yes_price'] * 0.9,
                        'resistance': market['yes_price'] * 1.1
                    })
                )
            else:
                raise ValueError("Could not parse JSON from AI response")
                
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            raise
    
    def _fallback_analysis(self, market: Dict) -> MarketAnalysis:
        """Local fallback analysis using heuristics"""
        yes_price = market['yes_price']
        volume = market['volume']
        liquidity = market['liquidity']
        
        # Simple heuristic analysis
        # Higher volume suggests more conviction
        volume_factor = min(volume / 1000000, 1.0)  # Normalize to 1M
        
        # Liquidity affects volatility
        liquidity_factor = min(liquidity / 100000, 1.0)  # Normalize to 100K
        
        # Price extremes suggest higher volatility
        price_extremity = abs(yes_price - 0.5) * 2
        
        # Calculate metrics
        volatility = max(0.1, min(0.8, (1 - liquidity_factor) * 0.5 + price_extremity * 0.3))
        
        # Trend based on price position
        if yes_price > 0.6:
            trend = "bullish"
        elif yes_price < 0.4:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Confidence based on volume and liquidity
        confidence = (volume_factor * 0.6 + liquidity_factor * 0.4)
        
        # Generate key factors based on category
        category = market.get('category', 'General').lower()
        key_factors = self._generate_key_factors(category, yes_price)
        
        # Simple support/resistance
        support = max(0.01, yes_price - volatility * 0.5)
        resistance = min(0.99, yes_price + volatility * 0.5)
        
        return MarketAnalysis(
            market_id=market['id'],
            fair_value=yes_price,  # Use current price as fair value baseline
            volatility=volatility,
            trend=trend,
            confidence=confidence,
            key_factors=key_factors,
            price_targets={"support": round(support, 3), "resistance": round(resistance, 3)}
        )
    
    def _generate_key_factors(self, category: str, price: float) -> List[str]:
        """Generate relevant key factors based on market category"""
        factor_templates = {
            'politics': [
                'Polling data trends',
                'Campaign funding levels',
                'Debate performance',
                'Economic indicators',
                'Historical voting patterns'
            ],
            'crypto': [
                'Market sentiment',
                'Regulatory developments',
                'Technical analysis',
                'Institutional adoption',
                'Network metrics'
            ],
            'technology': [
                'Industry developments',
                'Research progress', 
                'Patent filings',
                'Investment flows',
                'Competitive landscape'
            ],
            'economics': [
                'Economic indicators',
                'Federal Reserve policy',
                'Employment data',
                'Inflation trends',
                'GDP growth'
            ],
            'sports': [
                'Team performance',
                'Player injuries',
                'Historical matchups',
                'Weather conditions',
                'Betting odds'
            ]
        }
        
        # Get factors for category or use general ones
        factors = factor_templates.get(category, [
            'Market dynamics',
            'News sentiment',
            'Trading volume',
            'Time to expiry',
            'Risk factors'
        ])
        
        # Return 3-4 random factors
        return random.sample(factors, min(len(factors), random.randint(3, 4)))
    
    async def generate_trading_signal(self, market: Dict, analysis: MarketAnalysis) -> Optional[TradingSignal]:
        """Generate a trading signal based on market analysis"""
        yes_price = market['yes_price']
        fair_value = analysis.fair_value
        
        # Calculate edge (difference between fair value and current price)
        edge = fair_value - yes_price
        
        # Minimum edge threshold
        min_edge = 0.05
        
        if abs(edge) < min_edge:
            return None  # No signal if edge is too small
        
        # Determine side and confidence
        if edge > 0:
            side = TradeSide.YES
            confidence = min(0.9, abs(edge) * 2 + analysis.confidence * 0.3)
        else:
            side = TradeSide.NO
            confidence = min(0.9, abs(edge) * 2 + analysis.confidence * 0.3)
        
        # Calculate position size using simplified Kelly criterion
        kelly_fraction = (confidence * abs(edge)) / (1 - confidence)
        kelly_fraction = min(0.25, kelly_fraction)  # Cap at 25% of bankroll
        
        # Base position size
        base_size = settings.max_position_size * kelly_fraction
        
        # Adjust for liquidity
        liquidity_factor = min(1.0, market['liquidity'] / 10000)  # Adjust for liquidity
        recommended_size = base_size * liquidity_factor
        
        # Entry price (slight improvement from current price)
        if side == TradeSide.YES:
            entry_price = max(0.01, yes_price - 0.01)  # Bid slightly below
        else:
            entry_price = min(0.99, (1 - yes_price) - 0.01)  # Bid slightly below no price
        
        # Stop loss and take profit
        stop_loss = entry_price * (0.9 if side == TradeSide.YES else 1.1)
        take_profit = entry_price * (1.2 if side == TradeSide.YES else 0.8)
        
        # Generate reasoning
        reasoning = f"Fair value ({fair_value:.3f}) vs current price ({yes_price:.3f}) suggests {abs(edge):.3f} edge. " \
                   f"Market shows {analysis.trend} trend with {analysis.confidence:.2f} confidence. " \
                   f"Key factors: {', '.join(analysis.key_factors[:2])}"
        
        return TradingSignal(
            market_id=market['id'],
            side=side,
            confidence=confidence,
            recommended_size=round(recommended_size, 2),
            entry_price=round(entry_price, 3),
            stop_loss=round(max(0.01, min(0.99, stop_loss)), 3),
            take_profit=round(max(0.01, min(0.99, take_profit)), 3),
            reasoning=reasoning,
            risk_score=1 - confidence  # Higher confidence = lower risk
        )

# Global AI analyst instance
ai_analyst = AIAnalyst()