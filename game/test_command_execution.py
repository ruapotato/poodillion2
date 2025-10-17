#!/usr/bin/env python3
"""
Test command execution to see if execute_command still hangs
"""

import signal
from scenarios import create_scenario_zero

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Command execution timed out!")

def test_command_execution():
    """Test if commands can execute without hanging"""

    print("=" * 80)
    print("TESTING COMMAND EXECUTION")
    print("=" * 80)

    # Create scenario 0 (simplest one)
    print("\n1. Creating scenario...")
    attacker, network, metadata = create_scenario_zero()
    print("✓ Scenario created")

    # Boot attacker system
    print("\n2. Booting attacker system...")
    attacker.boot()
    print("✓ System booted")

    # Login
    print("\n3. Logging in as root...")
    success = attacker.login('root', 'root')
    if not success:
        print(f"✗ Login failed")
        return
    print("✓ Logged in successfully")

    # Try executing a simple command with timeout
    print("\n4. Testing command execution (5 second timeout)...")
    print("   Executing: pwd")

    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)  # 5 second timeout

    try:
        exit_code, stdout, stderr = attacker.execute_command('pwd')
        signal.alarm(0)  # Cancel alarm

        print(f"✓ Command executed successfully!")
        print(f"   Exit code: {exit_code}")
        print(f"   Stdout: {repr(stdout)}")
        print(f"   Stderr: {repr(stderr)}")

        # Try another command
        print("\n5. Testing another command: ls /")
        signal.alarm(5)
        exit_code, stdout, stderr = attacker.execute_command('ls /')
        signal.alarm(0)

        print(f"✓ Second command executed!")
        print(f"   Exit code: {exit_code}")
        print(f"   Stdout: {repr(stdout)}")
        print(f"   Stderr: {repr(stderr)}")

        print("\n" + "=" * 80)
        print("✓ COMMAND EXECUTION WORKS!")
        print("=" * 80)

    except TimeoutError as e:
        signal.alarm(0)
        print(f"\n✗ COMMAND EXECUTION STILL HANGS")
        print(f"   Error: {e}")
        print("\n   This means the execute_command bug is still present.")
        print("   Need to investigate Shell.execute() and /bin/pooshell")
        return False
    except Exception as e:
        signal.alarm(0)
        print(f"\n✗ Command failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == '__main__':
    test_command_execution()
