import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from core.config import settings
from core.models import Market, TradeSide

logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self):
        self.demo_mode = not settings.has_polymarket_api
        self.client = None
        
        if settings.has_polymarket_api:
            try:
                self.client = ClobClient(
                    host="https://clob.polymarket.com",
                    key=settings.polymarket_api_key,
                    secret=settings.polymarket_secret,
                    passphrase=settings.polymarket_passphrase,
                    chain_id=POLYGON,
                )
                self.demo_mode = False
                logger.info("Polymarket API client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Polymarket client: {e}. Using demo mode.")
                self.demo_mode = True
        else:
            logger.info("No Polymarket API credentials found. Using demo mode.")
    
    async def get_markets(self, limit: int = 50) -> List[Dict]:
        """Get active markets from Polymarket API or return demo data"""
        if self.demo_mode:
            return await self._get_demo_markets(limit)
        
        try:
            # Get markets from real API
            markets_data = self.client.get_markets()
            markets = []
            
            for market_data in markets_data[:limit]:
                try:
                    market = {
                        "id": market_data.get("condition_id", f"market_{random.randint(1000, 9999)}"),
                        "question": market_data.get("question", "Unknown Market"),
                        "end_date": market_data.get("end_date_iso"),
                        "category": market_data.get("category", "General"),
                        "volume": float(market_data.get("volume", 0)),
                        "liquidity": float(market_data.get("liquidity", 0)),
                        "yes_price": float(market_data.get("yes_price", 0.5)),
                        "no_price": float(market_data.get("no_price", 0.5)),
                    }
                    markets.append(market)
                except Exception as e:
                    logger.error(f"Error parsing market data: {e}")
                    continue
            
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching markets from API: {e}. Falling back to demo mode.")
            return await self._get_demo_markets(limit)
    
    async def _get_demo_markets(self, limit: int) -> List[Dict]:
        """Generate realistic demo market data"""
        base_markets = [
            {
                "question": "Will the Democratic candidate win the 2024 US Presidential Election?",
                "category": "Politics",
                "base_volume": 1500000,
                "base_yes_price": 0.52
            },
            {
                "question": "Will Bitcoin reach $50,000 by end of 2024?",
                "category": "Crypto",
                "base_volume": 890000,
                "base_yes_price": 0.68
            },
            {
                "question": "Will there be a major AI breakthrough announced in 2024?",
                "category": "Technology",
                "base_volume": 340000,
                "base_yes_price": 0.74
            },
            {
                "question": "Will the S&P 500 reach 5000 points in 2024?",
                "category": "Finance",
                "base_volume": 567000,
                "base_yes_price": 0.43
            },
            {
                "question": "Will Ethereum reach $3000 by end of 2024?",
                "category": "Crypto",
                "base_volume": 423000,
                "base_yes_price": 0.61
            },
            {
                "question": "Will there be a recession in the US in 2024?",
                "category": "Economics",
                "base_volume": 234000,
                "base_yes_price": 0.28
            },
            {
                "question": "Will Tesla stock price exceed $300 in 2024?",
                "category": "Stocks",
                "base_volume": 189000,
                "base_yes_price": 0.35
            },
            {
                "question": "Will the Federal Reserve cut interest rates in 2024?",
                "category": "Economics",
                "base_volume": 445000,
                "base_yes_price": 0.72
            }
        ]
        
        markets = []
        for i, base_market in enumerate(base_markets[:limit]):
            # Add some realistic price movement
            price_change = random.uniform(-0.05, 0.05)
            yes_price = max(0.01, min(0.99, base_market["base_yes_price"] + price_change))
            no_price = 1.0 - yes_price
            
            # Add some volume variation
            volume_multiplier = random.uniform(0.8, 1.2)
            volume = base_market["base_volume"] * volume_multiplier
            
            market = {
                "id": f"demo_market_{i + 1}",
                "question": base_market["question"],
                "end_date": (datetime.now() + timedelta(days=random.randint(7, 120))).isoformat(),
                "category": base_market["category"],
                "volume": volume,
                "liquidity": volume * 0.06,  # ~6% of volume as liquidity
                "yes_price": round(yes_price, 3),
                "no_price": round(no_price, 3),
            }
            markets.append(market)
        
        return markets
    
    async def get_market_orderbook(self, market_id: str) -> Dict:
        """Get orderbook for a specific market"""
        if self.demo_mode:
            return self._generate_demo_orderbook()
        
        try:
            # Get real orderbook data
            orderbook = self.client.get_orderbook(market_id)
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}. Using demo data.")
            return self._generate_demo_orderbook()
    
    def _generate_demo_orderbook(self) -> Dict:
        """Generate realistic demo orderbook"""
        # Generate realistic bid/ask spreads
        mid_price = random.uniform(0.3, 0.7)
        spread = random.uniform(0.01, 0.05)
        
        bids = []
        asks = []
        
        # Generate bids (below mid price)
        for i in range(5):
            price = mid_price - spread/2 - (i * 0.01)
            size = random.uniform(100, 1000)
            bids.append({"price": round(max(0.01, price), 3), "size": round(size, 2)})
        
        # Generate asks (above mid price)  
        for i in range(5):
            price = mid_price + spread/2 + (i * 0.01)
            size = random.uniform(100, 1000)
            asks.append({"price": round(min(0.99, price), 3), "size": round(size, 2)})
        
        return {
            "bids": bids,
            "asks": asks,
            "spread": round(spread, 4),
            "mid_price": round(mid_price, 3)
        }
    
    async def place_order(self, market_id: str, side: TradeSide, size: float, price: float) -> Dict:
        """Place an order (demo mode simulates execution)"""
        if self.demo_mode:
            return await self._simulate_order_execution(market_id, side, size, price)
        
        try:
            # Place real order
            order_args = {
                "token_id": market_id,
                "price": price,
                "size": size,
                "side": "BUY" if side == TradeSide.YES else "SELL",
                "fee_rate_bps": 0,  # Fee rate in basis points
            }
            
            result = self.client.post_order(**order_args)
            return {
                "success": True,
                "order_id": result.get("order_id"),
                "executed_size": size,
                "executed_price": price,
                "fee": size * price * 0.001  # 0.1% fee
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _simulate_order_execution(self, market_id: str, side: TradeSide, size: float, price: float) -> Dict:
        """Simulate order execution in demo mode"""
        # Simulate some slippage and partial fills
        slippage = random.uniform(0, 0.02)  # Up to 2% slippage
        fill_rate = random.uniform(0.8, 1.0)  # 80-100% fill rate
        
        executed_price = price * (1 + slippage if side == TradeSide.YES else 1 - slippage)
        executed_size = size * fill_rate
        fee = executed_size * executed_price * 0.001  # 0.1% fee
        
        # Simulate slight delay
        await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "order_id": f"demo_order_{random.randint(10000, 99999)}",
            "executed_size": round(executed_size, 2),
            "executed_price": round(executed_price, 3),
            "fee": round(fee, 2),
            "demo_mode": True
        }
    
    async def get_account_balance(self) -> float:
        """Get account balance (returns demo balance in demo mode)"""
        if self.demo_mode:
            return 10000.0  # $10,000 demo balance
        
        try:
            balance_data = self.client.get_balance()
            return float(balance_data.get("balance", 0))
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0

# Global client instance
polymarket_client = PolymarketClient()