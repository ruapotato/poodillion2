#!/usr/bin/env python3
"""
Test to verify default gateway usage in routing
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter
from core.packet_queue import build_icmp_echo_request


def test_gateway_usage():
    """Verify which gateway is used"""

    print("="*70)
    print("DEFAULT GATEWAY ROUTING TEST")
    print("="*70)

    # Create network
    network = NetworkAdapter()

    # Topology:
    # hacker (10.0.0.50) <-> router1 (10.0.0.1 / 192.168.1.1) <-> webserver (192.168.1.100)

    hacker = UnixSystem('hacker', '10.0.0.50')
    hacker.default_gateway = '10.0.0.1'  # This is the gateway hacker uses

    router1 = UnixSystem('router1', {
        'eth0': '10.0.0.1',      # Internet-facing (same subnet as hacker)
        'eth1': '192.168.1.1'    # DMZ-facing (same subnet as webserver)
    })
    router1.ip_forward = True

    webserver = UnixSystem('webserver', '192.168.1.100')
    webserver.default_gateway = '192.168.1.1'  # Webserver uses this gateway

    # Add to network
    for sys in [hacker, router1, webserver]:
        sys.add_network(network)

    # Setup routes (Layer 2 connectivity)
    network.add_route('10.0.0.50', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.50')
    network.add_route('192.168.1.1', '192.168.1.100')
    network.add_route('192.168.1.100', '192.168.1.1')

    # Boot
    for sys in [hacker, router1, webserver]:
        sys.boot(verbose=False)

    print("\nNetwork Configuration:")
    print("-" * 70)
    print(f"  Hacker:     IP={hacker.ip}, Gateway={hacker.default_gateway}")
    print(f"  Router1:    eth0={router1.interfaces['eth0']}, eth1={router1.interfaces['eth1']}")
    print(f"              IP_FORWARD={router1.ip_forward}")
    print(f"  Webserver:  IP={webserver.ip}, Gateway={webserver.default_gateway}")

    print("\n" + "="*70)
    print("QUESTION: When hacker (10.0.0.50) pings webserver (192.168.1.100),")
    print("          which gateway does it use?")
    print("="*70)

    print("\nAnalysis:")
    print("-" * 70)

    # Check routing path
    path = network.virtual_network._find_route_path('10.0.0.50', '192.168.1.100')
    print(f"\n1. Routing path from hacker to webserver:")
    print(f"   {' -> '.join(path)}")

    print(f"\n2. Hacker's configuration:")
    print(f"   - Hacker IP: 10.0.0.50")
    print(f"   - Hacker subnet: 10.0.0.0/24")
    print(f"   - Hacker default gateway: {hacker.default_gateway}")

    print(f"\n3. Destination analysis:")
    print(f"   - Webserver IP: 192.168.1.100")
    print(f"   - Webserver subnet: 192.168.1.0/24")
    print(f"   - Is webserver on same subnet as hacker? NO")
    print(f"   - Therefore: Packet must go through gateway")

    print(f"\n4. Gateway selection:")
    print(f"   - Hacker's default gateway: {hacker.default_gateway}")
    print(f"   - Is 192.168.1.1 on hacker's subnet? NO")
    print(f"   - Is 10.0.0.1 on hacker's subnet? YES")
    print(f"   - Therefore: Hacker uses {hacker.default_gateway} as its gateway")

    print(f"\n5. Packet flow:")
    print(f"   Step 1: Hacker (10.0.0.50) sends packet to gateway {hacker.default_gateway}")
    print(f"   Step 2: Router1 receives packet on eth0 (10.0.0.1)")
    print(f"   Step 3: Router1 sees destination is 192.168.1.100")
    print(f"   Step 4: Router1 checks: 192.168.1.100 is on eth1 subnet")
    print(f"   Step 5: Router1 forwards packet out eth1 (192.168.1.1)")
    print(f"   Step 6: Webserver (192.168.1.100) receives packet")

    # Verify with actual packet
    print("\n" + "="*70)
    print("VERIFICATION: Send actual packet and trace")
    print("="*70)

    webserver.packet_queue.clear()
    packet = build_icmp_echo_request('10.0.0.50', '192.168.1.100', 1, 1)
    success = hacker.packet_queue.send_packet(packet)

    print(f"\nPacket sent: {success}")
    print(f"Packet delivered to webserver: {len(webserver.packet_queue.inbound) > 0}")

    if len(webserver.packet_queue.inbound) > 0:
        received_packet = webserver.packet_queue.inbound[0]
        if hasattr(received_packet, 'hops'):
            print(f"Packet hops: {received_packet.hops}")

    # Summary
    print("\n" + "="*70)
    print("ANSWER")
    print("="*70)

    print(f"""
NO - Hacker (10.0.0.50) does NOT use gateway 192.168.1.1

Explanation:
  • Hacker's default gateway is: {hacker.default_gateway}
  • 192.168.1.1 is NOT reachable from hacker's subnet (10.0.0.0/24)
  • 192.168.1.1 is router1's OTHER interface on the DMZ side

Correct routing:
  1. Hacker uses its configured default gateway: {hacker.default_gateway}
  2. This gateway ({hacker.default_gateway}) IS router1 (eth0 interface)
  3. Router1 then forwards to webserver via its eth1 interface (192.168.1.1)

The confusion:
  • {hacker.default_gateway} and 192.168.1.1 are BOTH router1
  • But they are DIFFERENT interfaces on the same router
  • {hacker.default_gateway} = router1's Internet-facing interface
  • 192.168.1.1 = router1's DMZ-facing interface

So hacker sends TO {hacker.default_gateway}, and router1 forwards FROM 192.168.1.1
    """)

    print("="*70)


if __name__ == '__main__':
    test_gateway_usage()
