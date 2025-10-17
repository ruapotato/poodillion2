#!/usr/bin/env python3
"""
Minimal test - just check if systems can be created and logged into
"""

from core.system import UnixSystem
from core.network import VirtualNetwork

print("Creating network...")
network = VirtualNetwork()

print("Creating systems...")
sys1 = UnixSystem('box1', '192.168.1.100')
sys2 = UnixSystem('box2', '192.168.1.10')

print("Adding to network...")
sys1.add_network(network)
sys2.add_network(network)

print("Connecting...")
network.add_route('192.168.1.100', '192.168.1.10')
network.add_route('192.168.1.10', '192.168.1.100')

print("Booting sys1...")
sys1.boot()

print("Booting sys2...")
sys2.boot()

print("Logging into sys1...")
result = sys1.login('root', 'root')
print(f"Login result: {result}, shell_pid: {sys1.shell_pid}")

print("Logging into sys2...")
result = sys2.login('root', 'root')
print(f"Login result: {result}, shell_pid: {sys2.shell_pid}")

print("Testing if sys2 is alive...")
print(f"sys2.is_alive(): {sys2.is_alive()}")

print("Complete!")
