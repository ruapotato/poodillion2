#!/bin/bash
#
# Brainhair Bootstrap Script
#
# This script performs a self-hosting verification of the Brainhair compiler:
# 1. Compiles the compiler components (lexer, parser, codegen) to native x86
# 2. Runs unit tests to verify compiler correctness
# 3. If tests pass, builds all OS userland programs
#
# Usage: ./bootstrap.sh [--skip-os] [--verbose] [--parallel N]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPILER_DIR="$SCRIPT_DIR/compiler"
TEST_DIR="$SCRIPT_DIR/tests/compiler_unit"
USERLAND_DIR="$SCRIPT_DIR/userland"
BIN_DIR="$SCRIPT_DIR/bin"
BUILD_DIR="$SCRIPT_DIR/build/bootstrap"

# Options
SKIP_OS=false
VERBOSE=false
PARALLEL=4

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-os)
            SKIP_OS=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-j)
            PARALLEL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-os      Skip building OS userland programs"
            echo "  --verbose, -v  Show detailed output"
            echo "  --parallel, -j N  Build N programs in parallel (default: 4)"
            echo "  --help, -h     Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create build directory
mkdir -p "$BUILD_DIR"

# Statistics
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TOTAL_PROGRAMS=0
BUILT_PROGRAMS=0
FAILED_PROGRAMS=0

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          Brainhair Bootstrap & Self-Hosting Test            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

#############################################################################
# Phase 1: Compile Compiler Components
#############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 1: Compiling Compiler Components to Native x86${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

compile_component() {
    local src="$1"
    local name="$2"
    local output="$BUILD_DIR/$name"

    echo -n "  Compiling $src... "

    if python3 -c "
import sys
sys.path.insert(0, '$COMPILER_DIR')
from brainhair import Compiler
import io
from contextlib import redirect_stdout, redirect_stderr

compiler = Compiler('$COMPILER_DIR/$src', '$output',
                   kernel_mode=False, check_types=False,
                   check_ownership=False, check_lifetimes=False)

with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    success = compiler.compile()

sys.exit(0 if success else 1)
" 2>/dev/null; then
        # Verify binary runs
        if "$output" 2>/dev/null; then
            local size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null)
            echo -e "${GREEN}OK${NC} (${size} bytes)"
            return 0
        else
            echo -e "${RED}FAIL${NC} (binary crashed)"
            return 1
        fi
    else
        echo -e "${RED}FAIL${NC} (compilation error)"
        return 1
    fi
}

COMPILER_COMPONENTS=("lexer.py:lexer" "parser.py:parser" "codegen_x86.py:codegen_x86")
PHASE1_SUCCESS=true

for component in "${COMPILER_COMPONENTS[@]}"; do
    src="${component%:*}"
    name="${component#*:}"
    if ! compile_component "$src" "$name"; then
        PHASE1_SUCCESS=false
    fi
done

echo ""

if [ "$PHASE1_SUCCESS" = false ]; then
    echo -e "${RED}Phase 1 FAILED: Could not compile all compiler components${NC}"
    echo -e "${YELLOW}Continuing with tests anyway...${NC}"
fi

#############################################################################
# Phase 2: Run Unit Tests
#############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 2: Running Unit Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Expected outputs for tests
declare -A EXPECTED_OUTPUTS
EXPECTED_OUTPUTS["test_01_basic_io.bh"]="42"
EXPECTED_OUTPUTS["test_02_struct_basic.bh"]="12"
EXPECTED_OUTPUTS["test_03_strlen.bh"]="5"
EXPECTED_OUTPUTS["test_04_struct_multifield.bh"]=$'5\n104'
EXPECTED_OUTPUTS["test_05_loops_conditions.bh"]=$'5\n120'
EXPECTED_OUTPUTS["test_06_token_counter.bh"]="5"
EXPECTED_OUTPUTS["test_07_global_string.bh"]="5"

run_test() {
    local test_file="$1"
    local test_name="$(basename "$test_file")"
    local output_bin="$BUILD_DIR/${test_name%.bh}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "  $test_name: "

    # Compile
    if ! python3 -c "
import sys
sys.path.insert(0, '$COMPILER_DIR')
from brainhair import Compiler
import io
from contextlib import redirect_stdout, redirect_stderr

compiler = Compiler('$test_file', '$output_bin',
                   kernel_mode=False, check_types=False,
                   check_ownership=False, check_lifetimes=False)

with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    success = compiler.compile()

sys.exit(0 if success else 1)
" 2>/dev/null; then
        echo -e "${RED}FAIL${NC} (compilation error)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Run and capture output
    local actual_output
    if ! actual_output=$("$output_bin" 2>&1); then
        echo -e "${RED}FAIL${NC} (runtime error)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Trim trailing newline for comparison
    actual_output=$(echo -n "$actual_output" | sed 's/[[:space:]]*$//')

    # Check expected output
    local expected="${EXPECTED_OUTPUTS[$test_name]}"
    if [ -z "$expected" ]; then
        echo -e "${YELLOW}SKIP${NC} (no expected output)"
        return 0
    fi

    if [ "$actual_output" = "$expected" ]; then
        echo -e "${GREEN}PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        if [ "$VERBOSE" = true ]; then
            echo "    Expected: '$expected'"
            echo "    Got:      '$actual_output'"
        fi
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Run all .bh tests
for test_file in "$TEST_DIR"/test_*.bh; do
    if [ -f "$test_file" ]; then
        run_test "$test_file"
    fi
done

# Run Python-based self-hosting test
echo -n "  test_self_host_lexer.py: "
if python3 "$TEST_DIR/test_self_host_lexer.py" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo ""
echo -e "  Results: ${GREEN}$PASSED_TESTS passed${NC}, ${RED}$FAILED_TESTS failed${NC}, $TOTAL_TESTS total"
echo ""

if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Phase 2 FAILED: Some tests did not pass${NC}"
    if [ "$SKIP_OS" = false ]; then
        echo -e "${YELLOW}Aborting OS build. Use --skip-os to skip.${NC}"
        exit 1
    fi
fi

#############################################################################
# Phase 3: Build OS Userland
#############################################################################

if [ "$SKIP_OS" = true ]; then
    echo -e "${YELLOW}Skipping OS build (--skip-os specified)${NC}"
else
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Phase 3: Building OS Userland Programs${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Create bin directory
    mkdir -p "$BIN_DIR"

    # Count total programs
    TOTAL_PROGRAMS=$(ls "$USERLAND_DIR"/*.bh 2>/dev/null | wc -l)
    echo "  Building $TOTAL_PROGRAMS userland programs (parallel: $PARALLEL)..."
    echo ""

    # Build function
    build_program() {
        local src="$1"
        local name="$(basename "${src%.bh}")"
        local output="$BIN_DIR/$name"

        if python3 -c "
import sys
sys.path.insert(0, '$COMPILER_DIR')
from brainhair import Compiler
import io
from contextlib import redirect_stdout, redirect_stderr

compiler = Compiler('$src', '$output',
                   kernel_mode=False, check_types=False,
                   check_ownership=False, check_lifetimes=False)

with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    success = compiler.compile()

sys.exit(0 if success else 1)
" 2>/dev/null; then
            echo "OK:$name"
        else
            echo "FAIL:$name"
        fi
    }

    export -f build_program
    export COMPILER_DIR BIN_DIR

    # Build all programs in parallel and collect results
    RESULTS=$(ls "$USERLAND_DIR"/*.bh | xargs -P "$PARALLEL" -I {} bash -c 'build_program "$@"' _ {})

    # Count results
    BUILT_PROGRAMS=$(echo "$RESULTS" | grep -c "^OK:" || true)
    FAILED_PROGRAMS=$(echo "$RESULTS" | grep -c "^FAIL:" || true)

    # Show failures if any
    if [ $FAILED_PROGRAMS -gt 0 ]; then
        echo -e "  ${RED}Failed programs:${NC}"
        echo "$RESULTS" | grep "^FAIL:" | sed 's/^FAIL:/    /'
        echo ""
    fi

    echo -e "  Results: ${GREEN}$BUILT_PROGRAMS built${NC}, ${RED}$FAILED_PROGRAMS failed${NC}, $TOTAL_PROGRAMS total"
    echo ""
fi

#############################################################################
# Summary
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Bootstrap Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Compiler Components:"
if [ "$PHASE1_SUCCESS" = true ]; then
    echo -e "    ${GREEN}✓ All 3 components compiled successfully${NC}"
else
    echo -e "    ${RED}✗ Some components failed to compile${NC}"
fi
echo ""
echo "  Unit Tests:"
echo -e "    ${GREEN}✓ $PASSED_TESTS passed${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "    ${RED}✗ $FAILED_TESTS failed${NC}"
fi
echo ""

if [ "$SKIP_OS" = false ]; then
    echo "  OS Userland:"
    echo -e "    ${GREEN}✓ $BUILT_PROGRAMS programs built${NC}"
    if [ $FAILED_PROGRAMS -gt 0 ]; then
        echo -e "    ${RED}✗ $FAILED_PROGRAMS programs failed${NC}"
    fi
    echo ""
fi

# Final status
if [ "$PHASE1_SUCCESS" = true ] && [ $FAILED_TESTS -eq 0 ] && [ $FAILED_PROGRAMS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Bootstrap completed successfully!               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║           Bootstrap completed with some failures             ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
