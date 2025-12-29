#!/bin/bash
# Run BrainhairOS with VTNext graphical terminal (TCP method)
#
# This is the most reliable method - uses TCP for serial connection

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Build if needed
echo "Building kernel..."
make microkernel 2>&1 | tail -3

# Kill any existing QEMU
pkill -f "qemu-system-i386.*brainhair" 2>/dev/null || true
sleep 0.5

echo ""
echo "=== VTNext Graphics Terminal ==="
echo "Starting QEMU with TCP serial on port 5555..."
echo ""

# Start QEMU with TCP serial in background
qemu-system-i386 \
    -drive file=build/brainhair.img,format=raw \
    -display none \
    -serial tcp:127.0.0.1:5555,server,nowait \
    &
QEMU_PID=$!

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $QEMU_PID 2>/dev/null || true
}
trap cleanup EXIT

# Wait for QEMU to start
sleep 2

echo "Connecting VTNext terminal to TCP port 5555..."
echo "Press ESC or Q in the graphics window to quit"
echo ""

python3 "$SCRIPT_DIR/vtnext_terminal.py" --tcp 127.0.0.1:5555

echo "Done."
