#!/usr/bin/env python3
"""
Test PooScript Network Architecture

This test demonstrates the PooScript-driven network where:
1. Python provides the physical layer (NetworkInterface, NetworkSegment)
2. PooScript netd daemon handles all routing logic
3. Network device files (/dev/net/eth0_raw) bridge the two layers
"""

from core.system import UnixSystem
from core.network_physical import PhysicalNetwork, NetworkSegment

def test_pooscript_network():
    """Test basic PooScript network setup"""

    print("=" * 70)
    print("Testing PooScript Network Architecture")
    print("=" * 70)

    # Create two systems
    print("\n1. Creating two systems...")
    client = UnixSystem('client', '192.168.1.10')
    server = UnixSystem('server', '192.168.1.20')

    print(f"   ✓ Client: {client.hostname} @ {client.ip}")
    print(f"     Interfaces: {list(client.net_interfaces.keys())}")
    print(f"   ✓ Server: {server.hostname} @ {server.ip}")
    print(f"     Interfaces: {list(server.net_interfaces.keys())}")

    # Create physical network
    print("\n2. Creating physical network (broadcast domain)...")
    physical_net = PhysicalNetwork()
    segment = physical_net.create_segment('lan1')

    # Connect interfaces to segment
    segment.attach_interface(client.net_interfaces['eth0'])
    segment.attach_interface(server.net_interfaces['eth0'])

    print(f"   ✓ Created segment 'lan1'")
    print(f"   ✓ Connected client.eth0 (MAC: {client.net_interfaces['eth0'].mac})")
    print(f"   ✓ Connected server.eth0 (MAC: {server.net_interfaces['eth0'].mac})")

    # Test device file access
    print("\n3. Testing device file access...")

    # Test reading from eth0_raw (should be empty initially)
    packet = client.vfs.read_file('/dev/net/eth0_raw', 1)
    print(f"   ✓ Read from /dev/net/eth0_raw: {len(packet) if packet else 0} bytes")

    # Simulate sending a raw packet
    print("\n4. Testing raw packet transmission...")
    test_packet = b'\x45\x00\x00\x1c' + b'\x00' * 24 + b'test payload'

    # Write to client's eth0_raw (should broadcast to segment)
    client.vfs.write_file('/dev/net/eth0_raw', test_packet, 1)
    print(f"   ✓ Wrote {len(test_packet)} bytes to client:/dev/net/eth0_raw")

    # Check if server received it
    received = server.net_interfaces['eth0'].recv_raw()
    if received:
        print(f"   ✓ Server received {len(received)} bytes on eth0")
        print(f"     Payload matches: {received == test_packet}")
    else:
        print(f"   ✗ Server did not receive packet")

    # Test local packet queue
    print("\n5. Testing local packet delivery...")
    local_packet = b'packet for localhost'
    client.local_packet_queue.append(local_packet)

    # Read from /dev/net/local
    received_local = client.vfs.read_file('/dev/net/local', 1)
    if received_local:
        print(f"   ✓ Read {len(received_local)} bytes from /dev/net/local")
        print(f"     Payload matches: {received_local == local_packet}")
    else:
        print(f"   ✗ Failed to read from /dev/net/local")

    # Check configuration files
    print("\n6. Checking network configuration files...")

    interfaces_file = client.vfs.read_file('/etc/network/interfaces', 1)
    if interfaces_file and b'eth0' in interfaces_file:
        print(f"   ✓ /etc/network/interfaces exists and contains eth0")

    routes_file = client.vfs.read_file('/etc/network/routes', 1)
    if routes_file:
        print(f"   ✓ /etc/network/routes exists")

    netd_script = client.vfs.read_file('/sbin/netd', 1)
    if netd_script and b'netd' in netd_script:
        print(f"   ✓ /sbin/netd exists ({len(netd_script)} bytes)")

    # Summary
    print("\n" + "=" * 70)
    print("Architecture Summary:")
    print("=" * 70)
    print("""
    Python Layer (Physical):
    - NetworkInterface: Manages RX/TX buffers for each interface
    - NetworkSegment: Broadcasts packets (like a hub)
    - PhysicalNetwork: Manages network topology

    PooScript Layer (Logical):
    - /dev/net/eth0_raw: Read/write raw packets on interface
    - /dev/net/local: Receive packets destined for localhost
    - /sbin/netd: Network daemon (routes packets, handles ICMP)
    - /etc/network/routes: Routing table

    Packet Flow:
    1. PooScript writes to /dev/net/eth0_raw
    2. VFS device handler calls eth0.send_raw()
    3. NetworkInterface broadcasts to segment
    4. Segment puts packet in all other interfaces' RX buffers
    5. PooScript netd reads from /dev/net/eth0_raw
    6. netd routes based on /etc/network/routes
    7. netd writes to output interface or /dev/net/local
    """)

    print("=" * 70)
    print("✓ PooScript Network Architecture Test Complete!")
    print("=" * 70)

    return True

if __name__ == '__main__':
    test_pooscript_network()
