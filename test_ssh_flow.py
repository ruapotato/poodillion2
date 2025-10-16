#!/usr/bin/env python3
"""
Test SSH flow to debug the issue
"""

from scenarios import create_scenario_zero

# Create scenario
attacker, network, metadata = create_scenario_zero()

# Boot all systems
print("=== Booting systems ===")
for system in metadata['systems']:
    system.boot()

print("\n=== Testing SSH command directly ===")

# Login to attacker
attacker.login('root', 'root')

# Test SSH command directly
print("Executing: ssh 192.168.1.10")
exit_code, stdout, stderr = attacker.execute_command('ssh 192.168.1.10')
print(f"Exit code: {exit_code}")
print(f"Stdout: {stdout}")
print(f"Stderr: {stderr}")

# Check if SSH request was written
ssh_request = attacker.vfs.read_file('/tmp/.ssh_request', 1)
if ssh_request:
    print(f"\nSSH request file contents: {ssh_request.decode()}")
else:
    print("\nNo SSH request file found!")

print("\n=== Testing pooshell behavior ===")

# Create a test script that runs ssh and checks exit code
test_script = """#!/usr/bin/pooscript
print("Running SSH command...")
exit_code, stdout, stderr = process.execute('ssh 192.168.1.10')
print(f"SSH exit code: {exit_code}")
exit(exit_code)
"""

# Write test script
attacker.vfs.create_file('/tmp/test_ssh.psh', 0o755, 0, 0, test_script.encode(), 1)

# Execute test script
print("Executing test script...")
exit_code, stdout, stderr = attacker.shell.execute('/tmp/test_ssh.psh', attacker.shell_pid, b'')
print(f"Test script exit code: {exit_code}")
print(f"Test script stdout: {stdout.decode()}")
print(f"Test script stderr: {stderr.decode()}")

print("\n=== Complete ===")
