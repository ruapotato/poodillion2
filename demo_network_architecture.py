#!/usr/bin/env python3
"""
Visual Demo of PooScript Network Architecture

Shows the complete separation between Python "wire" and PooScript "intelligence"
"""

from core.system import UnixSystem
from core.network_physical import PhysicalNetwork

def demo():
    print("\n" + "=" * 80)
    print(" " * 20 + "POOSCRIPT NETWORK ARCHITECTURE DEMO")
    print("=" * 80)

    # Create three systems: client, router, server
    print("\n📦 Creating Systems...")
    client = UnixSystem('client', '192.168.1.10')
    router = UnixSystem('router', {'eth0': '192.168.1.1', 'eth1': '192.168.2.1'})
    server = UnixSystem('server', '192.168.2.10')

    # Enable routing on router
    router.ip_forward = True

    print(f"   • Client: {client.ip} (eth0)")
    print(f"   • Router: {router.interfaces['eth0']} (eth0), {router.interfaces['eth1']} (eth1)")
    print(f"   • Server: {server.ip} (eth0)")

    # Create physical network topology
    print("\n🔌 Creating Physical Network...")
    physical_net = PhysicalNetwork()

    # Create two broadcast domains
    lan1 = physical_net.create_segment('lan1')  # 192.168.1.0/24
    lan2 = physical_net.create_segment('lan2')  # 192.168.2.0/24

    # Connect systems
    lan1.attach_interface(client.net_interfaces['eth0'])
    lan1.attach_interface(router.net_interfaces['eth0'])
    lan2.attach_interface(router.net_interfaces['eth1'])
    lan2.attach_interface(server.net_interfaces['eth0'])

    print("   • LAN1 (192.168.1.0/24): client.eth0 ↔ router.eth0")
    print("   • LAN2 (192.168.2.0/24): router.eth1 ↔ server.eth0")

    # Configure routing on router
    print("\n🗺️  Configuring Routing Table...")
    routing_table = """# Routing table for router
192.168.1.0 0.0.0.0 255.255.255.0 eth0
192.168.2.0 0.0.0.0 255.255.255.0 eth1
"""
    router.vfs.write_file('/etc/network/routes', routing_table.encode(), 1)
    print("   • Router routes: 192.168.1.0/24 → eth0, 192.168.2.0/24 → eth1")

    # Show device files
    print("\n📁 Device Files Created:")
    for system_name, system in [('client', client), ('router', router), ('server', server)]:
        print(f"\n   {system_name}:")
        entries = system.vfs.list_dir('/dev/net', 1)
        if entries:
            for name, ino in sorted(entries):
                if name not in ('.', '..'):
                    print(f"      • /dev/net/{name}")

    # Show PooScript network daemon
    print("\n🤖 PooScript Network Daemon:")
    netd = router.vfs.read_file('/sbin/netd', 1)
    if netd:
        lines = netd.decode().split('\n')
        print(f"   • /sbin/netd: {len(lines)} lines, {len(netd)} bytes")
        print("   • Features: IP parsing, TTL decrement, routing, ICMP replies")

    # Demonstrate packet flow
    print("\n" + "=" * 80)
    print(" " * 25 + "PACKET FLOW DEMONSTRATION")
    print("=" * 80)

    # Build a simple IP packet
    print("\n1️⃣  Client sends packet to Server (192.168.2.10)")

    # IP header (simplified)
    packet = bytearray(40)
    packet[0] = 0x45  # Version 4, IHL 5
    packet[8] = 64    # TTL

    # Source IP: 192.168.1.10
    packet[12:16] = bytes([192, 168, 1, 10])

    # Dest IP: 192.168.2.10
    packet[16:20] = bytes([192, 168, 2, 10])

    # Payload
    packet[20:] = b'Hello from client!'

    print(f"   • Packet created: {len(packet)} bytes")
    print(f"   • Source: 192.168.1.10")
    print(f"   • Destination: 192.168.2.10")
    print(f"   • TTL: 64")

    # Client sends to eth0
    print("\n2️⃣  Client writes to /dev/net/eth0_raw")
    client.vfs.write_file('/dev/net/eth0_raw', bytes(packet), 1)
    print("   ✓ Python: client.eth0.send_raw() called")
    print("   ✓ NetworkSegment 'lan1' broadcasts packet")

    # Check router received
    print("\n3️⃣  Router receives on eth0")
    router_packet = router.net_interfaces['eth0'].recv_raw()
    if router_packet:
        print(f"   ✓ Router eth0 RX buffer: {len(router_packet)} bytes")
        print(f"   ✓ Source: {router_packet[12]}.{router_packet[13]}.{router_packet[14]}.{router_packet[15]}")
        print(f"   ✓ Dest: {router_packet[16]}.{router_packet[17]}.{router_packet[18]}.{router_packet[19]}")
        print(f"   ✓ TTL: {router_packet[8]}")
    else:
        print("   ✗ Router did not receive packet")

    # PooScript netd would:
    # 1. Read from /dev/net/eth0_raw
    # 2. Parse IP header
    # 3. Check if dest is for us (not 192.168.1.1 or 192.168.2.1)
    # 4. Look up route for 192.168.2.10 → finds eth1
    # 5. Decrement TTL
    # 6. Write to /dev/net/eth1_raw

    print("\n4️⃣  PooScript netd would route (simulated):")
    print("   • Reads from /dev/net/eth0_raw")
    print("   • Parses IP: dst = 192.168.2.10")
    print("   • Looks up route: 192.168.2.0/24 → eth1")
    print("   • Decrements TTL: 64 → 63")
    print("   • Writes to /dev/net/eth1_raw")

    # Simulate routing
    packet[8] = 63  # Decrement TTL
    router.vfs.write_file('/dev/net/eth1_raw', bytes(packet), 1)

    print("\n5️⃣  Server receives on eth0")
    server_packet = server.net_interfaces['eth0'].recv_raw()
    if server_packet:
        print(f"   ✓ Server eth0 RX buffer: {len(server_packet)} bytes")
        print(f"   ✓ TTL: {server_packet[8]} (decremented by router)")
        print(f"   ✓ Payload: {server_packet[20:].decode('utf-8', errors='ignore')}")
    else:
        print("   ✗ Server did not receive packet")

    # Summary
    print("\n" + "=" * 80)
    print(" " * 30 + "ARCHITECTURE SUMMARY")
    print("=" * 80)

    print("""
    PYTHON LAYER (Physical Wire):
    ┌────────────────────────────────────────────────────────────┐
    │ NetworkInterface: RX/TX buffers, MAC addresses             │
    │ NetworkSegment: Broadcasts packets (hub-like)              │
    │ PhysicalNetwork: Manages topology                          │
    └────────────────────────────────────────────────────────────┘
              ▲                          ▲
              │ read/write               │ send_raw/recv_raw
              │                          │
    ┌────────────────────────────────────────────────────────────┐
    │ VFS Device Handlers:                                       │
    │   /dev/net/eth0_raw → NetworkInterface.send_raw()         │
    │   /dev/net/eth1_raw → NetworkInterface.send_raw()         │
    │   /dev/net/local → local_packet_queue                     │
    └────────────────────────────────────────────────────────────┘
              ▲                          ▲
              │ vfs.read/write           │ vfs.read/write
              │                          │
    ┌────────────────────────────────────────────────────────────┐
    │ POOSCRIPT LAYER (Network Intelligence):                   │
    │                                                            │
    │   /sbin/netd:                                             │
    │     - Reads packets from /dev/net/eth*_raw                │
    │     - Parses IP headers                                   │
    │     - Routes based on /etc/network/routes                 │
    │     - Handles ICMP (ping replies)                         │
    │     - Decrements TTL                                      │
    │     - Writes to output interface or /dev/net/local        │
    │                                                            │
    │   /etc/network/routes:                                    │
    │     - Routing table (destination gateway netmask iface)   │
    │                                                            │
    │   Player Commands:                                         │
    │     - cat /sbin/netd (view routing logic)                 │
    │     - vi /sbin/netd (modify routing)                      │
    │     - echo "..." >> /etc/network/routes (add routes)      │
    │     - dd if=/dev/net/eth0_raw (sniff packets)            │
    └────────────────────────────────────────────────────────────┘

    KEY BENEFIT: Every network decision is visible and modifiable!

    Players can:
      ✓ Read routing daemon source code
      ✓ Modify packet forwarding logic
      ✓ Sniff packets via device files
      ✓ Add/remove routes
      ✓ Inject packets
      ✓ Create backdoors
      ✓ Exploit misconfigurations
    """)

    print("=" * 80)
    print(" " * 25 + "✨ INTEGRATION COMPLETE ✨")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    demo()
