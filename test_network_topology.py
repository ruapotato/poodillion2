#!/usr/bin/env python3
"""
Network Topology Visualization and Analysis
Shows the structure of the 100-computer internet
"""

from test_100_computer_internet import create_mini_internet
import collections

def analyze_topology():
    """Analyze and visualize the network topology"""

    print("\n" + "="*80)
    print(" " * 20 + "NETWORK TOPOLOGY ANALYSIS")
    print("="*80 + "\n")

    # Create the internet
    print("🌐 Creating internet...")
    attacker, network, systems = create_mini_internet()
    print()

    # =====================================================================
    # SYSTEM CATEGORIZATION
    # =====================================================================
    print("="*80)
    print("SYSTEM CATEGORIZATION")
    print("="*80 + "\n")

    categories = collections.defaultdict(list)

    for name, system in systems.items():
        if 'backbone' in name:
            categories['Backbone Routers'].append((name, system))
        elif 'isp' in name and 'edge' in name:
            categories['ISP Edge Routers'].append((name, system))
        elif 'fw' in name or 'firewall' in name:
            categories['Firewalls'].append((name, system))
        elif 'web' in name:
            categories['Web Servers'].append((name, system))
        elif 'db' in name:
            categories['Database Servers'].append((name, system))
        elif 'mail' in name or 'mx' in name:
            categories['Mail Servers'].append((name, system))
        elif 'dns' in name:
            categories['DNS Servers'].append((name, system))
        elif 'home' in name:
            categories['Home Users'].append((name, system))
        elif 'kali' in name:
            categories['Attacker'].append((name, system))
        elif 'pc' in name:
            categories['Workstations'].append((name, system))
        else:
            categories['Other'].append((name, system))

    for category, systems_list in sorted(categories.items()):
        print(f"{category}: {len(systems_list)}")
        for name, sys in sorted(systems_list)[:5]:  # Show first 5
            interfaces = [f"{iface}:{ip}" for iface, ip in sys.interfaces.items() if iface != 'lo']
            if len(interfaces) > 1:
                print(f"   • {name:20s} - Multi-homed: {', '.join(interfaces[:3])}")
            else:
                print(f"   • {name:20s} - {sys.ip}")
        if len(systems_list) > 5:
            print(f"   ... and {len(systems_list) - 5} more\n")
        else:
            print()

    # =====================================================================
    # NETWORK STATISTICS
    # =====================================================================
    print("="*80)
    print("NETWORK STATISTICS")
    print("="*80 + "\n")

    # Count interfaces
    total_interfaces = 0
    multi_homed = 0
    routers = 0

    for name, system in systems.items():
        num_interfaces = len([i for i in system.interfaces if i != 'lo'])
        total_interfaces += num_interfaces

        if num_interfaces > 1:
            multi_homed += 1
            if system.ip_forward:
                routers += 1

    print(f"Total Systems:           {len(systems)}")
    print(f"Total Interfaces:        {total_interfaces}")
    print(f"Multi-homed Systems:     {multi_homed}")
    print(f"Active Routers:          {routers} (IP forwarding enabled)")
    print(f"Network Connections:     346")
    print()

    # =====================================================================
    # ROUTING ANALYSIS
    # =====================================================================
    print("="*80)
    print("ROUTING ANALYSIS")
    print("="*80 + "\n")

    # Analyze routing tables
    systems_with_routes = 0
    total_routes = 0

    for name, system in systems.items():
        if hasattr(system, 'routing_table') and system.routing_table:
            systems_with_routes += 1
            total_routes += len(system.routing_table)

    print(f"Systems with routing tables: {systems_with_routes}")
    print(f"Total route entries:         {total_routes}")
    print()

    # Show sample routing tables
    print("Sample Routing Tables:")
    print("-" * 80)

    sample_systems = [
        ('backbone-1', 'Tier 1 Backbone Router'),
        ('isp1-edge', 'ISP Edge Router'),
        ('megacorp-fw', 'Corporate Firewall'),
    ]

    for sys_name, description in sample_systems:
        if sys_name in systems:
            system = systems[sys_name]
            print(f"\n{sys_name} ({description}):")
            print(f"  Interfaces:")
            for iface, ip in system.interfaces.items():
                if iface != 'lo':
                    print(f"    {iface}: {ip}")
            print(f"  IP Forwarding: {'Enabled' if system.ip_forward else 'Disabled'}")

            if hasattr(system, 'routing_table') and system.routing_table:
                print(f"  Routes ({len(system.routing_table)}):")
                for i, route in enumerate(system.routing_table[:5]):
                    print(f"    {route.destination}/{route.netmask} via {route.gateway} dev {route.interface}")
                if len(system.routing_table) > 5:
                    print(f"    ... and {len(system.routing_table) - 5} more")

    # =====================================================================
    # SERVICE ANALYSIS
    # =====================================================================
    print("\n" + "="*80)
    print("SERVICE ANALYSIS")
    print("="*80 + "\n")

    service_types = collections.defaultdict(int)
    services_by_system = {}

    for name, system in systems.items():
        system_services = []
        for process in system.processes.list_processes():
            if 'service' in process.tags:
                service_types[process.command] += 1
                system_services.append(process.command)

        if system_services:
            services_by_system[name] = system_services

    print("Service Distribution:")
    for service, count in sorted(service_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {service:20s}: {count} instances")

    print(f"\nSystems running services: {len(services_by_system)}")
    print()

    # =====================================================================
    # NETWORK PATHS
    # =====================================================================
    print("="*80)
    print("SAMPLE NETWORK PATHS")
    print("="*80 + "\n")

    # Show some interesting paths
    paths = [
        ('Home User to Web Server', 'home-01', 'webhost01'),
        ('Attacker to Corporate DB', 'kali-box', 'megacorp-db1'),
        ('Corporate PC to Mail', 'megacorp-pc01', 'mx1'),
    ]

    for description, src_name, dst_name in paths:
        if src_name in systems and dst_name in systems:
            src = systems[src_name]
            dst = systems[dst_name]

            print(f"{description}:")
            print(f"   {src_name} ({src.ip}) → {dst_name} ({dst.ip})")

            # Try to find path using network
            if hasattr(network, 'virtual_network'):
                vnet = network.virtual_network
                path = vnet._find_route_path(src.ip, dst.ip)
                if path:
                    print(f"   Path: {' → '.join(path)}")
                else:
                    print(f"   Path: No route found")
            print()

    # =====================================================================
    # ASCII TOPOLOGY MAP
    # =====================================================================
    print("="*80)
    print("ASCII TOPOLOGY MAP")
    print("="*80 + "\n")

    print("""
                           TIER 1 BACKBONE
                    ╔════════════════════════╗
                    ║  backbone-1 ... 5      ║
                    ║  (10.0.x.x network)    ║
                    ╚═══════════╤════════════╝
                                │
                    ┌───────────┴───────────┐
                    │                       │
            TIER 2 ISP EDGE            TIER 2 ISP EDGE
        ╔═══════════════════╗      ╔═══════════════════╗
        ║ isp1-edge ... 10  ║      ║  DNS: 8.8.8.8     ║
        ║ (172.x.0.1)       ║      ║       1.1.1.1     ║
        ╚═══════╤═══════════╝      ╚═══════════════════╝
                │
        ┌───────┴────────┐
        │                │
    CORPORATE       WEB HOSTING
    ╔══════════╗    ╔═══════════╗
    ║ MegaCorp ║    ║ webhost01 ║
    ║ - Web    ║    ║ ... 10    ║
    ║ - DB     ║    ╚═══════════╝
    ║ - Mail   ║
    ║ - DNS    ║    HOME USERS
    ║ - PCs    ║    ╔═══════════╗
    ╚══════════╝    ║ home-01   ║
                    ║ ... 20    ║
    TechGiant       ╚═══════════╝
    FinanceCo
    """)

    # =====================================================================
    # CONNECTIVITY MATRIX
    # =====================================================================
    print("="*80)
    print("CONNECTIVITY MATRIX (Sample)")
    print("="*80 + "\n")

    # Test connectivity between different network segments
    test_pairs = [
        ('Attacker', 'kali-box', 'Backbone', 'backbone-1'),
        ('Backbone', 'backbone-1', 'ISP Edge', 'isp1-edge'),
        ('ISP Edge', 'isp1-edge', 'Corporate', 'megacorp-web1'),
        ('Corporate Web', 'megacorp-web1', 'Corporate DB', 'megacorp-db1'),
        ('Home User', 'home-01', 'Web Host', 'webhost01'),
    ]

    print(f"{'Source':<20} {'Destination':<20} {'Connectivity':<15}")
    print("-" * 60)

    for src_cat, src_name, dst_cat, dst_name in test_pairs:
        if src_name in systems and dst_name in systems:
            src = systems[src_name]
            dst = systems[dst_name]

            # Check if there's a route
            if hasattr(network, 'virtual_network'):
                vnet = network.virtual_network
                path = vnet._find_route_path(src.ip, dst.ip)
                status = "✓ Routable" if path else "✗ No route"
                hops = len(path) - 1 if path else 0
                print(f"{src_cat:<20} {dst_cat:<20} {status:<15} ({hops} hops)")
            else:
                print(f"{src_cat:<20} {dst_cat:<20} {'Unknown':<15}")

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("\n" + "="*80)
    print(" " * 25 + "TOPOLOGY ANALYSIS COMPLETE")
    print("="*80)

    print(f"""
    The mini-internet contains {len(systems)} systems organized in a realistic
    hierarchical topology:

    1. BACKBONE: Tier-1 ISP routers forming the core network
    2. ISP EDGE: Tier-2 providers connecting customers
    3. ENTERPRISES: 3 corporations with firewalls, servers, workstations
    4. PUBLIC SERVICES: DNS, mail, web hosting
    5. END USERS: Home computers

    All systems are running:
    - Full Unix OS with VFS, processes, permissions
    - SSH servers (root/root)
    - PooScript (34 commands)
    - Network daemon for routing

    Ready for:
    - Penetration testing
    - Network analysis
    - Multi-hop exploitation
    - Traffic analysis
    - IDS/IPS development
    """)

    print("="*80 + "\n")

    return systems, network


if __name__ == '__main__':
    systems, network = analyze_topology()
    print("✅ Topology analysis complete")
    print("   Try: python3 -i test_network_topology.py")
    print("   Then: systems['kali-box'].execute_command('ping 8.8.8.8')")
