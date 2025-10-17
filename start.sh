#!/bin/bash
# Quick start script for Poodillion Web Server

echo "================================================"
echo "    🖥️  POODILLION WEB SERVER"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Start server
echo "🚀 Starting Poodillion Web Server..."
echo ""
echo "   Open your browser to: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""
python web_server.py
