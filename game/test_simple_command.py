#!/usr/bin/env python3
"""
Simple test to isolate where the hang occurs
"""

import signal
from scenarios import create_scenario_zero

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Timed out!")

print("=" * 80)
print("SIMPLE COMMAND TEST")
print("=" * 80)

# Test 1: Create scenario
print("\n[TEST 1] Creating scenario...")
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)
try:
    attacker, network, metadata = create_scenario_zero()
    signal.alarm(0)
    print("✓ Scenario created successfully")
except TimeoutError:
    print("✗ HANGS during scenario creation")
    exit(1)

# Test 2: Boot system
print("\n[TEST 2] Booting system...")
signal.alarm(5)
try:
    attacker.boot()
    signal.alarm(0)
    print("✓ Boot completed successfully")
except TimeoutError:
    print("✗ HANGS during boot")
    exit(1)

# Test 3: Login
print("\n[TEST 3] Logging in as root/root...")
signal.alarm(5)
try:
    success = attacker.login('root', 'root')
    signal.alarm(0)
    if not success:
        print("✗ Login failed (wrong credentials)")
        exit(1)
    print(f"✓ Login succeeded")
    print(f"  shell_pid = {attacker.shell_pid}")
except TimeoutError:
    print("✗ HANGS during login")
    exit(1)

# Test 4: Simple execute_command
print("\n[TEST 4] Testing execute_command('pwd')...")
signal.alarm(5)
try:
    exit_code, stdout, stderr = attacker.execute_command('pwd')
    signal.alarm(0)
    print(f"✓ Command completed!")
    print(f"  Exit code: {exit_code}")
    print(f"  Stdout: {repr(stdout)}")
    print(f"  Stderr: {repr(stderr)}")
except TimeoutError:
    print("✗ HANGS during execute_command")
    print("\n=== DIAGNOSIS ===")
    print("The hang occurs in execute_command('pwd')")
    print("This is the critical bug blocking all gameplay!")
    exit(1)

print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED - COMMAND EXECUTION WORKS!")
print("=" * 80)
