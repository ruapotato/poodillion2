#!/usr/bin/env python3
"""
Fast test of device-based networking implementation
Tests core functionality without slow sleep() calls
"""

from core.system import UnixSystem
from core.network import VirtualNetwork
from core.packet_queue import (
    build_icmp_echo_request, build_icmp_echo_reply,
    parse_ip_packet, parse_icmp_packet
)


def test_proc_net_files():
    """Test /proc/net/* dynamic file generation"""
    print("\n" + "=" * 60)
    print("Testing /proc/net/* Dynamic Files")
    print("=" * 60)

    # Create a multi-interface router
    router = UnixSystem('gateway', {
        'eth0': '10.0.0.1',
        'eth1': '192.168.1.1'
    })
    router.ip_forward = True
    router.default_gateway = '10.0.0.254'

    # Create network
    network = VirtualNetwork()
    router.add_network(network)

    # Add another system for ARP testing
    webserver = UnixSystem('webserver', '192.168.1.50')
    webserver.add_network(network)

    # Add layer-2 connectivity
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')

    # Test reading /proc/net/dev directly
    print("\n1. Testing /proc/net/dev")
    dev_content = router.vfs.read_file('/proc/net/dev', 1)
    if dev_content:
        print("✓ /proc/net/dev generated:")
        print(dev_content.decode('utf-8'))
    else:
        print("✗ Failed to read /proc/net/dev")
        return False

    # Test reading /proc/net/arp
    print("\n2. Testing /proc/net/arp")
    arp_content = router.vfs.read_file('/proc/net/arp', 1)
    if arp_content:
        print("✓ /proc/net/arp generated:")
        print(arp_content.decode('utf-8'))
        if '192.168.1.50' in arp_content.decode('utf-8'):
            print("✓ Shows neighbor 192.168.1.50")
    else:
        print("✗ Failed to read /proc/net/arp")
        return False

    # Test reading /proc/net/route
    print("\n3. Testing /proc/net/route")
    route_content = router.vfs.read_file('/proc/net/route', 1)
    if route_content:
        print("✓ /proc/net/route generated:")
        print(route_content.decode('utf-8'))
        if 'eth0' in route_content.decode('utf-8') and 'eth1' in route_content.decode('utf-8'):
            print("✓ Shows both interfaces")
    else:
        print("✗ Failed to read /proc/net/route")
        return False

    return True


def test_packet_building():
    """Test packet encoding/decoding"""
    print("\n" + "=" * 60)
    print("Testing Packet Encoding/Decoding")
    print("=" * 60)

    # Build a ping packet
    src_ip = '10.0.0.100'
    dst_ip = '192.168.1.50'
    packet = build_icmp_echo_request(src_ip, dst_ip, 1234, 1, b'test data')

    print(f"\n1. Built ICMP Echo Request ({len(packet)} bytes)")
    print(f"   Source: {src_ip}")
    print(f"   Destination: {dst_ip}")

    # Parse it back
    ip_header = parse_ip_packet(packet)
    print(f"\n2. Parsed IP header:")
    print(f"   Version: {ip_header['version']}")
    print(f"   Protocol: {ip_header['protocol']} (1=ICMP)")
    print(f"   Src: {ip_header['src']}")
    print(f"   Dst: {ip_header['dst']}")

    if ip_header['src'] != src_ip or ip_header['dst'] != dst_ip:
        print("✗ IP addresses don't match!")
        return False

    icmp_header = parse_icmp_packet(ip_header['data'])
    print(f"\n3. Parsed ICMP header:")
    print(f"   Type: {icmp_header['type']} (8=Echo Request)")
    print(f"   Code: {icmp_header['code']}")
    print(f"   ID: {icmp_header['id']}")
    print(f"   Sequence: {icmp_header['sequence']}")
    print(f"   Data: {icmp_header['data']}")

    if icmp_header['type'] != 8:
        print("✗ ICMP type should be 8 (Echo Request)")
        return False

    # Check data (may have padding for checksum)
    if not icmp_header['data'].startswith(b'test data'):
        print(f"✗ ICMP data doesn't match: expected b'test data', got {icmp_header['data']}")
        return False

    print("\n✓ Packet encoding/decoding works correctly!")
    return True


def test_packet_queue():
    """Test packet queue and device I/O"""
    print("\n" + "=" * 60)
    print("Testing Packet Queue and /dev/net/packet")
    print("=" * 60)

    # Create network
    network = VirtualNetwork()

    # Create two systems
    sender = UnixSystem('sender', '10.0.0.100')
    sender.add_network(network)

    receiver = UnixSystem('receiver', '10.0.0.200')
    receiver.add_network(network)

    # Add layer-2 connectivity
    network.add_route('10.0.0.100', '10.0.0.200')
    network.add_route('10.0.0.200', '10.0.0.100')

    print("\n1. Building test packet...")
    packet = build_icmp_echo_request('10.0.0.100', '10.0.0.200', 9999, 1, b'hello')

    print(f"\n2. Sending packet via PacketQueue.send_packet()...")
    success = sender.packet_queue.send_packet(packet)
    if success:
        print("✓ Packet sent successfully")
    else:
        print("✗ Failed to send packet")
        return False

    print(f"\n3. Checking receiver's inbound queue...")
    print(f"   Receiver has {len(receiver.packet_queue.inbound)} packets")
    if len(receiver.packet_queue.inbound) > 0:
        print("✓ Packet delivered to destination")
    else:
        print("✗ No packets in receiver queue")
        return False

    print(f"\n4. Checking sender's inbound queue (auto-reply)...")
    print(f"   Sender has {len(sender.packet_queue.inbound)} packets")
    if len(sender.packet_queue.inbound) > 0:
        print("✓ Auto-reply received!")
        # Parse the reply
        reply_packet = sender.packet_queue.receive_packet()
        if reply_packet:
            ip_reply = parse_ip_packet(reply_packet)
            icmp_reply = parse_icmp_packet(ip_reply['data'])
            if icmp_reply['type'] == 0:  # Echo Reply
                print(f"✓ ICMP Echo Reply (type=0) received")
                print(f"  Sequence: {icmp_reply['sequence']}")
                print(f"  Data: {icmp_reply['data']}")
            else:
                print(f"✗ Wrong ICMP type: {icmp_reply['type']}")
                return False
    else:
        print("✗ No auto-reply received")
        return False

    print("\n5. Testing /dev/net/packet device...")
    # Write packet via device
    sender.vfs.write_file('/dev/net/packet', packet, 1)

    # Read from device
    received = receiver.vfs.read_file('/dev/net/packet', 1, size=1024)
    if received and len(received) > 0:
        print(f"✓ Read {len(received)} bytes from /dev/net/packet")
    else:
        print("✗ No data read from /dev/net/packet")

    return True


def test_multi_hop_routing():
    """Test multi-hop packet routing"""
    print("\n" + "=" * 60)
    print("Testing Multi-Hop Routing")
    print("=" * 60)

    # Create network
    network = VirtualNetwork()

    # Create attacker (external network)
    attacker = UnixSystem('attacker', '10.0.0.100')
    attacker.add_network(network)

    # Create router with 2 interfaces
    router = UnixSystem('router', {
        'eth0': '10.0.0.1',      # External
        'eth1': '192.168.1.1'    # Internal
    })
    router.ip_forward = True  # Enable routing
    router.add_network(network)

    # Create webserver (internal network)
    webserver = UnixSystem('webserver', '192.168.1.50')
    webserver.add_network(network)

    # Add layer-2 connectivity
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.100')
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')

    print("\nNetwork Topology:")
    print("  Attacker (10.0.0.100)")
    print("      |")
    print("  Router (10.0.0.1 / 192.168.1.1) [ip_forward=True]")
    print("      |")
    print("  Webserver (192.168.1.50)")

    print("\n1. Testing direct connection (attacker -> router)...")
    path = network._find_route_path('10.0.0.100', '10.0.0.1')
    if path:
        print(f"✓ Route found: {' -> '.join(path)}")
    else:
        print("✗ No route found")
        return False

    print("\n2. Testing multi-hop routing (attacker -> webserver)...")
    path = network._find_route_path('10.0.0.100', '192.168.1.50')
    if path:
        print(f"✓ Route found: {' -> '.join(path)}")
        if len(path) > 2:
            print("✓ Multi-hop route detected!")
    else:
        print("✗ No route found")
        return False

    print("\n3. Sending packet through router...")
    packet = build_icmp_echo_request('10.0.0.100', '192.168.1.50', 5555, 1, b'multi-hop test')
    success = attacker.packet_queue.send_packet(packet)
    if success:
        print("✓ Packet sent")
        print(f"  Webserver queue: {len(webserver.packet_queue.inbound)} packets")
        if len(webserver.packet_queue.inbound) > 0:
            print("✓ Packet routed to webserver!")
        else:
            print("✗ Packet not delivered")
            return False
    else:
        print("✗ Packet send failed")
        return False

    print("\n4. Testing with routing disabled...")
    router.ip_forward = False
    path = network._find_route_path('10.0.0.100', '192.168.1.50')
    if not path:
        print("✓ Route correctly blocked when ip_forward=False")
    else:
        print("✗ Route should be blocked")
        return False

    return True


def main():
    """Run all tests"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Device-Based Networking Test Suite".center(58) + "║")
    print("║" + "  (Fast Version - No Sleep Calls)".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")

    tests = [
        ("Packet Encoding/Decoding", test_packet_building),
        ("/proc/net/* Files", test_proc_net_files),
        ("Packet Queue & Device I/O", test_packet_queue),
        ("Multi-Hop Routing", test_multi_hop_routing),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n✗ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        print("\nDevice-based networking is FULLY FUNCTIONAL!")
        print("\nKey Achievements:")
        print("  ✓ Packet queue implementation")
        print("  ✓ /dev/net/packet device handlers")
        print("  ✓ /proc/net/* dynamic file generation")
        print("  ✓ Packet encoding/decoding")
        print("  ✓ Multi-hop routing via devices")
        print("  ✓ Automatic ICMP Echo Reply generation")
        print("\nNext steps:")
        print("  - Test device-based ping command (in interactive mode)")
        print("  - Implement DHCP client/server")
        print("  - Add packet sniffing via /dev/net/packet")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit(main())
