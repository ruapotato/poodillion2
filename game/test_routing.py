#!/usr/bin/env python3
"""
Test multi-hop routing through routers
"""

from core.system import UnixSystem
from core.network import VirtualNetwork


def test_multi_hop_routing():
    """Test that packets can route through intermediate systems"""
    print("=== Multi-Hop Routing Test ===\n")

    network = VirtualNetwork()

    # Create attacker (external network)
    attacker = UnixSystem('attacker', '10.0.0.100')
    attacker.add_network(network)
    print(f"Created: {attacker.hostname} at {attacker.ip}")

    # Create router with TWO interfaces (this is the key!)
    router = UnixSystem('router', {
        'eth0': '10.0.0.1',      # External interface
        'eth1': '192.168.1.1'    # Internal interface
    })
    router.add_network(network)
    router.ip_forward = True  # Enable routing!
    print(f"Created: {router.hostname} with interfaces:")
    for iface, ip in router.interfaces.items():
        print(f"  {iface}: {ip}")
    print(f"  IP Forwarding: {router.ip_forward}")

    # Create web server (internal network)
    webserver = UnixSystem('webserver', '192.168.1.50')
    webserver.add_network(network)
    print(f"Created: {webserver.hostname} at {webserver.ip}")

    print("\n" + "="*60)
    print("Network Topology:")
    print("="*60)
    print("Attacker (10.0.0.100)")
    print("    |")
    print("    v")
    print("Router (10.0.0.1 / 192.168.1.1) [ip_forward=True]")
    print("    |")
    print("    v")
    print("Webserver (192.168.1.50)")
    print("="*60 + "\n")

    # Add network routes (layer 2 connectivity)
    print("Adding network routes...")
    # Attacker can reach router's external interface
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.100')
    print("  10.0.0.100 <-> 10.0.0.1")

    # Router's internal interface can reach webserver
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')
    print("  192.168.1.1 <-> 192.168.1.50")

    print("\n" + "="*60)
    print("Testing Connectivity")
    print("="*60)

    # Test 1: Attacker to router (direct)
    result = network.can_connect('10.0.0.100', '10.0.0.1')
    print(f"1. Attacker → Router (10.0.0.1): {'✓ SUCCESS' if result else '✗ FAIL'}")
    if result:
        path = network._find_route_path('10.0.0.100', '10.0.0.1')
        print(f"   Path: {' → '.join(path) if path else 'No path'}")

    # Test 2: Router to webserver (direct)
    result = network.can_connect('192.168.1.1', '192.168.1.50')
    print(f"2. Router → Webserver (192.168.1.50): {'✓ SUCCESS' if result else '✗ FAIL'}")
    if result:
        path = network._find_route_path('192.168.1.1', '192.168.1.50')
        print(f"   Path: {' → '.join(path) if path else 'No path'}")

    # Test 3: Attacker to webserver (MULTI-HOP through router!)
    result = network.can_connect('10.0.0.100', '192.168.1.50')
    print(f"3. Attacker → Webserver (192.168.1.50) [MULTI-HOP]: {'✓ SUCCESS' if result else '✗ FAIL'}")
    if result:
        path = network._find_route_path('10.0.0.100', '192.168.1.50')
        print(f"   Path: {' → '.join(path) if path else 'No path'}")
    else:
        print("   ✗ FAILED: Should route through 10.0.0.1!")

    # Test 4: Localhost always works
    result = network.can_connect('10.0.0.100', '127.0.0.1')
    print(f"4. Localhost (127.0.0.1): {'✓ SUCCESS' if result else '✗ FAIL'}")

    # Test 5: Own IP always works
    result = network.can_connect('10.0.0.100', '10.0.0.100')
    print(f"5. Own IP (10.0.0.100): {'✓ SUCCESS' if result else '✗ FAIL'}")

    print("\n" + "="*60)
    print("Testing with IP Forwarding DISABLED")
    print("="*60)

    # Disable IP forwarding on router
    router.ip_forward = False
    print(f"Router IP forwarding: {router.ip_forward}")

    result = network.can_connect('10.0.0.100', '192.168.1.50')
    print(f"Attacker → Webserver: {'✓ CONNECTED' if result else '✗ BLOCKED (expected)'}")
    if not result:
        print("   ✓ Correctly blocked - router not forwarding!")

    # Re-enable for remaining tests
    router.ip_forward = True

    print("\n" + "="*60)
    print("Testing Firewall")
    print("="*60)

    # Add firewall rule on webserver to block SSH
    webserver.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'tcp',
        'port': 22,
        'action': 'DROP',
        'source': 'any'
    })
    print("Added rule: DROP tcp port 22 from any")

    result_http = network.can_connect('10.0.0.100', '192.168.1.50', port=80)
    result_ssh = network.can_connect('10.0.0.100', '192.168.1.50', port=22)

    print(f"Attacker → Webserver:80 (HTTP): {'✓ ALLOWED' if result_http else '✗ BLOCKED'}")
    print(f"Attacker → Webserver:22 (SSH): {'✗ BLOCKED (expected)' if not result_ssh else '✓ ALLOWED (unexpected!)'}")

    print("\n" + "="*60)
    print("All Routing Tests Complete!")
    print("="*60)


if __name__ == '__main__':
    test_multi_hop_routing()
