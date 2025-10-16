#!/usr/bin/env python3
"""
Test that system interface is accessible from PooScript commands
"""

from core.system import UnixSystem


def test_system_interface():
    """Test system commands work"""
    print("=== Testing System Interface Wiring ===\n")

    # Create a system with multiple interfaces (simulating a router)
    router = UnixSystem('router', interfaces={
        'lo': '127.0.0.1',
        'eth0': '10.0.0.1',
        'eth1': '192.168.1.1'
    })

    # Login
    router.login('root', 'root')

    # Test 1: ifconfig should show all interfaces
    print("Test 1: ifconfig")
    print("="*50)
    exit_code, stdout, stderr = router.execute_command('ifconfig')
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

    # Test 2: route (should work even though there are no routes yet)
    print("\nTest 2: route -n")
    print("="*50)
    exit_code, stdout, stderr = router.execute_command('route -n')
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

    # Test 3: Check /proc/sys/net/ipv4/ip_forward
    print("\nTest 3: cat /proc/sys/net/ipv4/ip_forward")
    print("="*50)
    exit_code, stdout, stderr = router.execute_command('cat /proc/sys/net/ipv4/ip_forward')
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

    # Test 4: iptables -L (should show empty rules)
    print("\nTest 4: iptables -L")
    print("="*50)
    exit_code, stdout, stderr = router.execute_command('iptables -L')
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

    print("\n" + "="*50)
    print("All tests complete!")
    print("="*50)


if __name__ == '__main__':
    test_system_interface()
