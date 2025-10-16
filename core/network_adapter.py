"""
Network Adapter - Bridges old VirtualNetwork API with new PhysicalNetwork

This allows scenarios written for the old network API to work with the new
PooScript-driven physical network architecture.
"""

from core.network import VirtualNetwork
from core.network_physical import PhysicalNetwork, NetworkSegment
from typing import Dict, Set, Tuple


class NetworkAdapter:
    """
    Adapter that provides VirtualNetwork API but uses PhysicalNetwork underneath

    This allows existing scenarios to work without modification while using
    the new PooScript-driven network architecture.
    """

    def __init__(self):
        # Create both old and new network layers
        self.virtual_network = VirtualNetwork()
        self.physical_network = PhysicalNetwork()

        # Track which systems are on which segments
        # subnet -> segment
        self.segments: Dict[str, NetworkSegment] = {}

        # Track routing topology from add_route() calls
        # This tells us which systems can directly communicate (Layer 2)
        self.direct_routes: Set[Tuple[str, str]] = set()

    def register_system(self, ip: str, system: 'UnixSystem'):
        """Register a system on the network"""
        # Register with virtual network (for backward compat)
        self.virtual_network.register_system(ip, system)

        # Register with physical network
        self.physical_network.register_system(system, ip)

        # Determine subnet for this IP
        subnet = self._get_subnet(ip)

        # Get or create segment for this subnet
        if subnet not in self.segments:
            self.segments[subnet] = self.physical_network.create_segment(f'seg_{subnet}')

        segment = self.segments[subnet]

        # Connect all interfaces in this subnet to the segment
        for iface_name, iface_ip in system.interfaces.items():
            if iface_name == 'lo':
                continue

            iface_subnet = self._get_subnet(iface_ip)
            if iface_subnet == subnet:
                # This interface is on this subnet's segment
                if iface_name in system.net_interfaces:
                    net_iface = system.net_interfaces[iface_name]
                    segment.attach_interface(net_iface)

    def add_route(self, src_ip: str, dst_ip: str):
        """
        Add a Layer-2 route (direct connectivity)

        In the new architecture, this means the systems are on the same
        broadcast domain (segment).
        """
        # Track for routing decisions
        self.direct_routes.add((src_ip, dst_ip))

        # Add to virtual network for backward compat
        self.virtual_network.add_route(src_ip, dst_ip)

        # Get systems
        src_system = self.physical_network.get_system_by_ip(src_ip)
        dst_system = self.physical_network.get_system_by_ip(dst_ip)

        if not src_system or not dst_system:
            return

        # If they're on different subnets, they need a router
        src_subnet = self._get_subnet(src_ip)
        dst_subnet = self._get_subnet(dst_ip)

        if src_subnet == dst_subnet:
            # Same subnet - should already be on same segment
            pass
        else:
            # Different subnets - they connect through a router
            # Find if src_system has an interface on dst_subnet (is a router)
            for iface_ip in src_system.interfaces.values():
                if self._get_subnet(iface_ip) == dst_subnet:
                    # src_system is a router! Connect its interface to dst_subnet segment
                    for iface_name, ip in src_system.interfaces.items():
                        if ip == iface_ip and iface_name in src_system.net_interfaces:
                            dst_segment = self.segments.get(dst_subnet)
                            if dst_segment:
                                net_iface = src_system.net_interfaces[iface_name]
                                if net_iface not in dst_segment.interfaces:
                                    dst_segment.attach_interface(net_iface)

            # Same check for dst_system
            for iface_ip in dst_system.interfaces.values():
                if self._get_subnet(iface_ip) == src_subnet:
                    for iface_name, ip in dst_system.interfaces.items():
                        if ip == iface_ip and iface_name in dst_system.net_interfaces:
                            src_segment = self.segments.get(src_subnet)
                            if src_segment:
                                net_iface = dst_system.net_interfaces[iface_name]
                                if net_iface not in src_segment.interfaces:
                                    src_segment.attach_interface(net_iface)

    def add_firewall_rule(self, target_ip: str, action: str, port: int):
        """Add firewall rule (backward compat)"""
        self.virtual_network.add_firewall_rule(target_ip, action, port)

        # Add to target system's firewall rules
        system = self.physical_network.get_system_by_ip(target_ip)
        if system:
            system.firewall_rules.append({
                'action': action,
                'port': port,
                'target': target_ip
            })

    def _get_subnet(self, ip: str) -> str:
        """Get /24 subnet for an IP"""
        parts = ip.split('.')
        return '.'.join(parts[:3]) + '.0/24'

    def _configure_routing_tables(self):
        """
        Configure routing tables on all routers based on topology

        This should be called after all systems are registered and routes added.
        """
        # Find all routers (systems with ip_forward=True or multiple interfaces)
        routers = []
        for system in self.physical_network.systems.values():
            if system.ip_forward or len([i for i in system.interfaces.keys() if i != 'lo']) > 1:
                routers.append(system)

        # For each router, build routing table
        for router in routers:
            routes_content = "# Routing table\n"
            routes_content += "# Format: destination gateway netmask interface\n\n"

            # Add directly connected networks
            for iface_name, iface_ip in router.interfaces.items():
                if iface_name == 'lo':
                    continue

                subnet = self._get_subnet(iface_ip)
                subnet_base = '.'.join(subnet.split('.')[:3]) + '.0'

                # Directly connected network (no gateway)
                routes_content += f"{subnet_base} 0.0.0.0 255.255.255.0 {iface_name}\n"

            # Add default route if default_gateway is set
            if router.default_gateway:
                # Find which interface reaches the gateway
                for iface_name, iface_ip in router.interfaces.items():
                    if self._get_subnet(iface_ip) == self._get_subnet(router.default_gateway):
                        routes_content += f"0.0.0.0 {router.default_gateway} 0.0.0.0 {iface_name}\n"
                        break

            # Write routing table
            router.vfs.write_file('/etc/network/routes', routes_content.encode(), 1)

    @property
    def systems(self) -> Dict[str, 'UnixSystem']:
        """Get all systems (for backward compat)"""
        return self.virtual_network.systems

    def get_system_by_ip(self, ip: str) -> 'UnixSystem':
        """Get system by IP"""
        return self.physical_network.get_system_by_ip(ip)
