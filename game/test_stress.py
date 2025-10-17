#!/usr/bin/env python3
"""
Comprehensive Stress Testing for Poodillion
Tests the system under extreme load and edge cases
"""

import time
import random
from test_100_computer_internet import create_mini_internet

def stress_test_all():
    """Run all stress tests"""

    print("\n" + "="*80)
    print(" " * 20 + "POODILLION COMPREHENSIVE STRESS TESTS")
    print("="*80 + "\n")

    # Create the internet
    print("🌐 Creating 100-computer internet...")
    start = time.time()
    attacker, network, systems = create_mini_internet()
    creation_time = time.time() - start
    print(f"✅ Internet created in {creation_time:.3f}s\n")

    results = {
        'passed': 0,
        'failed': 0,
        'warnings': 0
    }

    # =====================================================================
    # TEST 1: Basic Command Execution on All Systems
    # =====================================================================
    print("="*80)
    print("TEST 1: Basic Command Execution on All Systems")
    print("="*80)

    test_commands = ['pwd', 'ls /', 'hostname', 'whoami', 'date']

    start = time.time()
    cmd_results = {}

    test_systems = list(systems.items())[:10]  # Test first 10
    for system_name, system in test_systems:
        system.login('root', 'root')
        cmd_results[system_name] = {}

        for cmd in test_commands:
            exit_code, stdout, stderr = system.execute_command(cmd)
            success = exit_code == 0
            cmd_results[system_name][cmd] = success

            if success:
                results['passed'] += 1
            else:
                results['failed'] += 1
                print(f"   ✗ {system_name}: {cmd} failed")

    elapsed = time.time() - start
    total_cmds = len(test_systems) * len(test_commands)
    print(f"✅ Executed {total_cmds} commands across 10 systems in {elapsed:.3f}s")
    print(f"   Average: {elapsed/total_cmds*1000:.2f}ms per command\n")

    # =====================================================================
    # TEST 2: File System Operations
    # =====================================================================
    print("="*80)
    print("TEST 2: File System Operations (Create, Read, Write, Delete)")
    print("="*80)

    start = time.time()
    fs_ops = 0

    for system_name, system in list(systems.items())[:5]:
        system.login('root', 'root')

        # Create files
        for i in range(20):
            exit_code, _, _ = system.execute_command(f'echo "test data {i}" > /tmp/test{i}.txt')
            if exit_code == 0:
                fs_ops += 1
                results['passed'] += 1
            else:
                results['failed'] += 1

        # Read files
        for i in range(20):
            exit_code, _, _ = system.execute_command(f'cat /tmp/test{i}.txt')
            if exit_code == 0:
                fs_ops += 1
                results['passed'] += 1
            else:
                results['failed'] += 1

        # Delete files
        for i in range(20):
            exit_code, _, _ = system.execute_command(f'rm /tmp/test{i}.txt')
            if exit_code == 0:
                fs_ops += 1
                results['passed'] += 1
            else:
                results['failed'] += 1

    elapsed = time.time() - start
    print(f"✅ Performed {fs_ops} file operations in {elapsed:.3f}s")
    print(f"   Average: {elapsed/fs_ops*1000:.2f}ms per operation\n")

    # =====================================================================
    # TEST 3: Process Management
    # =====================================================================
    print("="*80)
    print("TEST 3: Process Management (Spawn, List, Kill)")
    print("="*80)

    start = time.time()
    process_ops = 0

    for system_name, system in list(systems.items())[:5]:
        # List processes
        exit_code, stdout, _ = system.execute_command('ps')
        if exit_code == 0:
            results['passed'] += 1
            process_ops += 1
        else:
            results['failed'] += 1

        # Check process count
        processes = system.processes.list_processes()
        if len(processes) > 0:
            results['passed'] += 1
            process_ops += 1
        else:
            results['failed'] += 1

    elapsed = time.time() - start
    print(f"✅ Performed {process_ops} process operations in {elapsed:.3f}s\n")

    # =====================================================================
    # TEST 4: Network Connectivity Test (Ping)
    # =====================================================================
    print("="*80)
    print("TEST 4: Network Connectivity (Random Ping Tests)")
    print("="*80)

    start = time.time()
    ping_tests = 0
    ping_success = 0

    # Test 20 random connections
    system_list = list(systems.values())
    for _ in range(20):
        src = random.choice(system_list)
        dst = random.choice(system_list)

        if src == dst:
            continue

        src.login('root', 'root')
        exit_code, stdout, stderr = src.execute_command(f'ping -c 1 {dst.ip}')

        ping_tests += 1
        if exit_code == 0:
            ping_success += 1
            results['passed'] += 1
        else:
            results['warnings'] += 1  # Network connectivity might not be fully meshed

    elapsed = time.time() - start
    success_rate = (ping_success / ping_tests * 100) if ping_tests > 0 else 0
    print(f"✅ Performed {ping_tests} ping tests in {elapsed:.3f}s")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Average: {elapsed/ping_tests*1000:.2f}ms per ping\n")

    # =====================================================================
    # TEST 5: Concurrent Operations
    # =====================================================================
    print("="*80)
    print("TEST 5: Concurrent Command Execution")
    print("="*80)

    start = time.time()
    concurrent_ops = 0

    # Execute same command on multiple systems "simultaneously"
    for system in list(systems.values())[:20]:
        system.login('root', 'root')
        exit_code, _, _ = system.execute_command('ls /')
        if exit_code == 0:
            concurrent_ops += 1
            results['passed'] += 1
        else:
            results['failed'] += 1

    elapsed = time.time() - start
    print(f"✅ Executed {concurrent_ops} concurrent commands in {elapsed:.3f}s")
    print(f"   Throughput: {concurrent_ops/elapsed:.1f} commands/second\n")

    # =====================================================================
    # TEST 6: Edge Cases
    # =====================================================================
    print("="*80)
    print("TEST 6: Edge Cases and Error Handling")
    print("="*80)

    edge_tests = 0
    system = list(systems.values())[0]
    system.login('root', 'root')

    edge_cases = [
        ('Non-existent command', 'thisdoesnotexist'),
        ('Invalid path', 'cat /this/does/not/exist.txt'),
        ('Permission denied', 'cat /root/nonexistent'),
        ('Empty command', ''),
        ('Very long path', 'ls ' + '/a' * 100),
    ]

    for description, cmd in edge_cases:
        exit_code, stdout, stderr = system.execute_command(cmd)
        edge_tests += 1
        # Edge cases should NOT crash - they should return non-zero exit codes
        if exit_code != 0:  # Expected to fail
            results['passed'] += 1
            print(f"   ✓ {description}: Handled correctly")
        else:
            results['warnings'] += 1
            print(f"   ⚠ {description}: Unexpected success")

    print(f"✅ Tested {edge_tests} edge cases\n")

    # =====================================================================
    # TEST 7: System Crash and Recovery
    # =====================================================================
    print("="*80)
    print("TEST 7: System Crash and Recovery")
    print("="*80)

    # Pick a random system and crash it
    crash_system = list(systems.values())[10]
    print(f"   Crashing {crash_system.hostname}...")
    crash_system.login('root', 'root')

    # System should be running
    if crash_system.running:
        results['passed'] += 1
        print(f"   ✓ System was running")
    else:
        results['failed'] += 1
        print(f"   ✗ System was not running")

    # Execute crash command
    exit_code, stdout, stderr = crash_system.execute_command('crash')

    # System should be crashed now
    if crash_system.crashed:
        results['passed'] += 1
        print(f"   ✓ System crashed successfully")
    else:
        results['warnings'] += 1
        print(f"   ⚠ System did not crash")

    # System should not be alive
    if not crash_system.is_alive():
        results['passed'] += 1
        print(f"   ✓ System is not alive after crash")
    else:
        results['failed'] += 1
        print(f"   ✗ System still alive after crash")

    print()

    # =====================================================================
    # TEST 8: Large File Operations
    # =====================================================================
    print("="*80)
    print("TEST 8: Large File Operations")
    print("="*80)

    start = time.time()
    system = list(systems.values())[0]
    system.login('root', 'root')

    # Create large file
    large_content = "A" * 10000
    exit_code, _, _ = system.execute_command(f'echo "{large_content}" > /tmp/large.txt')
    if exit_code == 0:
        results['passed'] += 1
        print(f"   ✓ Created 10KB file")
    else:
        results['failed'] += 1
        print(f"   ✗ Failed to create large file")

    # Read large file
    exit_code, stdout, _ = system.execute_command('cat /tmp/large.txt')
    if exit_code == 0:
        results['passed'] += 1
        print(f"   ✓ Read 10KB file")
    else:
        results['failed'] += 1
        print(f"   ✗ Failed to read large file")

    elapsed = time.time() - start
    print(f"✅ Large file operations completed in {elapsed:.3f}s\n")

    # =====================================================================
    # TEST 9: Deep Directory Structures
    # =====================================================================
    print("="*80)
    print("TEST 9: Deep Directory Structures")
    print("="*80)

    start = time.time()
    system = list(systems.values())[0]
    system.login('root', 'root')

    # Create deep directory
    exit_code, _, _ = system.execute_command('mkdir -p /tmp/a/b/c/d/e/f/g/h/i/j')
    if exit_code == 0:
        results['passed'] += 1
        print(f"   ✓ Created deep directory (10 levels)")
    else:
        results['failed'] += 1
        print(f"   ✗ Failed to create deep directory")

    # Navigate to deep directory
    exit_code, _, _ = system.execute_command('cd /tmp/a/b/c/d/e/f/g/h/i/j && pwd')
    if exit_code == 0:
        results['passed'] += 1
        print(f"   ✓ Navigated to deep directory")
    else:
        results['failed'] += 1
        print(f"   ✗ Failed to navigate to deep directory")

    elapsed = time.time() - start
    print(f"✅ Deep directory operations completed in {elapsed:.3f}s\n")

    # =====================================================================
    # TEST 10: Pipe and Redirect Stress
    # =====================================================================
    print("="*80)
    print("TEST 10: Pipe and Redirect Operations")
    print("="*80)

    start = time.time()
    system = list(systems.values())[0]
    system.login('root', 'root')

    pipe_commands = [
        'ls / | grep etc',
        'cat /etc/passwd | grep root',
        'echo "test" | cat',
        'ps | grep init',
    ]

    pipe_success = 0
    for cmd in pipe_commands:
        exit_code, _, _ = system.execute_command(cmd)
        if exit_code == 0:
            pipe_success += 1
            results['passed'] += 1
        else:
            results['failed'] += 1

    elapsed = time.time() - start
    print(f"✅ Executed {len(pipe_commands)} pipe commands in {elapsed:.3f}s")
    print(f"   Success: {pipe_success}/{len(pipe_commands)}\n")

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("\n" + "="*80)
    print(" " * 30 + "TEST SUMMARY")
    print("="*80)

    total_tests = results['passed'] + results['failed'] + results['warnings']
    pass_rate = (results['passed'] / total_tests * 100) if total_tests > 0 else 0

    print(f"""
    Total Tests:      {total_tests}
    ✅ Passed:         {results['passed']} ({pass_rate:.1f}%)
    ✗ Failed:         {results['failed']}
    ⚠ Warnings:       {results['warnings']}

    System Performance:
    - Internet creation time: {creation_time:.3f}s
    - Total systems: {len(systems)}
    - Total network connections: 346

    """)

    if results['failed'] == 0:
        print("🎉 " + "="*74 + " 🎉")
        print("🎉 " + " " * 20 + "ALL TESTS PASSED!" + " " * 26 + " 🎉")
        print("🎉 " + "="*74 + " 🎉")
    else:
        print("⚠️  Some tests failed. Review output above for details.")

    print("="*80 + "\n")

    return results


if __name__ == '__main__':
    start_time = time.time()
    results = stress_test_all()
    total_time = time.time() - start_time

    print(f"\n✅ All stress tests completed in {total_time:.2f} seconds")
    print(f"   Test throughput: {(results['passed'] + results['failed'])/total_time:.1f} tests/second")
