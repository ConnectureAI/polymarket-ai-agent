# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete zero-configuration Polymarket AI trading system that provides automated prediction market analysis and trading capabilities. The system features a beautiful web dashboard, real-time market monitoring, AI-powered analysis, and sophisticated trading algorithms.

## Quick Start Commands

```bash
# One-time setup (installs everything)
./setup.sh

# Start the system
./run.sh

# Dashboard will be available at http://localhost:3000
```

## Architecture Overview

### Core Technologies
- **Backend**: FastAPI with async Python 3.9+
- **Database**: SQLite (auto-upgrades to Supabase when configured)
- **AI Integration**: Google AI Studio (Gemini Pro) with local fallbacks
- **Market Data**: Polymarket API via py-clob-client
- **Frontend**: Vanilla JavaScript with Alpine.js and Tailwind CSS
- **Real-time**: WebSocket connections for live updates
- **Charts**: Chart.js for data visualization

### Key Components

#### 1. Core System (`src/core/`)
- `database.py` - Async SQLite operations and data models
- `config.py` - Environment configuration management
- `models.py` - Pydantic data models for type safety
- `error_handler.py` - Comprehensive error handling and circuit breakers

#### 2. API Integrations (`src/api/`)
- `polymarket_client.py` - Polymarket API client with demo mode fallback
- `ai_client.py` - Google AI integration with local analysis fallback

#### 3. Trading Engine (`src/trading/`)
- `algorithms.py` - Black-Scholes adaptation and Kelly Criterion position sizing
- `risk_management.py` - Portfolio risk assessment and safety limits

#### 4. Web Interface (`src/web/`)
- `main.py` - FastAPI application with REST API and WebSocket endpoints
- `websocket_manager.py` - Real-time connection management

#### 5. Frontend (`templates/` & `static/`)
- `dashboard.html` - Responsive single-page application
- `dashboard.css` - Custom styling and animations

## Configuration

### Environment Variables (.env)
- `POLYMARKET_API_KEY` - Optional, enables live trading
- `POLYMARKET_SECRET` - Polymarket API secret
- `POLYMARKET_PASSPHRASE` - Polymarket API passphrase
- `GOOGLE_API_KEY` - Optional, enables AI analysis
- `DATABASE_URL` - SQLite path (default: sqlite:///./data/polymarket_ai.db)
- `DEMO_MODE` - true/false (automatically determined by API availability)
- `MAX_POSITION_SIZE` - Maximum position size (default: 100.0)
- `RISK_TOLERANCE` - Risk tolerance level (default: 0.25)

### Progressive Enhancement
1. **Demo Mode**: Works immediately with sample data (no API keys required)
2. **AI Enhanced**: Add GOOGLE_API_KEY for AI-powered market analysis
3. **Live Trading**: Add Polymarket credentials for real trading

## Key Features

### Zero Configuration
- Starts in demo mode immediately
- Auto-detects available APIs and adjusts functionality
- Intelligent fallbacks for all external dependencies
- Pre-loaded sample data for immediate functionality

### Trading Algorithms
- **Black-Scholes Adaptation**: Fair value calculation for binary options
- **Kelly Criterion**: Optimal position sizing based on edge and confidence
- **Risk Management**: Portfolio heat monitoring, position limits, circuit breakers
- **Multi-timeframe Analysis**: Volatility assessment and time decay modeling

### AI Integration
- **Market Analysis**: Sentiment analysis and probability assessment
- **Trading Signals**: Automated signal generation with confidence scores
- **Smart Fallbacks**: Local heuristics when AI APIs unavailable
- **Risk Assessment**: Comprehensive position and portfolio risk analysis

### Web Dashboard
- **Real-time Updates**: Live market prices and position P&L
- **Interactive Charts**: Portfolio performance and market trends
- **Mobile Responsive**: Works on all device sizes
- **Trading Interface**: One-click trade execution with confirmation

## Database Schema

### Markets Table
- Market information, prices, volume, liquidity
- Category classification and expiry dates

### Positions Table
- Open/closed positions with entry/exit prices
- Real-time P&L calculation and status tracking

### Trades Table
- Complete trade history with fees and timestamps
- Market context and performance analytics

## API Endpoints

### Market Data
- `GET /api/markets` - List active markets
- `GET /api/markets/{id}` - Market details with AI analysis
- `GET /api/analysis/{id}` - Detailed market analysis

### Trading
- `GET /api/positions` - Current positions
- `GET /api/trades` - Trade history
- `POST /api/trade` - Execute trade
- `GET /api/signals` - Generated trading signals

### Portfolio
- `GET /api/portfolio` - Portfolio stats and balance
- `WebSocket /ws` - Real-time updates

## Development Guidelines

### Code Organization
- Use async/await for all I/O operations
- Implement comprehensive error handling with fallbacks
- Follow type hints and Pydantic models for data validation
- Maintain backward compatibility with demo mode

### Testing Strategy
- Test both live API and demo mode functionality
- Verify graceful degradation when APIs unavailable
- Test risk management limits and circuit breakers
- Validate trading algorithm calculations

### Security Considerations
- API keys stored in environment variables only
- Trading size limits enforced at multiple levels
- Circuit breakers prevent runaway trading
- Input validation on all endpoints

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure virtual environment is activated
2. **Database Errors**: Check `data/` directory permissions
3. **API Failures**: System automatically falls back to demo mode
4. **Port Conflicts**: Modify PORT in .env file

### Error Recovery
- Circuit breakers automatically disable failing APIs
- Cached data used when real-time feeds unavailable
- Demo mode provides full functionality without external dependencies
- Health monitoring tracks component status

## Monitoring and Logs

### Log Files
- Application logs in `logs/` directory
- Error tracking with detailed stack traces
- Performance metrics and API response times

### Health Monitoring
- Component status tracking
- Circuit breaker status
- Error rate monitoring
- System performance metrics