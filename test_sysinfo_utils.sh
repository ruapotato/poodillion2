#!/bin/bash
# Test script for BrainhairOS system information utilities

echo "========================================"
echo "  BrainhairOS System Info Utilities"
echo "========================================"
echo ""

echo "1. printenv - Print all environment variables"
echo "   Command: ./bin/printenv | head -5"
./bin/printenv | head -5
echo "   ..."
echo ""

echo "2. printenv - Print specific variable (PATH)"
echo "   Command: ./bin/printenv PATH"
./bin/printenv PATH
echo ""

echo "3. printenv - Print specific variable (HOME)"
echo "   Command: ./bin/printenv HOME"
./bin/printenv HOME
echo ""

echo "4. printenv - Nonexistent variable (should exit 1)"
echo "   Command: ./bin/printenv NONEXISTENT"
./bin/printenv NONEXISTENT 2>&1
echo "   Exit code: $?"
echo ""

echo "5. tty - Print terminal name"
echo "   Command: ./bin/tty"
./bin/tty
echo "   Exit code: $?"
echo ""

echo "6. nproc - Print number of CPUs"
echo "   Command: ./bin/nproc"
./bin/nproc
echo ""

echo "7. arch - Print machine architecture"
echo "   Command: ./bin/arch"
./bin/arch
echo ""

echo "8. logname - Print login name"
echo "   Command: ./bin/logname"
./bin/logname
echo ""

echo "9. groups - Print group memberships"
echo "   Command: ./bin/groups"
./bin/groups
echo ""

echo "========================================"
echo "  Comparison with System Utilities"
echo "========================================"
echo ""
echo "nproc comparison:"
echo "  System: $(nproc)"
echo "  Ours:   $(./bin/nproc)"
echo ""
echo "arch comparison:"
echo "  System: $(arch)"
echo "  Ours:   $(./bin/arch)"
echo ""
echo "logname comparison:"
echo "  System: $(logname)"
echo "  Ours:   $(./bin/logname)"
echo ""

echo "========================================"
echo "  All tests completed!"
echo "========================================"
