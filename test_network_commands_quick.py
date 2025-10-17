#!/usr/bin/env python3
"""
Quick test of all network commands (non-blocking)
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter
import signal
import sys


def timeout_handler(signum, frame):
    raise TimeoutError("Command timed out")


def run_command_safe(system, cmd, description, timeout=5):
    """Run command with timeout"""
    print(f"\n  {description}")
    print(f"  $ {cmd}")

    try:
        # Set alarm for timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        ec, out, err = system.execute_command(cmd)

        # Cancel alarm
        signal.alarm(0)

        if out:
            lines = out.split('\n')[:8]
            for line in lines:
                if line.strip():
                    print(f"    {line}")
            if len(out.split('\n')) > 8:
                print(f"    ...")

        if err:
            print(f"    ERROR: {err[:200]}")

        result = "✓" if ec == 0 else "✗"
        print(f"    {result} Exit code: {ec}")
        return ec == 0

    except TimeoutError:
        signal.alarm(0)
        print(f"    ⏱ Command timed out after {timeout}s")
        return False
    except Exception as e:
        signal.alarm(0)
        print(f"    ✗ Exception: {e}")
        return False


def test_network_commands():
    """Quick test of network commands"""
    print("="*70)
    print("QUICK NETWORK COMMANDS TEST")
    print("="*70)

    # Create simple network
    network = NetworkAdapter()

    router = UnixSystem('router', {'eth0': '10.0.0.1', 'eth1': '192.168.1.1'})
    router.ip_forward = True

    client = UnixSystem('client', '10.0.0.10')
    client.default_gateway = '10.0.0.1'

    router.add_network(network)
    client.add_network(network)

    network.add_route('10.0.0.1', '10.0.0.10')
    network.add_route('10.0.0.10', '10.0.0.1')

    router.boot(verbose=False)
    client.boot(verbose=False)

    router.login('root', 'root')
    client.login('root', 'root')

    results = {}

    print("\n" + "="*70)
    print("1. IFCONFIG")
    print("="*70)
    results['ifconfig'] = run_command_safe(client, 'ifconfig', 'Show network interfaces', timeout=3)

    print("\n" + "="*70)
    print("2. ROUTE")
    print("="*70)
    results['route'] = run_command_safe(client, 'route', 'Show routing table', timeout=3)

    print("\n" + "="*70)
    print("3. PING")
    print("="*70)
    results['ping'] = run_command_safe(client, 'ping -c 1 10.0.0.1', 'Ping gateway', timeout=3)

    print("\n" + "="*70)
    print("4. IPTABLES")
    print("="*70)
    results['iptables-list'] = run_command_safe(client, 'iptables -L', 'List rules', timeout=3)
    results['iptables-add'] = run_command_safe(client, 'iptables -A INPUT -p tcp --dport 22 -j DROP', 'Add rule', timeout=3)
    results['iptables-flush'] = run_command_safe(client, 'iptables -F', 'Flush rules', timeout=3)

    print("\n" + "="*70)
    print("5. NMAP")
    print("="*70)
    results['nmap'] = run_command_safe(client, 'nmap 10.0.0.1', 'Scan gateway', timeout=5)

    print("\n" + "="*70)
    print("6. SSH")
    print("="*70)
    # Check if command exists by looking at VFS
    ssh_exists = client.vfs.stat('/bin/ssh', 1) is not None
    results['ssh'] = ssh_exists
    print(f"  SSH command: {'✓ Available at /bin/ssh' if ssh_exists else '✗ Not found'}")

    print("\n" + "="*70)
    print("7. CURL")
    print("="*70)
    curl_exists = client.vfs.stat('/bin/curl', 1) is not None
    results['curl'] = curl_exists
    print(f"  CURL command: {'✓ Available at /bin/curl' if curl_exists else '✗ Not found'}")

    print("\n" + "="*70)
    print("8. LYNX")
    print("="*70)
    lynx_exists = client.vfs.stat('/bin/lynx', 1) is not None
    results['lynx'] = lynx_exists
    print(f"  LYNX command: {'✓ Available at /bin/lynx' if lynx_exists else '✗ Not found'}")

    print("\n" + "="*70)
    print("9. TCPDUMP")
    print("="*70)
    tcpdump_exists = client.vfs.stat('/sbin/tcpdump', 1) is not None
    results['tcpdump'] = tcpdump_exists
    print(f"  TCPDUMP command: {'✓ Available at /sbin/tcpdump' if tcpdump_exists else '✗ Not found'}")

    print("\n" + "="*70)
    print("10. NETD")
    print("="*70)
    netd_exists = client.vfs.stat('/sbin/netd', 1) is not None
    results['netd'] = netd_exists
    print(f"  NETD daemon: {'✓ Available at /sbin/netd' if netd_exists else '✗ Not found'}")

    # Summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nCommands tested: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    print("\nDetails:")
    for cmd, status in results.items():
        status_symbol = "✓" if status else "✗"
        print(f"  {status_symbol} {cmd}")

    print("\n" + "="*70)
    print(f"TEST {'PASSED' if passed == total else 'COMPLETED'}")
    print("="*70)

    return passed == total


if __name__ == '__main__':
    try:
        success = test_network_commands()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
