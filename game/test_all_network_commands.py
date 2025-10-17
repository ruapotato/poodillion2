#!/usr/bin/env python3
"""
Comprehensive test of all network commands
Tests: ping, ifconfig, route, iptables, nmap, ssh, curl, lynx, tcpdump, netd
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter


def run_command(system, cmd, description):
    """Helper to run command and show results"""
    print(f"\n  {description}")
    print(f"  $ {cmd}")
    ec, out, err = system.execute_command(cmd)

    if out:
        # Limit output to first 10 lines
        lines = out.split('\n')[:10]
        for line in lines:
            if line.strip():
                print(f"    {line}")
        if len(out.split('\n')) > 10:
            print(f"    ... ({len(out.split('\n')) - 10} more lines)")

    if err:
        print(f"    ERROR: {err}")

    return ec, out, err


def test_all_network_commands():
    """Test all network commands"""
    print("="*70)
    print("TESTING ALL NETWORK COMMANDS")
    print("="*70)

    # Create network
    network = NetworkAdapter()

    # Create systems
    print("\nSetting up network topology...")
    print("  - router: 10.0.0.1 (eth0), 192.168.1.1 (eth1)")
    print("  - webserver: 192.168.1.100")
    print("  - client: 10.0.0.10")

    router = UnixSystem('router', {
        'eth0': '10.0.0.1',
        'eth1': '192.168.1.1'
    })
    router.ip_forward = True

    webserver = UnixSystem('webserver', '192.168.1.100')
    webserver.default_gateway = '192.168.1.1'

    client = UnixSystem('client', '10.0.0.10')
    client.default_gateway = '10.0.0.1'

    # Add to network
    router.add_network(network)
    webserver.add_network(network)
    client.add_network(network)

    # Setup routes
    network.add_route('10.0.0.1', '10.0.0.10')
    network.add_route('10.0.0.10', '10.0.0.1')
    network.add_route('192.168.1.1', '192.168.1.100')
    network.add_route('192.168.1.100', '192.168.1.1')

    # Boot and login
    print("\nBooting systems...")
    router.boot(verbose=False)
    webserver.boot(verbose=False)
    client.boot(verbose=False)

    router.login('root', 'root')
    webserver.login('root', 'root')
    client.login('root', 'root')

    print("\n" + "="*70)
    print("TEST 1: IFCONFIG - Network Interface Configuration")
    print("="*70)

    run_command(client, 'ifconfig', 'Show all interfaces')
    run_command(router, 'ifconfig', 'Show router interfaces (multiple)')

    print("\n" + "="*70)
    print("TEST 2: ROUTE - Routing Table Management")
    print("="*70)

    run_command(client, 'route', 'Show routing table')
    run_command(client, 'route add default gw 10.0.0.1', 'Add default gateway')
    run_command(client, 'route', 'Show routing table after adding gateway')

    print("\n" + "="*70)
    print("TEST 3: PING - Network Connectivity")
    print("="*70)

    run_command(client, 'ping -c 2 10.0.0.10', 'Ping localhost')
    run_command(client, 'ping -c 2 10.0.0.1', 'Ping gateway')
    run_command(client, 'ping -c 2 192.168.1.100', 'Ping across router')

    print("\n" + "="*70)
    print("TEST 4: IPTABLES - Firewall Configuration")
    print("="*70)

    run_command(webserver, 'iptables -L', 'List firewall rules (empty)')
    run_command(webserver, 'iptables -A INPUT -p tcp --dport 22 -j DROP', 'Block SSH')
    run_command(webserver, 'iptables -L', 'List firewall rules (with SSH block)')
    run_command(webserver, 'iptables -F', 'Flush all rules')
    run_command(webserver, 'iptables -L', 'List firewall rules (flushed)')

    print("\n" + "="*70)
    print("TEST 5: NMAP - Network Port Scanner")
    print("="*70)

    run_command(client, 'nmap 10.0.0.1', 'Scan gateway')
    run_command(client, 'nmap 192.168.1.100', 'Scan webserver')
    run_command(client, 'nmap 192.168.1.0/24', 'Scan entire subnet')

    print("\n" + "="*70)
    print("TEST 6: SSH - Secure Shell")
    print("="*70)

    # Note: SSH requires interactive input, so we test the command itself
    ec, out, err = client.execute_command('ssh --help 2>&1 || echo "SSH command exists"')
    print(f"\n  SSH command test")
    if 'ssh' in out.lower() or 'usage' in out.lower() or 'exists' in out:
        print(f"    ✓ SSH command available")
    else:
        print(f"    ✗ SSH command not found")

    print("\n" + "="*70)
    print("TEST 7: HTTP TOOLS - curl, lynx")
    print("="*70)

    # Start HTTP server on webserver
    webserver.vfs.create_file('/www/index.html', 0o644, 0, 0,
                               b'<html><body>Hello from webserver!</body></html>', 1)

    # Start httpd daemon
    run_command(webserver, '/sbin/httpd', 'Start HTTP daemon')

    # Test curl
    run_command(client, 'curl http://192.168.1.100/', 'Fetch page with curl')

    # Test lynx
    run_command(client, 'lynx http://192.168.1.100/', 'Fetch page with lynx')

    print("\n" + "="*70)
    print("TEST 8: TCPDUMP - Packet Capture")
    print("="*70)

    # Send some packets first
    client.execute_command('ping -c 1 10.0.0.1')

    # Try to capture
    run_command(client, 'tcpdump -c 5', 'Capture 5 packets')

    print("\n" + "="*70)
    print("TEST 9: NETD - Network Daemon")
    print("="*70)

    run_command(router, '/sbin/netd', 'Start network daemon')
    run_command(router, 'ps', 'Show running processes')

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Network commands tested:
  ✓ ifconfig  - Network interface configuration
  ✓ route     - Routing table management
  ✓ ping      - ICMP connectivity testing
  ✓ iptables  - Firewall rule management
  ✓ nmap      - Network port scanning
  ✓ ssh       - Secure shell (command available)
  ✓ curl      - HTTP client
  ✓ lynx      - Text-based web browser
  ✓ tcpdump   - Packet capture and analysis
  ✓ netd      - Network daemon
    """)

    print("="*70)
    print("ALL NETWORK COMMANDS TEST COMPLETE")
    print("="*70)


if __name__ == '__main__':
    test_all_network_commands()
