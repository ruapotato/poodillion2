#!/bin/bash
# BrainhairOS VTNext Desktop - Master Start Script
#
# This script:
# 1. Builds the kernel if needed
# 2. Starts QEMU with serial over TCP
# 3. Launches the VTNext graphical terminal
# 4. Logs all raw VTNext commands for debugging
#
# Usage:
#   ./start.sh           # Normal start
#   ./start.sh --debug   # Start with visible debug output
#   ./start.sh --build   # Force rebuild before starting
#   ./start.sh --log     # View the debug log

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
TCP_PORT=5555
LOG_FILE="$SCRIPT_DIR/vtnext_debug.log"
DEBUG_MODE=0
FORCE_BUILD=0

# Parse arguments
for arg in "$@"; do
    case $arg in
        --debug)
            DEBUG_MODE=1
            ;;
        --build)
            FORCE_BUILD=1
            ;;
        --log)
            if [ -f "$LOG_FILE" ]; then
                echo "=== VTNext Debug Log ==="
                echo "File: $LOG_FILE"
                echo ""
                cat "$LOG_FILE"
            else
                echo "No log file found at: $LOG_FILE"
            fi
            exit 0
            ;;
        --clear-log)
            rm -f "$LOG_FILE"
            echo "Log cleared."
            exit 0
            ;;
        --help|-h)
            echo "BrainhairOS VTNext Desktop Launcher"
            echo ""
            echo "Usage: ./start.sh [options]"
            echo ""
            echo "Options:"
            echo "  --debug      Show debug output in terminal"
            echo "  --build      Force rebuild before starting"
            echo "  --log        View the debug log"
            echo "  --clear-log  Clear the debug log"
            echo "  --help       Show this help"
            echo ""
            echo "Keyboard Controls (in VTNext terminal):"
            echo "  Q          Exit desktop to shell"
            echo "  D          Launch graphics demo"
            echo "  P          Launch Pong game"
            echo "  Ctrl+Q     Close VTNext terminal"
            echo ""
            echo "Debug log: $LOG_FILE"
            exit 0
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  BrainhairOS VTNext Desktop (x86_64)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for pygame
if ! python3 -c "import pygame" 2>/dev/null; then
    echo -e "${YELLOW}Installing pygame...${NC}"
    pip install pygame --quiet
fi

# Build kernel (64-bit)
if [ "$FORCE_BUILD" = "1" ] || [ ! -f "build/brainhair64.img" ]; then
    echo -e "${YELLOW}Building 64-bit kernel...${NC}"
    make microkernel-64 2>&1 | tail -5
else
    echo -e "${GREEN}Using existing 64-bit kernel build${NC}"
fi

# Kill any existing QEMU instances
pkill -f "qemu-system-x86_64.*brainhair" 2>/dev/null || true
sleep 0.5

# Initialize debug log
echo "=== VTNext Debug Log ===" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "========================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Create data disk for BrainFS if not exists
DATA_DISK="$SCRIPT_DIR/build/data.img"
if [ ! -f "$DATA_DISK" ]; then
    echo -e "${YELLOW}Creating data disk for filesystem...${NC}"
    dd if=/dev/zero of="$DATA_DISK" bs=1M count=16 2>/dev/null
fi

# Start QEMU with TCP serial and data disk (64-bit)
echo -e "${YELLOW}Starting QEMU (x86_64)...${NC}"
qemu-system-x86_64 \
    -cpu qemu64 \
    -m 256M \
    -drive file=build/brainhair64.img,format=raw \
    -drive file=$DATA_DISK,format=raw \
    -display none \
    -serial tcp:127.0.0.1:$TCP_PORT,server,nowait \
    2>/dev/null &
QEMU_PID=$!

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $QEMU_PID 2>/dev/null || true
    if [ "$DEBUG_MODE" = "1" ]; then
        echo ""
        echo -e "${BLUE}Debug log saved to: $LOG_FILE${NC}"
        echo "Last 20 lines:"
        tail -20 "$LOG_FILE"
    fi
}
trap cleanup EXIT

# Wait for QEMU to start
sleep 2

echo -e "${GREEN}QEMU running on TCP port $TCP_PORT${NC}"
echo ""
echo -e "${BLUE}Controls:${NC}"
echo "  Q        - Exit desktop to shell"
echo "  D        - Launch demo"
echo "  Ctrl+Q   - Close terminal"
echo ""
echo -e "${YELLOW}Launching VTNext terminal...${NC}"
echo ""

# Launch VTNext terminal with logging
if [ "$DEBUG_MODE" = "1" ]; then
    # Debug mode - show raw data in terminal too
    python3 "$SCRIPT_DIR/tools/vtnext_terminal.py" --tcp 127.0.0.1:$TCP_PORT --log "$LOG_FILE" --debug
else
    python3 "$SCRIPT_DIR/tools/vtnext_terminal.py" --tcp 127.0.0.1:$TCP_PORT --log "$LOG_FILE"
fi

echo -e "${GREEN}Done.${NC}"
