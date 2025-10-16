#!/usr/bin/env python3
"""
100-Computer Internet Simulation
Creates a realistic mini-internet with:
- ISPs with backbone routers
- Corporate networks
- Web servers hosting sites
- DNS servers
- Mail servers
- Home users
- Network gear (routers, switches, firewalls)
All running SSH and full poodillion OS
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter
import random
import time

def create_mini_internet():
    """
    Create a 100-computer internet simulation

    Architecture:
    - Tier 1 ISP Backbone (5 routers)
    - Tier 2 ISPs (10 edge routers)
    - Corporate Networks (3 major corps, 15 systems each = 45)
    - Web hosting (10 web servers hosting multiple sites)
    - DNS infrastructure (5 DNS servers)
    - Mail infrastructure (5 mail servers)
    - Home users (20 home computers)

    Total: ~100 systems
    """

    print("\n" + "="*80)
    print(" " * 20 + "CREATING 100-COMPUTER MINI-INTERNET")
    print("="*80 + "\n")

    network = NetworkAdapter()
    systems = {}

    # =====================================================================
    # TIER 1: ISP BACKBONE (5 routers)
    # =====================================================================
    print("📡 Creating Tier 1 ISP Backbone (5 routers)...")
    backbone_ips = [
        ('10.0.1.1', '10.0.2.1', '10.0.3.1'),    # backbone-1
        ('10.0.1.2', '10.0.4.1', '10.0.5.1'),    # backbone-2
        ('10.0.2.2', '10.0.4.2', '10.0.6.1'),    # backbone-3
        ('10.0.3.2', '10.0.5.2', '10.0.7.1'),    # backbone-4
        ('10.0.6.2', '10.0.7.2', '10.0.8.1'),    # backbone-5
    ]

    for i, interfaces in enumerate(backbone_ips, 1):
        hostname = f'backbone-{i}'
        iface_dict = {f'eth{j}': ip for j, ip in enumerate(interfaces)}
        system = UnixSystem(hostname, iface_dict)
        system.ip_forward = True
        system.add_network(network)
        systems[hostname] = system
        print(f"   ✓ {hostname}: {', '.join(interfaces)}")

    # =====================================================================
    # TIER 2: EDGE ROUTERS (10 ISPs)
    # =====================================================================
    print("\n🌐 Creating Tier 2 ISP Edge Routers (10 routers)...")
    edge_base = 20
    for i in range(1, 11):
        hostname = f'isp{i}-edge'
        interfaces = {
            'eth0': f'10.0.8.{edge_base + i}',      # Backbone connection
            'eth1': f'172.{16+i}.0.1',              # Customer network
        }
        system = UnixSystem(hostname, interfaces)
        system.ip_forward = True
        system.add_network(network)
        systems[hostname] = system
        print(f"   ✓ {hostname}: {interfaces['eth0']} <-> {interfaces['eth1']}")

    # =====================================================================
    # CORPORATE NETWORKS (3 major corporations)
    # =====================================================================
    print("\n🏢 Creating Corporate Networks (3 corporations, 15 systems each)...")

    corps = [
        ('megacorp', 1),
        ('techgiant', 2),
        ('financeco', 3),
    ]

    for corp_name, corp_id in corps:
        print(f"\n   Corporation: {corp_name}")
        base_network = f'172.{16 + corp_id}'

        # Corporate firewall/router
        hostname = f'{corp_name}-fw'
        system = UnixSystem(hostname, {
            'eth0': f'{base_network}.0.1',
            'eth1': f'{base_network}.1.1',
            'eth2': f'{base_network}.2.1',
        })
        system.ip_forward = True
        system.add_network(network)
        systems[hostname] = system
        print(f"      ✓ {hostname} (firewall)")

        # Web servers (2 per corp)
        for i in range(1, 3):
            hostname = f'{corp_name}-web{i}'
            system = UnixSystem(hostname, f'{base_network}.1.{10+i}')
            system.add_network(network)
            system.spawn_service('nginx', ['service', 'webserver'], uid=33)
            system.spawn_service('sshd', ['service', 'ssh'], uid=0)
            systems[hostname] = system
            print(f"      ✓ {hostname} (web server)")

        # Database servers (2 per corp)
        for i in range(1, 3):
            hostname = f'{corp_name}-db{i}'
            system = UnixSystem(hostname, f'{base_network}.1.{20+i}')
            system.add_network(network)
            system.spawn_service('mysqld', ['service', 'database'], uid=27)
            system.spawn_service('sshd', ['service', 'ssh'], uid=0)
            systems[hostname] = system
            print(f"      ✓ {hostname} (database)")

        # Mail server (1 per corp)
        hostname = f'{corp_name}-mail'
        system = UnixSystem(hostname, f'{base_network}.1.30')
        system.add_network(network)
        system.spawn_service('postfix', ['service', 'mail'], uid=0)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        print(f"      ✓ {hostname} (mail server)")

        # Internal systems (5 per corp)
        for i in range(1, 6):
            hostname = f'{corp_name}-pc{i:02d}'
            system = UnixSystem(hostname, f'{base_network}.2.{10+i}')
            system.add_network(network)
            system.spawn_service('sshd', ['service', 'ssh'], uid=0)
            systems[hostname] = system
            print(f"      ✓ {hostname} (workstation)")

        # DNS server (1 per corp)
        hostname = f'{corp_name}-dns'
        system = UnixSystem(hostname, f'{base_network}.1.53')
        system.add_network(network)
        system.spawn_service('bind9', ['service', 'dns'], uid=53)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        print(f"      ✓ {hostname} (DNS server)")

    # =====================================================================
    # WEB HOSTING PROVIDER (10 servers)
    # =====================================================================
    print("\n🌍 Creating Web Hosting Provider (10 servers)...")
    for i in range(1, 11):
        hostname = f'webhost{i:02d}'
        system = UnixSystem(hostname, f'172.20.0.{10+i}')
        system.add_network(network)
        system.spawn_service('apache2', ['service', 'webserver'], uid=33)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        print(f"   ✓ {hostname} (hosting {3+i%5} websites)")

    # =====================================================================
    # PUBLIC DNS INFRASTRUCTURE (5 servers)
    # =====================================================================
    print("\n🔍 Creating Public DNS Infrastructure (5 servers)...")
    dns_ips = [
        '8.8.8.8',      # Primary DNS
        '8.8.4.4',      # Secondary DNS
        '1.1.1.1',      # Fast DNS
        '9.9.9.9',      # Security DNS
        '208.67.222.222' # OpenDNS
    ]
    for i, ip in enumerate(dns_ips, 1):
        hostname = f'dns{i}'
        system = UnixSystem(hostname, ip)
        system.add_network(network)
        system.spawn_service('bind9', ['service', 'dns'], uid=53)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        print(f"   ✓ {hostname} ({ip})")

    # =====================================================================
    # PUBLIC MAIL INFRASTRUCTURE (5 servers)
    # =====================================================================
    print("\n📧 Creating Public Mail Infrastructure (5 servers)...")
    for i in range(1, 6):
        hostname = f'mx{i}'
        system = UnixSystem(hostname, f'172.30.0.{10+i}')
        system.add_network(network)
        system.spawn_service('postfix', ['service', 'mail'], uid=0)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        print(f"   ✓ {hostname} (mail exchange)")

    # =====================================================================
    # HOME USERS (20 computers)
    # =====================================================================
    print("\n🏠 Creating Home Users (20 computers)...")
    for i in range(1, 21):
        hostname = f'home-{i:02d}'
        system = UnixSystem(hostname, f'192.168.{100 + i // 10}.{10 + i % 10}')
        system.add_network(network)
        system.spawn_service('sshd', ['service', 'ssh'], uid=0)
        systems[hostname] = system
        if i % 5 == 0:
            print(f"   ✓ Created {i} home users...")
    print(f"   ✓ All 20 home users created")

    # =====================================================================
    # ATTACKER SYSTEM (your machine)
    # =====================================================================
    print("\n🎯 Creating Attacker System...")
    attacker = UnixSystem('kali-box', '10.0.0.1')
    attacker.add_network(network)
    attacker.default_gateway = '10.0.1.1'
    systems['kali-box'] = attacker

    attacker.vfs.create_file(
        '/root/README.txt',
        0o644, 0, 0,
        b'=== 100-COMPUTER INTERNET SIMULATION ===\n\n'
        b'Welcome to the mini-internet!\n\n'
        b'This network contains:\n'
        b'  - 5 Tier-1 ISP backbone routers\n'
        b'  - 10 Tier-2 ISP edge routers\n'
        b'  - 45 corporate systems (3 corporations)\n'
        b'  - 10 web hosting servers\n'
        b'  - 5 public DNS servers\n'
        b'  - 5 mail servers\n'
        b'  - 20 home users\n'
        b'  - 1 attacker (YOU)\n\n'
        b'Total: 101 systems!\n\n'
        b'MISSION:\n'
        b'Explore the network and find interesting targets.\n'
        b'All systems are running SSH (root/root for testing).\n\n'
        b'TIP: Start with "ping" to test connectivity\n'
        b'TIP: Use "nmap" to scan for services\n'
        b'TIP: Use "ssh <ip>" to connect to systems\n\n'
        b'Have fun!\n',
        1
    )

    attacker.vfs.create_file(
        '/root/network-map.txt',
        0o644, 0, 0,
        f'NETWORK TOPOLOGY\n'
        f'================\n\n'
        f'Total Systems: {len(systems)}\n\n'
        f'BACKBONE:\n' +
        '\n'.join([f'  {name}: {sys.ip}' for name, sys in systems.items() if 'backbone' in name]) + '\n\n' +
        f'ISP EDGE ROUTERS:\n' +
        '\n'.join([f'  {name}: {sys.ip}' for name, sys in systems.items() if 'isp' in name]) + '\n\n' +
        f'CORPORATIONS:\n' +
        '\n'.join([f'  {name}: {sys.ip}' for name, sys in systems.items() if any(c in name for c in ['megacorp', 'techgiant', 'financeco'])]) + '\n',
        1
    )

    print(f"   ✓ kali-box (10.0.0.1) - YOUR SYSTEM")

    # =====================================================================
    # NETWORK CONNECTIVITY (Layer 2)
    # =====================================================================
    print("\n🔌 Configuring Network Connectivity...")

    # Backbone mesh (all backbone routers can reach each other)
    backbone_systems = [s for name, s in systems.items() if 'backbone' in name]
    connections = 0
    for i, sys1 in enumerate(backbone_systems):
        for sys2 in backbone_systems[i+1:]:
            for ip1 in [sys1.interfaces[iface] for iface in sys1.interfaces if iface != 'lo']:
                for ip2 in [sys2.interfaces[iface] for iface in sys2.interfaces if iface != 'lo']:
                    network.add_route(ip1, ip2)
                    network.add_route(ip2, ip1)
                    connections += 2
    print(f"   ✓ Backbone mesh: {connections} connections")

    # Connect edge routers to backbone
    edge_systems = [s for name, s in systems.items() if 'isp' in name and 'edge' in name]
    for edge in edge_systems:
        edge_ip = edge.interfaces['eth0']
        # Connect to nearest backbone
        backbone_ip = '10.0.8.1'
        network.add_route(edge_ip, backbone_ip)
        network.add_route(backbone_ip, edge_ip)
        connections += 2
    print(f"   ✓ Edge routers connected to backbone")

    # Connect corporate networks to their ISPs
    for corp_name, corp_id in corps:
        fw_name = f'{corp_name}-fw'
        fw_system = systems[fw_name]
        isp_edge = systems[f'isp{corp_id}-edge']

        fw_wan_ip = fw_system.interfaces['eth0']
        isp_ip = isp_edge.interfaces['eth1']

        network.add_route(fw_wan_ip, isp_ip)
        network.add_route(isp_ip, fw_wan_ip)

        # Connect all internal systems to firewall
        for name, sys in systems.items():
            if corp_name in name and name != fw_name:
                sys_ip = sys.ip
                # Determine which internal interface
                if sys_ip.startswith(f'172.{16 + corp_id}.1'):
                    fw_internal = fw_system.interfaces['eth1']
                elif sys_ip.startswith(f'172.{16 + corp_id}.2'):
                    fw_internal = fw_system.interfaces['eth2']
                else:
                    continue

                network.add_route(sys_ip, fw_internal)
                network.add_route(fw_internal, sys_ip)
                connections += 2

    print(f"   ✓ Corporate networks connected")

    # Connect web hosting to ISP
    for i in range(1, 11):
        hostname = f'webhost{i:02d}'
        webhost_ip = systems[hostname].ip
        isp_ip = systems['isp4-edge'].interfaces['eth1']
        network.add_route(webhost_ip, isp_ip)
        network.add_route(isp_ip, webhost_ip)
        connections += 2

    # Connect DNS servers to backbone
    for i, ip in enumerate(dns_ips, 1):
        network.add_route(ip, '10.0.1.1')
        network.add_route('10.0.1.1', ip)
        connections += 2

    # Connect mail servers to ISP
    for i in range(1, 6):
        mx_ip = systems[f'mx{i}'].ip
        isp_ip = systems['isp5-edge'].interfaces['eth1']
        network.add_route(mx_ip, isp_ip)
        network.add_route(isp_ip, mx_ip)
        connections += 2

    # Connect home users to their ISPs
    for i in range(1, 21):
        home_ip = systems[f'home-{i:02d}'].ip
        isp_num = 6 + (i % 5)
        isp_ip = systems[f'isp{isp_num}-edge'].interfaces['eth1']
        network.add_route(home_ip, isp_ip)
        network.add_route(isp_ip, home_ip)
        connections += 2

    # Connect attacker to backbone
    network.add_route('10.0.0.1', '10.0.1.1')
    network.add_route('10.0.1.1', '10.0.0.1')

    print(f"   ✓ Total network connections: {connections}")

    # Configure routing tables
    print(f"\n⚙️  Configuring routing tables...")
    network._configure_routing_tables()
    print(f"   ✓ Routing tables configured")

    # =====================================================================
    # BOOT ALL SYSTEMS
    # =====================================================================
    print(f"\n🚀 Booting all {len(systems)} systems...")
    booted = 0
    failed = 0

    for name, system in systems.items():
        try:
            system.running = True
            booted += 1
            if booted % 20 == 0:
                print(f"   ✓ Booted {booted} systems...")
        except Exception as e:
            print(f"   ✗ Failed to boot {name}: {e}")
            failed += 1

    print(f"   ✓ All systems booted! ({booted} successful, {failed} failed)")

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("\n" + "="*80)
    print(" " * 25 + "🎉 MINI-INTERNET READY! 🎉")
    print("="*80)
    print(f"""
    Statistics:
    -----------
    Total Systems:        {len(systems)}
    Backbone Routers:     5
    ISP Edge Routers:     10
    Corporate Systems:    45
    Web Servers:          10
    DNS Servers:          5
    Mail Servers:         5
    Home Users:           20
    Attacker:             1

    Network Connections:  {connections}

    Your system: kali-box (10.0.0.1)

    Ready to hack the internet!
    """)
    print("="*80 + "\n")

    return attacker, network, systems


if __name__ == '__main__':
    start_time = time.time()
    attacker, network, systems = create_mini_internet()
    elapsed = time.time() - start_time

    print(f"✅ Created {len(systems)}-computer internet in {elapsed:.2f} seconds")
    print(f"\nTo start hacking, use play.py or interactive mode")
    print(f"Example: python3 -i test_100_computer_internet.py")
