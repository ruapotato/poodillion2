#!/usr/bin/env python3
"""
Test various commands to ensure they work properly
"""

from scenarios import create_scenario_zero

print("=" * 80)
print("COMMAND FUNCTIONALITY TEST")
print("=" * 80)

# Create and boot scenario
print("\n1. Setting up test environment...")
attacker, network, metadata = create_scenario_zero()
attacker.boot()
attacker.login('root', 'root')
print("✓ System ready")

# Test commands
commands_to_test = [
    ('pwd', 'Print working directory'),
    ('ls /', 'List root directory'),
    ('cat /etc/hostname', 'Read hostname file'),
    ('echo "Hello World"', 'Echo command'),
    ('whoami', 'Show current user'),
    ('hostname', 'Show hostname'),
    ('date', 'Show date'),
    ('ps', 'Show processes'),
    ('ifconfig', 'Show network interfaces'),
]

print(f"\n2. Testing {len(commands_to_test)} commands:")
print()

passed = 0
failed = 0

for cmd, description in commands_to_test:
    print(f"  [{description}]")
    print(f"    Command: {cmd}")

    try:
        exit_code, stdout, stderr = attacker.execute_command(cmd)

        if exit_code == 0:
            print(f"    ✓ Exit code: 0")
            if stdout.strip():
                # Show first line of output
                first_line = stdout.strip().split('\n')[0]
                if len(first_line) > 60:
                    first_line = first_line[:60] + '...'
                print(f"    Output: {first_line}")
            passed += 1
        else:
            print(f"    ✗ Exit code: {exit_code}")
            if stderr.strip():
                print(f"    Error: {stderr.strip()}")
            failed += 1
    except Exception as e:
        print(f"    ✗ Exception: {e}")
        failed += 1

    print()

# Summary
print("=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(commands_to_test)} tests")
print("=" * 80)

if failed == 0:
    print("\n✓ ALL COMMANDS WORKING!")
else:
    print(f"\n⚠ {failed} commands need attention")
