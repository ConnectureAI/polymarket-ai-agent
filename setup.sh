#!/bin/bash

set -e

echo "🚀 Setting up Polymarket AI Trading System..."

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "📱 Detected OS: ${MACHINE}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    if [[ "$MACHINE" == "Mac" ]]; then
        echo "💡 Install with: brew install python@3.11"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= tuple(map(int, '$REQUIRED_VERSION'.split('.'))) else 1)" 2>/dev/null; then
    echo "❌ Python $REQUIRED_VERSION+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p src/{core,api,trading,web,data}
mkdir -p static/{css,js,images}
mkdir -p templates
mkdir -p data/{markets,trades,cache}
mkdir -p logs
mkdir -p config

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating default configuration..."
    cat > .env << EOF
# Polymarket API Configuration (optional - works in demo mode without these)
POLYMARKET_API_KEY=
POLYMARKET_SECRET=
POLYMARKET_PASSPHRASE=

# Google AI Studio API Key (optional - has local fallback)
GOOGLE_API_KEY=

# Database Configuration
DATABASE_URL=sqlite:///./data/polymarket_ai.db

# Web Server
HOST=127.0.0.1
PORT=3000

# Trading Configuration
DEMO_MODE=true
MAX_POSITION_SIZE=100.0
RISK_TOLERANCE=0.25
ENABLE_AUTO_TRADING=false

# Logging
LOG_LEVEL=INFO
EOF
fi

# Initialize database
echo "🗄️ Initializing database..."
python3 -c "
import sqlite3
import os
os.makedirs('data', exist_ok=True)
conn = sqlite3.connect('data/polymarket_ai.db')
conn.execute('''
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    end_date TEXT,
    category TEXT,
    volume REAL DEFAULT 0,
    liquidity REAL DEFAULT 0,
    yes_price REAL DEFAULT 0.5,
    no_price REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.execute('''
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL,
    size REAL NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL,
    pnl REAL DEFAULT 0,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.execute('''
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL,
    size REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()
conn.close()
print('✅ Database initialized')
"

# Create sample data
echo "📊 Loading sample market data..."
python3 -c "
import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('data/polymarket_ai.db')

sample_markets = [
    {
        'id': 'sample_election_2024',
        'question': 'Will the Democratic candidate win the 2024 US Presidential Election?',
        'end_date': (datetime.now() + timedelta(days=30)).isoformat(),
        'category': 'Politics',
        'volume': 1250000.0,
        'liquidity': 85000.0,
        'yes_price': 0.52,
        'no_price': 0.48
    },
    {
        'id': 'sample_bitcoin_50k',
        'question': 'Will Bitcoin reach \$50,000 by end of 2024?',
        'end_date': (datetime.now() + timedelta(days=60)).isoformat(),
        'category': 'Crypto',
        'volume': 890000.0,
        'liquidity': 45000.0,
        'yes_price': 0.68,
        'no_price': 0.32
    },
    {
        'id': 'sample_ai_breakthrough',
        'question': 'Will there be a major AI breakthrough announced in 2024?',
        'end_date': (datetime.now() + timedelta(days=90)).isoformat(),
        'category': 'Technology',
        'volume': 340000.0,
        'liquidity': 22000.0,
        'yes_price': 0.74,
        'no_price': 0.26
    }
]

for market in sample_markets:
    conn.execute('''
        INSERT OR REPLACE INTO markets 
        (id, question, end_date, category, volume, liquidity, yes_price, no_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        market['id'], market['question'], market['end_date'], market['category'],
        market['volume'], market['liquidity'], market['yes_price'], market['no_price']
    ))

conn.commit()
conn.close()
print('✅ Sample data loaded')
"

echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the system, run:"
echo "    ./run.sh"
echo ""
echo "📱 The dashboard will be available at: http://localhost:3000"
echo ""
echo "⚙️ Configuration:"
echo "   • Demo mode: Enabled (no API keys required)"
echo "   • Database: SQLite (data/polymarket_ai.db)"
echo "   • Sample data: Loaded"
echo ""
echo "🔧 To configure API keys, edit the .env file"