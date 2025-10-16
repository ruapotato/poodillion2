#!/usr/bin/env python3
"""
Direct network test without shell layer
"""

from core.system import UnixSystem
from core.network import VirtualNetwork


def test_network_direct():
    """Test network layer directly"""
    print('=== Direct Network Layer Test ===\n')

    # Create network
    network = VirtualNetwork()

    # Create two systems
    attacker = UnixSystem('attacker', '192.168.1.100')
    target = UnixSystem('target', '192.168.1.50')

    print(f'Created attacker system: {attacker.hostname} at {attacker.ip}')
    print(f'Created target system: {target.hostname} at {target.ip}')
    print()

    # Add to network
    attacker.add_network(network)
    target.add_network(network)
    print('Systems added to network')
    print()

    # Check initial connectivity (should be false - no routes)
    can_connect = network.can_connect('192.168.1.100', '192.168.1.50')
    print(f'Can attacker reach target (before routes)? {can_connect}')
    print()

    # Add routes
    network.add_route('192.168.1.100', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.100')
    print('Routes added')
    print()

    # Check connectivity (should be true now)
    can_connect = network.can_connect('192.168.1.100', '192.168.1.50')
    print(f'Can attacker reach target (after routes)? {can_connect}')
    print()

    # Spawn services on target
    sshd_pid = target.spawn_service('sshd', ['service', 'ssh'], uid=0)
    apache_pid = target.spawn_service('apache2', ['service', 'webserver'], uid=33)
    mysql_pid = target.spawn_service('mysqld', ['service', 'database'], uid=27)

    print(f'Spawned services on target:')
    print(f'  sshd (PID {sshd_pid})')
    print(f'  apache2 (PID {apache_pid})')
    print(f'  mysqld (PID {mysql_pid})')
    print()

    # Test network scan
    print('=== Subnet Scan (192.168.1.0/24) ===')
    hosts = network.scan_network('192.168.1.100', '192.168.1.0/24')
    print(f'Found {len(hosts)} hosts:')
    for host in hosts:
        print(f'  {host}')
    print()

    # Test port scan
    print('=== Port Scan (192.168.1.50) ===')
    ports = network.port_scan('192.168.1.100', '192.168.1.50')
    print(f'Found {len(ports)} open ports:')
    for port in sorted(ports):
        print(f'  {port}/tcp')
    print()

    # Test unreachable target
    print('=== Test Unreachable Target ===')
    can_reach = network.can_connect('192.168.1.100', '10.0.0.1')
    print(f'Can reach 10.0.0.1? {can_reach}')
    print()

    # Test firewall
    print('=== Test Firewall ===')
    print('Adding firewall rule to block port 22 on target')
    network.add_firewall_rule('192.168.1.50', 'DENY', 22)
    can_connect_ssh = network.can_connect('192.168.1.100', '192.168.1.50', 22)
    can_connect_http = network.can_connect('192.168.1.100', '192.168.1.50', 80)
    print(f'Can connect to port 22? {can_connect_ssh} (should be False)')
    print(f'Can connect to port 80? {can_connect_http} (should be True)')
    print()

    print('=== All Direct Network Tests Complete ===')


if __name__ == '__main__':
    test_network_direct()
