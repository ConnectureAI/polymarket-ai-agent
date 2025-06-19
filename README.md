# 🚀 Polymarket AI Trading System

A complete zero-configuration AI-powered prediction market trading platform. Start trading in seconds with live market analysis, automated signals, and a beautiful dashboard - no setup required!

## ✨ Features

🎯 **Zero Configuration** - Works immediately with demo data  
🤖 **AI-Powered Analysis** - Google Gemini Pro integration with smart fallbacks  
📊 **Professional Dashboard** - Real-time charts, positions, and P&L tracking  
⚡ **Live Trading** - Polymarket integration with risk management  
🛡️ **Safety First** - Circuit breakers, position limits, and comprehensive error handling  
📱 **Mobile Ready** - Responsive design that works everywhere  

## 🚀 Quick Start

```bash
git clone https://github.com/ConnectureAI/polymarket-ai-agent
cd polymarket-ai-agent
./setup.sh
./run.sh
```

**That's it!** Open http://localhost:3000 and start trading immediately.

## 🎮 Demo Mode

The system starts in **demo mode** with realistic sample data, so you can:
- ✅ Explore the full trading interface
- ✅ Test AI analysis features  
- ✅ Practice with paper trading
- ✅ Learn the platform risk-free

## 🔧 Progressive Enhancement

### Level 1: Demo Mode (No APIs Required)
- Sample market data
- Local analysis algorithms
- Paper trading simulation
- Full dashboard functionality

### Level 2: AI Enhanced
Add your Google AI Studio API key to `.env`:
```bash
GOOGLE_API_KEY=your_key_here
```
- Real-time market analysis
- AI-generated trading signals
- Sentiment analysis
- Advanced market insights

### Level 3: Live Trading
Add Polymarket credentials to `.env`:
```bash
POLYMARKET_API_KEY=your_key
POLYMARKET_SECRET=your_secret
POLYMARKET_PASSPHRASE=your_passphrase
```
- Live market data
- Real trade execution
- Portfolio tracking
- Professional trading tools

## 🎯 Trading Algorithms

### Black-Scholes Adaptation
- Fair value calculation for binary options
- Time decay modeling
- Volatility assessment
- Risk-adjusted pricing

### Kelly Criterion Position Sizing
- Optimal bet sizing based on edge
- Risk-adjusted position allocation
- Bankroll management
- Expected value optimization

### Risk Management
- Portfolio heat monitoring
- Position size limits
- Category concentration limits
- Circuit breakers for protection

## 📊 Dashboard Features

### Live Markets
- Real-time price updates
- Volume and liquidity data
- Category filtering
- Market analysis

### Trading Interface
- One-click trade execution
- AI-generated signals
- Risk assessment
- Position management

### Portfolio Tracking
- Real-time P&L
- Position monitoring
- Trade history
- Performance analytics

### Risk Management
- Portfolio heat maps
- Risk metrics
- Safety alerts
- Position limits

## 🛠️ Technical Architecture

### Backend
- **FastAPI** - High-performance async Python API
- **SQLite** - Local database with optional cloud upgrade
- **WebSockets** - Real-time data streaming
- **Pydantic** - Type-safe data models

### Frontend
- **Alpine.js** - Reactive JavaScript framework
- **Tailwind CSS** - Modern utility-first styling
- **Chart.js** - Interactive data visualization
- **WebSocket** - Live updates

### Integrations
- **Polymarket API** - Live market data and trading
- **Google AI Studio** - Advanced market analysis
- **py-clob-client** - Professional trading client

## 🔒 Security & Safety

### Trading Safety
- Position size limits
- Portfolio risk controls
- Circuit breakers
- Demo mode default

### Data Security
- Environment variable configuration
- No hardcoded credentials
- Local data storage
- Optional cloud integration

### Error Handling
- Comprehensive fallbacks
- Graceful degradation
- Health monitoring
- Automatic recovery

## 📝 Configuration

### Environment Variables
Create or edit `.env` file:

```bash
# Optional: Polymarket API (enables live trading)
POLYMARKET_API_KEY=
POLYMARKET_SECRET=
POLYMARKET_PASSPHRASE=

# Optional: Google AI Studio (enables AI analysis)
GOOGLE_API_KEY=

# Trading Settings
DEMO_MODE=true
MAX_POSITION_SIZE=100.0
RISK_TOLERANCE=0.25

# Server Settings
HOST=127.0.0.1
PORT=3000
```

## 🚨 Troubleshooting

### Common Issues

**Setup fails?**
- Ensure Python 3.9+ is installed
- Check internet connection for dependencies
- Try running `./setup.sh` again

**Can't access dashboard?**
- Check if port 3000 is available
- Try changing PORT in `.env`
- Ensure `./run.sh` completed successfully

**Trading not working?**
- Verify API credentials in `.env`
- Check Polymarket API status
- Demo mode always works offline

**AI analysis unavailable?**
- Add GOOGLE_API_KEY to `.env`
- System works with local fallbacks
- Check Google AI Studio quota

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- 📚 [Documentation](./CLAUDE.md)
- 🐛 [Issues](https://github.com/ConnectureAI/polymarket-ai-agent/issues)
- 💬 [Discussions](https://github.com/ConnectureAI/polymarket-ai-agent/discussions)

## ⚠️ Disclaimer

This software is for educational and research purposes. Prediction market trading involves financial risk. Always:

- Start with demo mode
- Use appropriate position sizes
- Understand the risks involved
- Trade responsibly

---

**Ready to start trading? Run `./setup.sh` and get started in seconds!** 🚀