#!/usr/bin/env python3
"""
Quick test of SSH and network emulation features
"""

from scenarios import create_scenario_zero

# Create scenario
attacker, network, metadata = create_scenario_zero()

# Boot all systems
print("=== Booting all systems ===")
for system in metadata['systems']:
    print(f"Booting {system.hostname} ({system.ip})...")
    system.boot()

print("\n=== Testing network state ===")
# Verify all systems are alive
for system in metadata['systems']:
    status = "ALIVE" if system.is_alive() else "DOWN"
    print(f"{system.hostname} ({system.ip}): {status}")

print("\n=== Testing routing with all systems up ===")
# Test routing from attacker to gamma
from_ip = '192.168.1.100'
to_ip = '192.168.1.30'
can_reach = network.can_connect(from_ip, to_ip)
print(f"Can reach {to_ip} from {from_ip}: {can_reach}")

# Test route path
path = network._find_route_path(from_ip, to_ip)
if path:
    print(f"Route path: {' -> '.join(path)}")

print("\n=== Shutting down server-alpha ===")
server_alpha = network.systems.get('192.168.1.10')
if server_alpha:
    server_alpha.shutdown()
    print(f"server-alpha is_alive: {server_alpha.is_alive()}")

print("\n=== Testing routing with server-alpha down ===")
# Test routing to alpha (should fail)
can_reach_alpha = network.can_connect(from_ip, '192.168.1.10')
print(f"Can reach 192.168.1.10 from {from_ip}: {can_reach_alpha}")

# Test routing to gamma (should still work - not through alpha)
can_reach_gamma = network.can_connect(from_ip, '192.168.1.30')
print(f"Can reach {to_ip} from {from_ip}: {can_reach_gamma}")

print("\n=== Testing router shutdown ===")
router = network.systems.get('192.168.1.1')
if router:
    print("Shutting down router...")
    router.shutdown()
    print(f"router is_alive: {router.is_alive()}")

# Now nothing should be reachable if router is needed
can_reach_after_router = network.can_connect(from_ip, to_ip)
print(f"Can reach {to_ip} from {from_ip} (router down): {can_reach_after_router}")

print("\n=== Test complete ===")
