import sqlite3
import asyncio
import aiosqlite
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from contextlib import asynccontextmanager

class Database:
    def __init__(self, db_path: str = "../data/polymarket_ai.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    @asynccontextmanager
    async def get_connection(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn
    
    async def get_markets(self, limit: int = 50) -> List[Dict]:
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM markets ORDER BY volume DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_market(self, market_id: str) -> Optional[Dict]:
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM markets WHERE id = ?", (market_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_market_prices(self, market_id: str, yes_price: float, no_price: float):
        async with self.get_connection() as conn:
            await conn.execute(
                """UPDATE markets SET yes_price = ?, no_price = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (yes_price, no_price, market_id)
            )
            await conn.commit()
    
    async def add_market(self, market: Dict):
        """Add a new market to the database"""
        async with self.get_connection() as conn:
            await conn.execute(
                """INSERT OR REPLACE INTO markets 
                   (id, question, end_date, category, volume, liquidity, yes_price, no_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    market["id"], market["question"], market.get("end_date"),
                    market.get("category"), market.get("volume", 0),
                    market.get("liquidity", 0), market.get("yes_price", 0.5),
                    market.get("no_price", 0.5)
                )
            )
            await conn.commit()
    
    async def get_positions(self, status: str = "open") -> List[Dict]:
        async with self.get_connection() as conn:
            query = """
                SELECT p.*, m.question, m.category 
                FROM positions p 
                JOIN markets m ON p.market_id = m.id 
                WHERE p.status = ?
                ORDER BY p.created_at DESC
            """
            async with conn.execute(query, (status,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def create_position(self, market_id: str, side: str, size: float, entry_price: float) -> int:
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO positions (market_id, side, size, entry_price, current_price, status) 
                   VALUES (?, ?, ?, ?, ?, 'open')""",
                (market_id, side, size, entry_price, entry_price)
            )
            await conn.commit()
            return cursor.lastrowid
    
    async def update_position_pnl(self, position_id: int, current_price: float, pnl: float):
        async with self.get_connection() as conn:
            await conn.execute(
                """UPDATE positions SET current_price = ?, pnl = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (current_price, pnl, position_id)
            )
            await conn.commit()
    
    async def close_position(self, position_id: int, exit_price: float):
        async with self.get_connection() as conn:
            await conn.execute(
                """UPDATE positions SET status = 'closed', current_price = ?, 
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (exit_price, position_id)
            )
            await conn.commit()
    
    async def record_trade(self, market_id: str, side: str, size: float, price: float, fee: float = 0):
        async with self.get_connection() as conn:
            await conn.execute(
                """INSERT INTO trades (market_id, side, size, price, fee) 
                   VALUES (?, ?, ?, ?, ?)""",
                (market_id, side, size, price, fee)
            )
            await conn.commit()
    
    async def get_trade_history(self, limit: int = 100) -> List[Dict]:
        async with self.get_connection() as conn:
            query = """
                SELECT t.*, m.question, m.category 
                FROM trades t 
                JOIN markets m ON t.market_id = m.id 
                ORDER BY t.timestamp DESC LIMIT ?
            """
            async with conn.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_portfolio_stats(self) -> Dict:
        async with self.get_connection() as conn:
            # Total PnL from positions
            async with conn.execute("SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM positions") as cursor:
                total_pnl = (await cursor.fetchone())[0]
            
            # Open positions count
            async with conn.execute("SELECT COUNT(*) as open_positions FROM positions WHERE status = 'open'") as cursor:
                open_positions = (await cursor.fetchone())[0]
            
            # Total trades
            async with conn.execute("SELECT COUNT(*) as total_trades FROM trades") as cursor:
                total_trades = (await cursor.fetchone())[0]
            
            # Win rate (closed profitable positions)
            async with conn.execute(
                "SELECT COUNT(*) as wins FROM positions WHERE status = 'closed' AND pnl > 0"
            ) as cursor:
                wins = (await cursor.fetchone())[0]
            
            async with conn.execute("SELECT COUNT(*) as total_closed FROM positions WHERE status = 'closed'") as cursor:
                total_closed = (await cursor.fetchone())[0]
            
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
            
            return {
                "total_pnl": total_pnl,
                "open_positions": open_positions,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "total_closed_positions": total_closed
            }

# Global database instance
db = Database()