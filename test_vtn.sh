#!/bin/bash
# Test VTNext Demo

echo "Building kernel..."
make microkernel 2>&1 | tail -5

echo ""
echo "Starting test - press Q to quit vtn_demo, or Ctrl-A X to exit QEMU"
echo "============================================================"

# Run with serial output
qemu-system-i386 -drive file=build/brainhair.img,format=raw \
    -display none -serial stdio \
    -device e1000,netdev=net0 -netdev user,id=net0
