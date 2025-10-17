#!/usr/bin/env python3
"""
Test packet-level firewall enforcement
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter


def test_icmp_firewall():
    """Test that ICMP packets are blocked by firewall rules"""
    print("Testing packet-level ICMP firewall...")

    # Create network
    network = NetworkAdapter()

    # Create two systems
    gateway = UnixSystem('gateway', '192.168.13.1')
    kali = UnixSystem('kali-box', '192.168.13.37')

    # Add to network
    gateway.add_network(network)
    kali.add_network(network)

    # Connect them on same subnet
    network.add_route('192.168.13.1', '192.168.13.37')
    network.add_route('192.168.13.37', '192.168.13.1')

    # Boot systems
    gateway.boot(verbose=False)
    kali.boot(verbose=False)

    # Login to systems
    gateway.login('root', 'root')
    kali.login('root', 'root')

    # Test that execute_command works
    ec, out, err = kali.execute_command('echo "test"')
    print(f"   [DEBUG ECHO] ec={ec}, out='{out}', err='{err}'")

    print("\n1. Testing without firewall (should work)...")
    ec, out, err = kali.execute_command('ping -c 1 192.168.13.1')
    result = out + err
    print(f"   [DEBUG PING] ec={ec}, out='{out}', err='{err}'")
    if '1 packets transmitted, 1 received' in result:
        print("   ✓ Ping successful (no firewall)")
    else:
        print("   ✗ Ping failed (unexpected)")
        if result:
            print(f"   Result: {result}")

    print("\n2. Adding firewall rule to block all ICMP on gateway...")
    # Add firewall rule to block all ICMP
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': 'any'
    })

    print("\n3. Testing with firewall (should fail)...")
    ec, out, err = kali.execute_command('ping -c 1 192.168.13.1')
    result = out + err
    if '0 packets transmitted, 0 received' in result or '0 received' in result:
        print("   ✓ Ping blocked by firewall (expected)")
    else:
        print("   ✗ Ping succeeded (firewall not working!)")
        print(result)

    print("\n4. Testing ICMP block from specific source...")
    gateway.firewall_rules.clear()
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': '192.168.13.37'
    })

    ec, out, err = kali.execute_command('ping -c 1 192.168.13.1')
    result = out + err
    if '0 packets transmitted, 0 received' in result or '0 received' in result:
        print("   ✓ Ping from specific source blocked (expected)")
    else:
        print("   ✗ Ping succeeded (source filtering not working!)")
        print(result)

    print("\n5. Testing ICMP block by subnet...")
    gateway.firewall_rules.clear()
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': '192.168.13.0/24'
    })

    ec, out, err = kali.execute_command('ping -c 1 192.168.13.1')
    result = out + err
    if '0 packets transmitted, 0 received' in result or '0 received' in result:
        print("   ✓ Ping from subnet blocked (expected)")
    else:
        print("   ✗ Ping succeeded (subnet filtering not working!)")
        print(result)

    print("\n✓ Packet-level firewall test complete")


def test_tcp_firewall():
    """Test that TCP packets are blocked by firewall rules"""
    print("\n\nTesting packet-level TCP firewall...")

    # Create network
    network = NetworkAdapter()

    # Create two systems
    server = UnixSystem('webserver', '192.168.1.100')
    client = UnixSystem('client', '192.168.1.10')

    # Add to network
    server.add_network(network)
    client.add_network(network)

    # Connect them
    network.add_route('192.168.1.100', '192.168.1.10')
    network.add_route('192.168.1.10', '192.168.1.100')

    # Boot systems
    server.boot(verbose=False)
    client.boot(verbose=False)

    # Login to systems
    server.login('root', 'root')
    client.login('root', 'root')

    print("\n1. Adding firewall rule to block SSH (port 22)...")
    server.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'tcp',
        'port': 22,
        'action': 'DROP',
        'source': 'any'
    })

    # The VirtualNetwork.can_connect() should now fail due to firewall
    can_connect = network.virtual_network.can_connect('192.168.1.10', '192.168.1.100', 22)
    if not can_connect:
        print("   ✓ SSH blocked by firewall")
    else:
        print("   ✗ SSH not blocked (firewall check failed)")

    print("\n2. Testing HTTP (port 80) still works...")
    can_connect = network.virtual_network.can_connect('192.168.1.10', '192.168.1.100', 80)
    if can_connect:
        print("   ✓ HTTP allowed (only SSH blocked)")
    else:
        print("   ✗ HTTP blocked (should be allowed)")

    print("\n✓ TCP firewall test complete")


if __name__ == '__main__':
    test_icmp_firewall()
    test_tcp_firewall()
    print("\n" + "="*60)
    print("ALL FIREWALL TESTS COMPLETE")
    print("="*60)
