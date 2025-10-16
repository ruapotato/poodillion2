"""
Virtual network layer
Allows multiple systems to connect and communicate
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import random


@dataclass
class NetworkInterface:
    """Network interface"""
    name: str  # e.g., eth0
    ip_address: str
    netmask: str = '255.255.255.0'
    gateway: Optional[str] = None
    up: bool = True


@dataclass
class Route:
    """Routing table entry"""
    destination: str
    gateway: str
    netmask: str
    interface: str


@dataclass
class Connection:
    """Active network connection"""
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    protocol: str  # tcp, udp
    state: str  # ESTABLISHED, LISTEN, etc.


class VirtualNetwork:
    """Virtual network connecting multiple systems"""

    def __init__(self):
        # Map of IP address to system ID
        self.systems: Dict[str, 'UnixSystem'] = {}

        # Network topology (which IPs can reach which)
        self.connections: Dict[str, Set[str]] = {}

        # Firewall rules per system
        self.firewalls: Dict[str, List[dict]] = {}

    def register_system(self, ip: str, system: 'UnixSystem'):
        """Register a system on the network"""
        self.systems[ip] = system
        self.connections[ip] = set()
        self.firewalls[ip] = []

    def add_route(self, from_ip: str, to_ip: str):
        """Allow network connection between two IPs"""
        if from_ip in self.connections:
            self.connections[from_ip].add(to_ip)

    def can_connect(self, from_ip: str, to_ip: str, port: int = 22) -> bool:
        """
        Check if from_ip can connect to to_ip on given port
        Supports multi-hop routing through intermediate systems with ip_forward enabled
        """
        # Localhost/loopback always works
        if to_ip == '127.0.0.1' or to_ip == from_ip:
            return True

        # Try to find a route (direct or through routers)
        path = self._find_route_path(from_ip, to_ip)
        if not path:
            return False

        # Check firewall rules on target system
        return self._check_firewall(to_ip, port, from_ip)

    def _find_route_path(self, from_ip: str, to_ip: str) -> Optional[List[str]]:
        """
        Find network path from source to destination using BFS
        Returns path as list of IPs, or None if no route exists
        Respects ip_forward flag AND system alive state on intermediate systems
        """
        # Localhost/loopback - pinging yourself always works if system is alive
        if from_ip == to_ip:
            src_system = self.systems.get(from_ip)
            if src_system and src_system.is_alive():
                return [from_ip]
            return None

        # Direct connection?
        if from_ip in self.connections and to_ip in self.connections.get(from_ip, set()):
            # Check if destination system is alive
            dest_system = self.systems.get(to_ip)
            if dest_system and not dest_system.is_alive():
                return None  # Destination is down
            return [from_ip, to_ip]

        # BFS to find path through routers
        visited_systems = set()  # Track systems, not just IPs
        visited_ips = set([from_ip])
        queue = [(from_ip, [from_ip])]

        while queue:
            current_ip, path = queue.pop(0)

            # Get the system at this IP
            current_system = self.systems.get(current_ip)
            if current_system:
                # Check if this intermediate system is alive
                if len(path) > 1 and not current_system.is_alive():
                    # Intermediate router/system is down, can't route through it
                    continue

                # Mark this system as visited
                system_id = id(current_system)
                if system_id in visited_systems:
                    continue
                visited_systems.add(system_id)

            # Check all directly reachable IPs from current position
            for next_ip in self.connections.get(current_ip, set()):
                if next_ip in visited_ips:
                    continue

                # Check if next hop system is alive
                next_system = self.systems.get(next_ip)
                if next_system and not next_system.is_alive():
                    # Next hop is down, skip it
                    continue

                visited_ips.add(next_ip)
                new_path = path + [next_ip]

                # Found destination!
                if next_ip == to_ip:
                    return new_path

                # Can this system forward packets to other networks?
                # Only if it's alive AND has ip_forward enabled
                if next_system and next_system.is_alive() and getattr(next_system, 'ip_forward', False):
                    # This is a router - continue searching from ALL its interfaces
                    # Check routes from ALL interfaces of this system
                    for interface, interface_ip in next_system.interfaces.items():
                        if interface != 'lo' and interface_ip != '127.0.0.1':
                            if interface_ip not in visited_ips:
                                # Add routes from this interface to the queue
                                for dest in self.connections.get(interface_ip, set()):
                                    if dest not in visited_ips:
                                        queue.append((interface_ip, new_path))

        return None  # No route found

    def _check_firewall(self, target_ip: str, port: int, source_ip: str) -> bool:
        """Check if firewall on target allows connection from source"""
        target_system = self.systems.get(target_ip)
        if target_system and hasattr(target_system, 'firewall_rules'):
            # Check system's iptables rules
            for rule in target_system.firewall_rules:
                if rule.get('action') == 'DROP' and rule.get('port') == port:
                    # Check if source is blocked
                    source_rule = rule.get('source', 'any')
                    if source_rule == 'any':
                        return False  # Blocks all sources
                    # Check if source IP matches the rule
                    if source_ip.startswith(source_rule.replace('/8', '').replace('/16', '').replace('/24', '')):
                        return False

        # Legacy firewall rules (for backward compatibility)
        if target_ip in self.firewalls:
            for rule in self.firewalls[target_ip]:
                if rule.get('action') == 'DENY' and rule.get('port') == port:
                    return False

        return True  # No blocking rules found

    def add_firewall_rule(self, ip: str, action: str, port: int):
        """Add firewall rule"""
        if ip in self.firewalls:
            self.firewalls[ip].append({'action': action, 'port': port})

    def scan_network(self, from_ip: str, subnet: str) -> List[str]:
        """Scan network for active hosts (simplified)"""
        # Return all reachable IPs
        if from_ip not in self.connections:
            return []

        # Parse subnet parameter (e.g., "192.168.1.0/24")
        if '/' in subnet:
            subnet_base = subnet.split('/')[0]
            # Get /24 prefix (first 3 octets)
            subnet_prefix = '.'.join(subnet_base.split('.')[:3])
        else:
            # If no CIDR notation, assume it's a single IP
            subnet_prefix = '.'.join(subnet.split('.')[:3])

        reachable = []

        for ip in self.systems.keys():
            if ip.startswith(subnet_prefix) and ip != from_ip:
                # Check if we can actually reach this IP
                if self.can_connect(from_ip, ip, 0):
                    reachable.append(ip)

        return reachable

    def port_scan(self, from_ip: str, to_ip: str) -> List[int]:
        """Scan ports on target (game mechanic)"""
        if not self.can_connect(from_ip, to_ip, 0):
            return []

        target_system = self.systems.get(to_ip)
        if not target_system:
            return []

        # Find listening services
        open_ports = []
        for process in target_system.processes.list_processes():
            if 'service' in process.tags or 'server' in process.tags:
                # Assign pseudo-random port based on process
                port = 1024 + (process.pid * 137) % 60000
                open_ports.append(port)

        return sorted(open_ports)


class NetworkCommands:
    """Network-related commands"""

    def __init__(self, vfs, permissions, processes, network):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes
        self.network = network

    def cmd_ifconfig(self, command, current_pid: int, input_data: bytes):
        """Show network interfaces"""
        # Simplified - just show static config
        output = """eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255
        ether 08:00:27:12:34:56  txqueuelen 1000  (Ethernet)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        loop  txqueuelen 1000  (Local Loopback)
"""
        return 0, output.encode(), b''

    def cmd_netstat(self, command, current_pid: int, input_data: bytes):
        """Show network statistics and connections"""
        lines = ['Proto Recv-Q Send-Q Local Address           Foreign Address         State']

        # Show some dummy connections
        lines.append('tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN')
        lines.append('tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN')

        return 0, '\n'.join(lines).encode() + b'\n', b''

    def cmd_nmap(self, command, current_pid: int, input_data: bytes):
        """Network scanner (game mechanic)"""
        if not command.args:
            return 1, b'', b'nmap: missing target\n'

        target = command.args[0]

        # Get current system IP (simplified)
        current_ip = '192.168.1.100'  # Would be looked up from process/system

        # Check if target is an IP or subnet
        if target.endswith('/24'):
            # Subnet scan
            hosts = self.network.scan_network(current_ip, target)
            output = f'Starting Nmap scan on {target}\n\n'
            output += f'Nmap scan report - {len(hosts)} hosts up\n'
            for host in hosts:
                output += f'{host}\n'
        else:
            # Single host scan
            ports = self.network.port_scan(current_ip, target)
            output = f'Starting Nmap 7.01 ( https://nmap.org )\n'
            output += f'Nmap scan report for {target}\n'
            output += f'Host is up (0.00052s latency).\n\n'
            output += 'PORT     STATE SERVICE\n'

            for port in ports[:10]:  # Limit to 10 for display
                service = {22: 'ssh', 80: 'http', 443: 'https', 3306: 'mysql'}.get(port, 'unknown')
                output += f'{port}/tcp  open  {service}\n'

        return 0, output.encode(), b''

    def cmd_ssh(self, command, current_pid: int, input_data: bytes):
        """SSH to remote system (game mechanic)"""
        if not command.args:
            return 1, b'', b'ssh: missing target\n'

        target = command.args[0]

        # Parse user@host
        if '@' in target:
            username, host = target.split('@', 1)
        else:
            username = 'root'
            host = target

        output = f'Connecting to {host}...\n'
        output += f'[This would open a shell on {host} as {username}]\n'
        output += '[Feature coming soon]\n'

        return 0, output.encode(), b''
