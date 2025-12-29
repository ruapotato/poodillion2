#!/bin/bash
# Run BrainhairOS with VTNext graphical terminal
#
# This script:
# 1. Builds the kernel if needed
# 2. Starts QEMU with serial output
# 3. Launches the VTNext graphical terminal
#
# Requirements:
#   pip install pygame pyserial

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Build if needed
echo "Building kernel..."
make microkernel 2>&1 | tail -3

# Check for pygame
if ! python3 -c "import pygame" 2>/dev/null; then
    echo "Installing pygame..."
    pip install pygame
fi

# Create a named pipe for serial communication
PIPE="/tmp/brainhair_serial_$$"
mkfifo "$PIPE.in" 2>/dev/null || true
mkfifo "$PIPE.out" 2>/dev/null || true

cleanup() {
    echo "Cleaning up..."
    rm -f "$PIPE.in" "$PIPE.out"
    kill $QEMU_PID 2>/dev/null || true
    kill $TERM_PID 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "=== VTNext Graphics Terminal ==="
echo "Starting QEMU and VTNext terminal..."
echo "Press ESC or Q in the graphics window to quit"
echo ""

# Method 1: Use PTY (simpler)
# Start QEMU with PTY serial
qemu-system-i386 \
    -drive file=build/brainhair.img,format=raw \
    -display none \
    -serial pty \
    2>&1 &
QEMU_PID=$!

# Wait for QEMU to print the PTY path
sleep 1

# Get the PTY path from QEMU output (it prints "char device redirected to /dev/pts/X")
PTY_PATH=$(ps aux | grep -o '/dev/pts/[0-9]*' | head -1)

if [ -z "$PTY_PATH" ]; then
    echo "Could not detect QEMU PTY. Trying alternative method..."

    # Method 2: Use TCP
    kill $QEMU_PID 2>/dev/null || true
    sleep 1

    qemu-system-i386 \
        -drive file=build/brainhair.img,format=raw \
        -display none \
        -serial tcp:localhost:5555,server,nowait \
        &
    QEMU_PID=$!

    sleep 2
    echo "Connecting to QEMU serial on TCP port 5555..."
    python3 "$SCRIPT_DIR/vtnext_terminal.py" --tcp localhost:5555
else
    echo "QEMU PTY: $PTY_PATH"
    echo "Starting VTNext terminal..."
    sleep 1
    python3 "$SCRIPT_DIR/vtnext_terminal.py" --serial "$PTY_PATH"
fi

echo "Done."
