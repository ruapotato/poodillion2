#!/usr/bin/env python3
"""
Simple SSH test - check if SSH binary works
"""

from core.system import UnixSystem
from core.network import VirtualNetwork

# Create minimal network
network = VirtualNetwork()

# Create two systems
sys1 = UnixSystem('box1', '192.168.1.100')
sys1.add_network(network)
sys1.boot()
sys1.login('root', 'root')

sys2 = UnixSystem('box2', '192.168.1.10')
sys2.add_network(network)
sys2.boot()
sys2.login('root', 'root')

# Connect them
network.add_route('192.168.1.100', '192.168.1.10')
network.add_route('192.168.1.10', '192.168.1.100')

print("=== Testing SSH binary directly ===")

# Read SSH binary
ssh_binary = sys1.vfs.read_file('/bin/ssh', 1)
if ssh_binary:
    print(f"SSH binary exists, size: {len(ssh_binary)} bytes")
    print("First 100 chars:", ssh_binary[:100])
else:
    print("SSH binary not found!")

print("\n=== Testing execute_pooscript ===")
from core.pooscript import execute_pooscript

# Get process
proc = sys1.processes.get_process(sys1.shell_pid)

# Execute SSH directly via pooscript
args = ['192.168.1.10']
exit_code, stdout, stderr = execute_pooscript(
    ssh_binary,
    args,
    b'',
    proc.env,
    sys1.vfs,
    proc,
    sys1.processes,
    sys1.shell.executor,
    None,  # input callback
    None,  # output callback
    None,  # error callback
    network,
    sys1.ip
)

print(f"Exit code: {exit_code}")
print(f"Stdout: {stdout.decode()}")
print(f"Stderr: {stderr.decode()}")

# Check SSH request file
ssh_req = sys1.vfs.read_file('/tmp/.ssh_request', 1)
if ssh_req:
    print(f"\nSSH request written: {ssh_req.decode()}")
else:
    print("\nNo SSH request file!")

print("\n=== Complete ===")
