#!/bin/bash
# BrainhairOS Startup Script

set -e

# Build first
echo "Building BrainhairOS..."
make brainhair

# Run QEMU with E1000 networking
echo "Starting QEMU..."
qemu-system-i386 \
    -drive file=build/brainhair.img,format=raw,if=ide \
    -device e1000,netdev=net0 \
    -netdev user,id=net0,hostfwd=tcp::5555-:80 \
    -serial stdio \
    -m 32M \
    "$@"
