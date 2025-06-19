import asyncio
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
import json
from datetime import datetime
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.database import db
from core.models import TradingSignal, TradeSide
from api.polymarket_client import polymarket_client
from api.ai_client import ai_analyst
from trading.algorithms import trading_engine
from web.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Polymarket AI Trading System",
    description="Zero-configuration AI-powered prediction market trading platform",
    version="1.0.0"
)

# Static files and templates
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "demo_mode": settings.demo_mode,
        "has_polymarket_api": settings.has_polymarket_api,
        "has_google_api": settings.has_google_api
    })

@app.get("/api/markets")
async def get_markets(limit: int = 20):
    """Get active markets"""
    try:
        markets = await polymarket_client.get_markets(limit)
        return {"markets": markets}
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/markets/{market_id}")
async def get_market(market_id: str):
    """Get specific market details"""
    try:
        market = await db.get_market(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")
        
        # Get AI analysis
        analysis = await ai_analyst.analyze_market(market)
        
        # Get trading signal
        current_positions = await db.get_positions()
        signal = trading_engine.analyze_trading_opportunity(market, current_positions)
        
        return {
            "market": market,
            "analysis": analysis.dict() if analysis else None,
            "signal": signal.dict() if signal else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market {market_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    try:
        positions = await db.get_positions()
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades")
async def get_trades(limit: int = 50):
    """Get trade history"""
    try:
        trades = await db.get_trade_history(limit)
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio")
async def get_portfolio():
    """Get portfolio statistics"""
    try:
        stats = await db.get_portfolio_stats()
        balance = await polymarket_client.get_account_balance()
        
        return {
            "stats": stats,
            "balance": balance,
            "demo_mode": settings.demo_mode
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade")
async def execute_trade(trade_data: dict):
    """Execute a trade"""
    try:
        market_id = trade_data["market_id"]
        side = TradeSide(trade_data["side"])
        size = float(trade_data["size"])
        price = float(trade_data.get("price", 0))
        
        # Get market info - first try database, then get from current markets
        market = await db.get_market(market_id)
        if not market:
            # If not in database, get from current markets (for demo markets)
            markets = await polymarket_client.get_markets()
            market = next((m for m in markets if m["id"] == market_id), None)
            if not market:
                raise HTTPException(status_code=404, detail="Market not found")
        
        # Use current market price if not specified
        if price == 0:
            price = market["yes_price"] if side == TradeSide.YES else market["no_price"]
        
        # Execute trade through Polymarket client
        result = await polymarket_client.place_order(market_id, side, size, price)
        
        if result["success"]:
            # Ensure market exists in database (add if it's a demo market)
            db_market = await db.get_market(market_id)
            if not db_market:
                # Add demo market to database
                await db.add_market(market)
            
            # Record trade in database
            await db.record_trade(
                market_id=market_id,
                side=side.value,
                size=result["executed_size"],
                price=result["executed_price"],
                fee=result["fee"]
            )
            
            # Create position
            position_id = await db.create_position(
                market_id=market_id,
                side=side.value,
                size=result["executed_size"],
                entry_price=result["executed_price"]
            )
            
            # Broadcast update
            await manager.broadcast({
                "type": "trade_executed",
                "data": {
                    "market_id": market_id,
                    "side": side.value,
                    "size": result["executed_size"],
                    "price": result["executed_price"],
                    "position_id": position_id
                }
            })
            
            return {
                "success": True,
                "trade": result,
                "position_id": position_id
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Trade failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{market_id}")
async def get_market_analysis(market_id: str):
    """Get AI analysis for a market"""
    try:
        market = await db.get_market(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")
        
        analysis = await ai_analyst.analyze_market(market)
        return {"analysis": analysis.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing market {market_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals")
async def get_trading_signals():
    """Get trading signals for all markets"""
    try:
        markets = await polymarket_client.get_markets(10)
        current_positions = await db.get_positions()
        
        signals = []
        for market in markets:
            try:
                signal = trading_engine.analyze_trading_opportunity(market, current_positions)
                if signal:
                    signals.append(signal.dict())
            except Exception as e:
                logger.error(f"Error generating signal for {market['id']}: {e}")
                continue
        
        # If no signals generated, create some demo signals for testing
        if not signals and settings.demo_mode:
            import random
            demo_signals = []
            for i, market in enumerate(markets[:3]):
                if random.random() > 0.5:  # 50% chance to generate signal
                    side = TradeSide.YES if random.random() > 0.5 else TradeSide.NO
                    confidence = random.uniform(0.6, 0.8)
                    size = random.uniform(25, 75)
                    price = market["yes_price"] if side == TradeSide.YES else market["no_price"]
                    
                    demo_signal = TradingSignal(
                        market_id=market["id"],
                        side=side,
                        confidence=confidence,
                        recommended_size=size,
                        entry_price=price - 0.01 if side == TradeSide.YES else price - 0.01,
                        stop_loss=max(0.01, price * 0.8),
                        take_profit=min(0.99, price * 1.2),
                        reasoning=f"Demo signal: {market['category']} market showing {side.value.upper()} opportunity with {confidence:.0%} confidence",
                        risk_score=1 - confidence
                    )
                    demo_signals.append(demo_signal.dict())
            signals = demo_signals
        
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle WebSocket messages if needed
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to update market data
async def update_market_data():
    """Background task to periodically update market data"""
    while True:
        try:
            logger.info("Updating market data...")
            
            # Fetch latest markets
            markets = await polymarket_client.get_markets(20)
            
            # Update database with new prices
            for market in markets:
                try:
                    await db.update_market_prices(
                        market["id"],
                        market["yes_price"],
                        market["no_price"]
                    )
                except Exception as e:
                    logger.error(f"Error updating market {market['id']}: {e}")
            
            # Update position PnL
            positions = await db.get_positions()
            for position in positions:
                try:
                    market = next((m for m in markets if m["id"] == position["market_id"]), None)
                    if market:
                        current_price = market["yes_price"] if position["side"] == "yes" else market["no_price"]
                        
                        if position["side"] == "yes":
                            pnl = (current_price - position["entry_price"]) * position["size"]
                        else:
                            pnl = (position["entry_price"] - current_price) * position["size"]
                        
                        await db.update_position_pnl(position["id"], current_price, pnl)
                except Exception as e:
                    logger.error(f"Error updating position {position['id']}: {e}")
            
            # Broadcast updates
            await manager.broadcast({
                "type": "market_update",
                "data": {"markets": markets, "timestamp": datetime.now().isoformat()}
            })
            
        except Exception as e:
            logger.error(f"Error in background update: {e}")
        
        # Wait 30 seconds before next update
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Polymarket AI Trading System...")
    logger.info(f"Demo Mode: {settings.demo_mode}")
    logger.info(f"Polymarket API: {'Configured' if settings.has_polymarket_api else 'Not configured'}")
    logger.info(f"Google AI API: {'Configured' if settings.has_google_api else 'Not configured'}")
    
    # Start background task
    asyncio.create_task(update_market_data())

if __name__ == "__main__":
    # Print startup banner
    import subprocess
    try:
        local_ip = subprocess.check_output(
            "ifconfig | grep 'inet ' | grep -v 127.0.0.1 | head -1 | awk '{print $2}'", 
            shell=True
        ).decode().strip()
    except:
        local_ip = "unknown"
    
    print("\n" + "="*60)
    print("🚀 POLYMARKET AI TRADING SYSTEM")
    print("="*60)
    if settings.host == "0.0.0.0":
        print(f"📱 Local: http://localhost:{settings.port}")
        print(f"🌍 Network: http://{local_ip}:{settings.port}")
    else:
        print(f"📱 Dashboard: http://{settings.host}:{settings.port}")
    print(f"🔧 Demo Mode: {'ON' if settings.demo_mode else 'OFF'}")
    print(f"🔑 APIs: PM={'✓' if settings.has_polymarket_api else '✗'} | AI={'✓' if settings.has_google_api else '✗'}")
    print("="*60 + "\n")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )