#!/usr/bin/env python3
"""
Direct test of packet-level firewall (bypassing shell)
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter
from core.packet_queue import build_icmp_echo_request


def test_packet_level_firewall():
    """Test firewall at packet level"""
    print("Testing packet-level firewall directly...")

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

    print("\n1. Testing ICMP without firewall...")
    # Build ICMP echo request packet
    packet = build_icmp_echo_request(
        src_ip='192.168.13.37',
        dst_ip='192.168.13.1',
        icmp_id=1234,
        sequence=1,
        data=b'test'
    )

    # Send packet
    success = kali.packet_queue.send_packet(packet)

    # Check if reply was received
    has_reply = gateway.packet_queue.has_packets() or kali.packet_queue.has_packets()

    if success:
        print("   ✓ Packet sent successfully (no firewall)")
    else:
        print("   ✗ Packet failed (unexpected)")

    # Clear queues
    gateway.packet_queue.clear()
    kali.packet_queue.clear()

    print("\n2. Adding firewall rule to block ICMP...")
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': 'any'
    })

    print("\n3. Testing ICMP with firewall (should be blocked)...")
    packet = build_icmp_echo_request(
        src_ip='192.168.13.37',
        dst_ip='192.168.13.1',
        icmp_id=1234,
        sequence=2,
        data=b'test'
    )

    # Send packet
    success = kali.packet_queue.send_packet(packet)

    # Check if packet was delivered to gateway's inbound queue
    has_inbound = len(gateway.packet_queue.inbound) > 0

    if not success or not has_inbound:
        print("   ✓ Packet blocked by firewall (expected)")
    else:
        print("   ✗ Packet not blocked (firewall failed!)")
        print(f"   Gateway inbound queue: {len(gateway.packet_queue.inbound)} packets")

    print("\n4. Testing specific source blocking...")
    gateway.firewall_rules.clear()
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': '192.168.13.37'
    })

    packet = build_icmp_echo_request(
        src_ip='192.168.13.37',
        dst_ip='192.168.13.1',
        icmp_id=1234,
        sequence=3,
        data=b'test'
    )

    success = kali.packet_queue.send_packet(packet)
    has_inbound = len(gateway.packet_queue.inbound) > 0

    if not success or not has_inbound:
        print("   ✓ Packet from specific source blocked (expected)")
    else:
        print("   ✗ Packet not blocked (source filtering failed!)")

    print("\n5. Testing subnet blocking...")
    gateway.firewall_rules.clear()
    gateway.packet_queue.clear()
    gateway.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'icmp',
        'action': 'DROP',
        'source': '192.168.13.0/24'
    })

    packet = build_icmp_echo_request(
        src_ip='192.168.13.37',
        dst_ip='192.168.13.1',
        icmp_id=1234,
        sequence=4,
        data=b'test'
    )

    success = kali.packet_queue.send_packet(packet)
    has_inbound = len(gateway.packet_queue.inbound) > 0

    if not success or not has_inbound:
        print("   ✓ Packet from subnet blocked (expected)")
    else:
        print("   ✗ Packet not blocked (subnet filtering failed!)")

    print("\n✓ Direct packet-level firewall test complete\n")


if __name__ == '__main__':
    test_packet_level_firewall()
    print("="*60)
    print("PACKET-LEVEL FIREWALL TEST COMPLETE")
    print("="*60)
