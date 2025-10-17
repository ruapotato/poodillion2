#!/usr/bin/env python3
"""
Test the interactive shell flow with SSH
"""

from scenarios import create_scenario_zero
import sys

# Create scenario
attacker, network, metadata = create_scenario_zero()

# Boot all systems
print("=== Booting all systems ===")
for system in metadata['systems']:
    system.boot()

print("\n=== Testing interactive_shell simulation ===")

# Simulate what happens when we SSH

# 1. Login to attacker
print("\n1. Login to attacker")
success = attacker.login('root', 'root')
print(f"   Login successful: {success}")
print(f"   Shell PID: {attacker.shell_pid}")

# 2. Execute SSH command (simulated)
print("\n2. Simulating SSH command execution")
# Create the SSH request file manually
ssh_request = "root|192.168.1.10\n"
try:
    attacker.vfs.create_file('/tmp/.ssh_request', 0o644, 0, 0, ssh_request.encode(), 1)
    print("   SSH request file created")
except:
    print("   Failed to create SSH request file")

# 3. Read the SSH request (simulating what interactive_shell does)
print("\n3. Reading SSH request")
request_data = attacker.vfs.read_file('/tmp/.ssh_request', 1)
if request_data:
    request = request_data.decode('utf-8', errors='ignore').strip()
    print(f"   Request: {request}")
    target_user, target_host = request.split('|', 1)
    print(f"   Target: {target_user}@{target_host}")

    # 4. Get target system
    print("\n4. Getting target system")
    target_system = network.systems.get(target_host)
    if target_system:
        print(f"   Found: {target_system.hostname}")
        print(f"   Is alive: {target_system.is_alive()}")
        print(f"   Current shell_pid: {target_system.shell_pid}")

        # 5. Try to login to target
        print("\n5. Attempting login to target")
        login_success = target_system.login(target_user, 'root')
        print(f"   Login successful: {login_success}")
        print(f"   New shell_pid: {target_system.shell_pid}")

        if login_success:
            # 6. Try to execute a simple command
            print("\n6. Testing command execution on target")
            proc = target_system.processes.get_process(target_system.shell_pid)
            if proc:
                print(f"   Process found: PID={proc.pid}, UID={proc.uid}")
            else:
                print("   ERROR: Process not found!")

            # Try executing hostname
            exit_code, stdout, stderr = target_system.execute_command('hostname')
            print(f"   hostname exit_code: {exit_code}")
            print(f"   hostname stdout: {stdout}")
            print(f"   hostname stderr: {stderr}")
    else:
        print(f"   ERROR: System {target_host} not found in network!")
else:
    print("   ERROR: No SSH request found!")

print("\n=== Complete ===")
