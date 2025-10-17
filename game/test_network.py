#!/usr/bin/env python3
"""
Test network functionality
"""

from core.system import UnixSystem
from core.network import VirtualNetwork


def test_networking():
    """Test network commands"""
    print('=== Network Test ===\n')

    # Create network
    network = VirtualNetwork()

    # Create two systems
    attacker = UnixSystem('attacker', '192.168.1.100')
    target = UnixSystem('target', '192.168.1.50')

    # Add to network
    attacker.add_network(network)
    target.add_network(network)

    # Add routes
    network.add_route('192.168.1.100', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.100')

    # Spawn services on target
    target.spawn_service('sshd', ['service', 'ssh'], uid=0)
    target.spawn_service('apache2', ['service', 'webserver'], uid=33)
    target.spawn_service('mysqld', ['service', 'database'], uid=27)

    # Login to attacker
    print('Logging into attacker system...')
    attacker.login('root', 'root')
    print()

    # Test 1: ifconfig
    print('=== Test 1: ifconfig ===')
    exit_code, stdout, stderr = attacker.execute_command('ifconfig')
    print(stdout)

    # Test 2: ping target
    print('=== Test 2: ping 192.168.1.50 -c 3 ===')
    exit_code, stdout, stderr = attacker.execute_command('ping 192.168.1.50 -c 3')
    print(stdout)

    # Test 3: nmap subnet scan
    print('=== Test 3: nmap 192.168.1.0/24 (subnet scan) ===')
    exit_code, stdout, stderr = attacker.execute_command('nmap 192.168.1.0/24')
    print(stdout)

    # Test 4: nmap port scan
    print('=== Test 4: nmap 192.168.1.50 (port scan) ===')
    exit_code, stdout, stderr = attacker.execute_command('nmap 192.168.1.50')
    print(stdout)

    # Test 5: Check unreachable host
    print('=== Test 5: ping 10.0.0.1 -c 2 (unreachable) ===')
    exit_code, stdout, stderr = attacker.execute_command('ping 10.0.0.1 -c 2')
    print(stdout)

    print('=== All Network Tests Complete ===')


if __name__ == '__main__':
    test_networking()
