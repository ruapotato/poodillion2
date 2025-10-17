#!/usr/bin/env python3
"""
Test Scenario 0 with new PhysicalNetwork architecture
"""

from scenarios import create_scenario_zero

def test_scenario_zero():
    """Test that scenario 0 creates successfully with new architecture"""

    print("=" * 80)
    print("Testing Scenario 0 - SSH Training Network")
    print("=" * 80)

    # Create scenario
    print("\n1. Creating scenario...")
    attacker, network, metadata = create_scenario_zero()

    print(f"   ✓ Attacker: {attacker.hostname} @ {attacker.ip}")
    print(f"   ✓ Network type: {type(network).__name__}")
    print(f"   ✓ Systems: {len(metadata['systems'])}")

    # Check physical network setup
    print("\n2. Checking physical network...")
    print(f"   ✓ Physical network: {len(network.physical_network.segments)} segments")

    for seg_name, segment in network.physical_network.segments.items():
        print(f"   ✓ Segment '{seg_name}': {len(segment.interfaces)} interfaces")
        for iface in segment.interfaces:
            system_ip = None
            # Find which system this interface belongs to
            for ip, sys in network.physical_network.systems.items():
                if iface in sys.net_interfaces.values():
                    system_ip = ip
                    break
            print(f"      - {iface.name} (MAC: {iface.mac}) @ {system_ip}")

    # Check device files
    print("\n3. Checking device files on attacker...")
    entries = attacker.vfs.list_dir('/dev/net', 1)
    if entries:
        for name, ino in sorted(entries):
            if name not in ('.', '..'):
                print(f"   ✓ /dev/net/{name}")

    # Boot all systems
    print("\n4. Booting systems...")
    for system in metadata['systems']:
        print(f"   Booting {system.hostname}...")
        system.boot()
        print(f"   ✓ {system.hostname} is {'alive' if system.is_alive() else 'dead'}")

    # Test packet transmission
    print("\n5. Testing packet transmission...")

    # Get two systems from same subnet
    system1 = metadata['systems'][0]  # attacker
    system2 = metadata['systems'][2]  # server-alpha

    print(f"   Sending packet from {system1.hostname} to {system2.hostname}...")

    # Build test packet
    packet = bytearray(40)
    packet[0] = 0x45  # Version 4, IHL 5
    packet[8] = 64    # TTL

    # Source IP: system1.ip
    src_parts = [int(x) for x in system1.ip.split('.')]
    packet[12:16] = bytes(src_parts)

    # Dest IP: system2.ip
    dst_parts = [int(x) for x in system2.ip.split('.')]
    packet[16:20] = bytes(dst_parts)

    # Send from system1
    system1.vfs.write_file('/dev/net/eth0_raw', bytes(packet), 1)
    print(f"   ✓ Sent {len(packet)} bytes from {system1.hostname}")

    # Check if system2 received
    received = system2.net_interfaces['eth0'].recv_raw()
    if received:
        print(f"   ✓ {system2.hostname} received {len(received)} bytes")
        print(f"   ✓ Payload matches: {received == bytes(packet)}")
    else:
        print(f"   ✗ {system2.hostname} did not receive packet")

    # Check routing table files
    print("\n6. Checking routing configuration...")
    for system in metadata['systems']:
        if system.ip_forward or len([i for i in system.interfaces if i != 'lo']) > 1:
            routes_file = system.vfs.read_file('/etc/network/routes', 1)
            if routes_file:
                num_routes = len([l for l in routes_file.decode().split('\n') if l and not l.startswith('#')])
                print(f"   ✓ {system.hostname}: {num_routes} routes configured")

    print("\n" + "=" * 80)
    print("✓ Scenario 0 Test Complete!")
    print("=" * 80)
    print("\nScenario is ready to play with:")
    print("  python3 play.py")
    print("  Select option [0] for SSH Training\n")

if __name__ == '__main__':
    test_scenario_zero()
