#!/bin/bash

set -e

echo "🚀 Starting Polymarket AI Trading System..."

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ Configuration file not found. Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if main application exists
if [ ! -f "src/main.py" ]; then
    echo "❌ Main application not found. Please run ./setup.sh first"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo "🔧 Configuration:"
echo "   • Host: ${HOST:-127.0.0.1}"
echo "   • Port: ${PORT:-3000}"
echo "   • Demo Mode: ${DEMO_MODE:-true}"
echo "   • Database: ${DATABASE_URL:-sqlite:///./data/polymarket_ai.db}"
echo ""

# Get local IP address
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

# Start the application
echo "🌐 Starting web server..."
if [ "${HOST}" = "0.0.0.0" ]; then
    echo "📱 Local access: http://localhost:${PORT:-3000}"
    echo "🌍 Network access: http://${LOCAL_IP}:${PORT:-3000}"
    echo "📲 Access from any device on your network using the network URL above"
else
    echo "📱 Dashboard will be available at: http://${HOST:-127.0.0.1}:${PORT:-3000}"
fi
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd src && python main.py