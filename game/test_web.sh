#!/bin/bash
# Quick test to verify web server can start

echo "Testing Poodillion Web Server..."
echo ""

# Test Python imports
echo "1. Testing Python imports..."
python3 -c "
from world_1990 import create_december_1990_world
from core.system import UnixSystem
from core.shell import ShellExecutor
print('   ✓ Imports successful')
"

if [ $? -ne 0 ]; then
    echo "   ✗ Import failed"
    exit 1
fi

# Test world creation
echo "2. Testing world creation..."
python3 -c "
from world_1990 import create_december_1990_world
attacker, network, all_systems = create_december_1990_world()
print(f'   ✓ Created world with {len(all_systems)} systems')
print(f'   ✓ Network has {len(network.systems)} registered systems')
print(f'   ✓ Attacker system: {attacker.hostname} at {attacker.ip}')
"

if [ $? -ne 0 ]; then
    echo "   ✗ World creation failed"
    exit 1
fi

# Test Flask imports
echo "3. Testing Flask dependencies..."
python3 -c "
import flask
import flask_socketio
print('   ✓ Flask and Socket.IO available')
"

if [ $? -ne 0 ]; then
    echo "   ✗ Flask dependencies missing"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "Ready to start server with:"
echo "  python3 web_server.py"
echo ""
