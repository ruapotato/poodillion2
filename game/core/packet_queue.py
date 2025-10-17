"""
Packet queue for device-based networking
Handles packet queueing, routing, and delivery

This implements a real packet-based network where:
- Packets are actual byte streams with IP/TCP/UDP/ICMP headers
- Routing happens hop-by-hop through intermediate systems
- TTL decrements at each hop (enables traceroute)
- Packets can be captured for analysis (tcpdump)
"""

from typing import Optional, List, Tuple, Dict
import struct
import time


class Packet:
    """Network packet with headers and metadata"""
    def __init__(self, raw_bytes: bytes, interface: str = 'eth0'):
        self.raw = raw_bytes
        self.timestamp = time.time()
        self.interface = interface  # Which interface this packet was seen on
        self.hops = []  # Track which systems this packet traversed

    def __bytes__(self):
        return self.raw

    def add_hop(self, ip: str):
        """Record that packet passed through this IP"""
        self.hops.append((ip, time.time()))


class PacketQueue:
    """
    Packet queue for network device I/O
    Each system has its own queue for inbound/outbound packets
    """

    def __init__(self, system: 'UnixSystem', network: 'VirtualNetwork' = None):
        """
        Initialize packet queue

        Args:
            system: The UnixSystem this queue belongs to
            network: The VirtualNetwork this system is connected to
        """
        self.system = system
        self.network = network
        self.inbound: List[Packet] = []  # Packets waiting to be read
        self.outbound: List[Packet] = []  # Packets to be sent (not used yet)

    def send_packet(self, packet_bytes: bytes, capture: bool = True) -> bool:
        """
        Send a packet through the network with multi-hop routing

        This simulates real packet forwarding:
        1. Parse IP header to get destination
        2. Find route (may go through multiple routers)
        3. Forward hop-by-hop, decrementing TTL
        4. Deliver to final destination (with firewall checking)

        Args:
            packet_bytes: Raw packet bytes (IP packet)
            capture: Whether to add this packet to capture buffer

        Returns:
            True if packet was sent successfully
        """
        if not self.network:
            return False

        try:
            # Parse IP header
            ip_header = parse_ip_packet(packet_bytes)
            dest_ip = ip_header['dst']
            src_ip = ip_header['src']
            ttl = ip_header['ttl']

            # Check TTL
            if ttl <= 0:
                # TTL expired - send ICMP Time Exceeded back to source
                self._send_icmp_time_exceeded(src_ip, packet_bytes)
                return False

            # Find complete route to destination
            path = self.network._find_route_path(src_ip, dest_ip)
            if not path:
                # No route - send ICMP Destination Unreachable
                self._send_icmp_unreachable(src_ip, packet_bytes)
                return False

            # Create packet object to track hops
            packet = Packet(packet_bytes, interface='eth0')

            # Handle localhost case (path contains only source IP)
            if len(path) == 1 and path[0] == src_ip == dest_ip:
                # Localhost packet
                packet.add_hop(src_ip)

                # For ICMP Echo Request, generate reply immediately
                # Don't deliver the request itself to inbound queue
                header = parse_ip_packet(packet_bytes)
                if header['protocol'] == 1:  # ICMP
                    icmp = parse_icmp_packet(header['data'])
                    if icmp and icmp['type'] == 8:  # Echo Request
                        # Capture the outbound request
                        self._capture_packet(packet, 'send')

                        # Build and deliver Echo Reply
                        reply_packet = build_icmp_echo_reply(
                            src_ip, src_ip,  # Both src and dst are ourselves
                            icmp['id'], icmp['sequence'],
                            icmp['data']
                        )
                        # Deliver reply to inbound queue
                        reply = Packet(reply_packet, interface='lo')
                        reply.add_hop(src_ip)
                        self.inbound.append(reply)
                        self._capture_packet(reply, 'recv')
                        return True

                # For other localhost packets, deliver normally
                self.inbound.append(packet)
                self._capture_packet(packet, 'recv')
                return True

            # Forward packet through each hop in the path
            current_bytes = packet_bytes
            for i in range(len(path) - 1):
                current_ip = path[i]
                next_ip = path[i + 1]

                # Get the system at this hop
                hop_system = self.network.systems.get(current_ip)
                if not hop_system:
                    return False

                # Check if system is alive
                if not hop_system.is_alive():
                    # Router is down - packet dropped
                    return False

                # Record hop
                packet.add_hop(current_ip)

                # Decrement TTL for each hop (except source)
                if i > 0:
                    current_bytes = _decrement_ttl(current_bytes)
                    new_header = parse_ip_packet(current_bytes)
                    if new_header['ttl'] <= 0:
                        # TTL expired at this hop
                        self._send_icmp_time_exceeded_from(current_ip, src_ip, packet_bytes)
                        return False

                # Capture packet at intermediate router if enabled
                if capture and i > 0 and hasattr(hop_system, 'packet_queue'):
                    hop_system.packet_queue._capture_packet(packet, 'forward')

            # Final destination
            dest_system = self.network.systems.get(dest_ip)
            if not dest_system or not dest_system.is_alive():
                return False

            # Update packet with final bytes
            packet.raw = current_bytes
            packet.add_hop(dest_ip)

            # PACKET-LEVEL FIREWALL CHECK
            # Check firewall rules before delivering to destination
            if not self._check_packet_firewall(current_bytes, dest_system, src_ip):
                # Packet blocked by firewall - drop silently
                if capture:
                    dest_system.packet_queue._capture_packet(packet, 'drop')
                return False

            # Deliver to destination's inbound queue
            if hasattr(dest_system, 'packet_queue'):
                dest_system.packet_queue.inbound.append(packet)

                # Capture at destination
                if capture:
                    dest_system.packet_queue._capture_packet(packet, 'recv')

                # Auto-respond to ICMP Echo Request (ping)
                final_header = parse_ip_packet(current_bytes)
                if final_header['protocol'] == 1:  # ICMP
                    icmp = parse_icmp_packet(final_header['data'])
                    if icmp and icmp['type'] == 8:  # Echo Request
                        # Build Echo Reply
                        reply_packet = build_icmp_echo_reply(
                            dest_ip, src_ip,
                            icmp['id'], icmp['sequence'],
                            icmp['data']
                        )
                        # Send reply back through network
                        dest_system.packet_queue.send_packet(reply_packet, capture=capture)

                return True

        except Exception as e:
            # Packet parsing/routing failed
            import traceback
            traceback.print_exc()
            return False

        return False

    def _capture_packet(self, packet: Packet, direction: str):
        """
        Capture packet for analysis tools like tcpdump

        Args:
            packet: The packet to capture
            direction: 'send', 'recv', or 'forward'
        """
        # Store captured packets (limit to last 1000)
        if not hasattr(self, 'captured_packets'):
            self.captured_packets = []

        self.captured_packets.append({
            'packet': packet,
            'direction': direction,
            'timestamp': packet.timestamp,
            'interface': packet.interface
        })

        # Keep only last 1000 packets
        if len(self.captured_packets) > 1000:
            self.captured_packets.pop(0)

    def _send_icmp_time_exceeded(self, dest_ip: str, original_packet: bytes):
        """Send ICMP Time Exceeded message"""
        # TODO: Implement ICMP error messages
        pass

    def _send_icmp_time_exceeded_from(self, router_ip: str, dest_ip: str, original_packet: bytes):
        """Send ICMP Time Exceeded from a specific router"""
        # TODO: Implement for traceroute support
        pass

    def _send_icmp_unreachable(self, dest_ip: str, original_packet: bytes):
        """Send ICMP Destination Unreachable message"""
        # TODO: Implement ICMP error messages
        pass

    def _check_packet_firewall(self, packet_bytes: bytes, dest_system: 'UnixSystem', src_ip: str) -> bool:
        """
        Check if packet is allowed by destination system's firewall

        Args:
            packet_bytes: Raw packet bytes
            dest_system: Destination system
            src_ip: Source IP address

        Returns:
            True if packet is allowed, False if blocked
        """
        if not hasattr(dest_system, 'firewall_rules'):
            return True  # No firewall, allow all

        # Parse packet to determine protocol and port
        try:
            ip_header = parse_ip_packet(packet_bytes)
            protocol = ip_header['protocol']
            protocol_name = {1: 'icmp', 6: 'tcp', 17: 'udp'}.get(protocol, 'unknown')

            # Extract port for TCP/UDP
            dst_port = None
            if protocol == 6:  # TCP
                tcp = parse_tcp_packet(ip_header['data'])
                dst_port = tcp['dst_port']
            elif protocol == 17:  # UDP
                udp = parse_udp_packet(ip_header['data'])
                dst_port = udp['dst_port']

            # Check firewall rules
            for rule in dest_system.firewall_rules:
                action = rule.get('action', 'ACCEPT')
                rule_protocol = rule.get('protocol', 'all')
                rule_port = rule.get('port')
                rule_source = rule.get('source', 'any')
                rule_chain = rule.get('chain', 'INPUT')

                # Only check INPUT chain for incoming packets
                if rule_chain != 'INPUT':
                    continue

                # Check if protocol matches
                if rule_protocol != 'all' and rule_protocol != protocol_name:
                    continue

                # Check if port matches (if specified)
                if rule_port is not None and dst_port != rule_port:
                    continue

                # Check if source IP matches
                if rule_source != 'any':
                    # Support CIDR notation (e.g., "192.168.1.0/24")
                    if '/' in rule_source:
                        # Simple subnet matching
                        subnet_base = rule_source.split('/')[0]
                        prefix_len = rule_source.split('/')[1]

                        # /24 = first 3 octets, /16 = first 2, /8 = first 1
                        if prefix_len == '24':
                            if not src_ip.startswith('.'.join(subnet_base.split('.')[:3])):
                                continue
                        elif prefix_len == '16':
                            if not src_ip.startswith('.'.join(subnet_base.split('.')[:2])):
                                continue
                        elif prefix_len == '8':
                            if not src_ip.startswith(subnet_base.split('.')[0]):
                                continue
                    else:
                        # Exact IP match
                        if src_ip != rule_source:
                            continue

                # Rule matches - apply action
                if action == 'DROP' or action == 'REJECT':
                    return False  # Block packet
                elif action == 'ACCEPT':
                    return True  # Allow packet

            # No matching rule - default policy is ACCEPT
            return True

        except Exception as e:
            # Error parsing packet - allow by default
            return True

    def receive_packet(self, timeout: float = 0.0) -> Optional[bytes]:
        """
        Read next packet from inbound queue

        Args:
            timeout: How long to wait for a packet (0 = non-blocking)

        Returns:
            Packet bytes or None if no packet available
        """
        if self.inbound:
            packet = self.inbound.pop(0)
            return bytes(packet)
        return None

    def has_packets(self) -> bool:
        """Check if there are packets waiting"""
        return len(self.inbound) > 0

    def clear(self):
        """Clear all queued packets"""
        self.inbound.clear()
        self.outbound.clear()


# Packet encoding/decoding utilities

def parse_ip_packet(packet_bytes: bytes) -> dict:
    """
    Parse IP packet header

    Simplified IP packet format:
    - Version (4 bits): 4
    - Header length (4 bits): 5 (20 bytes)
    - Total length (16 bits)
    - Protocol (8 bits): 1=ICMP, 6=TCP, 17=UDP
    - TTL (8 bits): Time to live
    - Source IP (32 bits)
    - Destination IP (32 bits)
    - Data (rest)

    Returns:
        dict with 'version', 'protocol', 'ttl', 'src', 'dst', 'data'
    """
    if len(packet_bytes) < 20:
        raise ValueError("Packet too short")

    # Parse header (simplified - first 20 bytes)
    version_ihl = packet_bytes[0]
    version = version_ihl >> 4
    ihl = (version_ihl & 0x0F) * 4  # Header length in bytes

    ttl = packet_bytes[8]
    protocol = packet_bytes[9]

    # Extract IPs (bytes 12-15 = source, 16-19 = dest)
    src_ip = '.'.join(str(b) for b in packet_bytes[12:16])
    dst_ip = '.'.join(str(b) for b in packet_bytes[16:20])

    # Data starts after header
    data = packet_bytes[ihl:]

    return {
        'version': version,
        'protocol': protocol,
        'ttl': ttl,
        'src': src_ip,
        'dst': dst_ip,
        'data': data
    }


def _decrement_ttl(packet_bytes: bytes) -> bytes:
    """
    Decrement TTL in IP packet by 1

    Args:
        packet_bytes: Original packet

    Returns:
        New packet with decremented TTL
    """
    packet = bytearray(packet_bytes)
    if len(packet) >= 9:
        packet[8] = max(0, packet[8] - 1)  # Decrement TTL
        # Recalculate checksum (simplified - just set to 0)
        packet[10:12] = b'\x00\x00'
    return bytes(packet)


def build_ip_packet(src_ip: str, dst_ip: str, protocol: int, data: bytes) -> bytes:
    """
    Build IP packet

    Args:
        src_ip: Source IP address (e.g., "192.168.1.1")
        dst_ip: Destination IP address
        protocol: IP protocol (1=ICMP, 6=TCP, 17=UDP)
        data: Packet payload

    Returns:
        Raw packet bytes
    """
    # IP header (simplified, 20 bytes)
    header = bytearray(20)

    # Version (4) + IHL (5 = 20 bytes)
    header[0] = (4 << 4) | 5

    # Total length
    total_len = 20 + len(data)
    header[2:4] = struct.pack('!H', total_len)

    # TTL (64)
    header[8] = 64

    # Protocol
    header[9] = protocol

    # Source IP
    src_parts = [int(x) for x in src_ip.split('.')]
    header[12:16] = bytes(src_parts)

    # Destination IP
    dst_parts = [int(x) for x in dst_ip.split('.')]
    header[16:20] = bytes(dst_parts)

    # Checksum (simplified - just set to 0)
    header[10:12] = b'\x00\x00'

    return bytes(header) + data


def parse_icmp_packet(icmp_bytes: bytes) -> dict:
    """
    Parse ICMP packet

    ICMP format:
    - Type (8 bits): 8=Echo Request, 0=Echo Reply
    - Code (8 bits): Usually 0
    - Checksum (16 bits)
    - ID (16 bits)
    - Sequence (16 bits)
    - Data (rest)

    Returns:
        dict with 'type', 'code', 'id', 'sequence', 'data'
    """
    if len(icmp_bytes) < 8:
        raise ValueError("ICMP packet too short")

    icmp_type = icmp_bytes[0]
    code = icmp_bytes[1]
    checksum = struct.unpack('!H', icmp_bytes[2:4])[0]
    icmp_id = struct.unpack('!H', icmp_bytes[4:6])[0]
    sequence = struct.unpack('!H', icmp_bytes[6:8])[0]
    data = icmp_bytes[8:]

    return {
        'type': icmp_type,
        'code': code,
        'checksum': checksum,
        'id': icmp_id,
        'sequence': sequence,
        'data': data
    }


def build_icmp_packet(icmp_type: int, code: int, icmp_id: int, sequence: int, data: bytes) -> bytes:
    """
    Build ICMP packet

    Args:
        icmp_type: ICMP type (8=Echo Request, 0=Echo Reply)
        code: ICMP code (usually 0)
        icmp_id: Identifier (usually process ID)
        sequence: Sequence number
        data: Payload data

    Returns:
        Raw ICMP packet bytes
    """
    # Build packet without checksum first
    packet = bytearray(8 + len(data))
    packet[0] = icmp_type
    packet[1] = code
    packet[2:4] = b'\x00\x00'  # Checksum placeholder
    packet[4:6] = struct.pack('!H', icmp_id)
    packet[6:8] = struct.pack('!H', sequence)
    packet[8:] = data

    # Calculate checksum
    checksum = _calculate_checksum(packet)
    packet[2:4] = struct.pack('!H', checksum)

    return bytes(packet)


def _calculate_checksum(data: bytes) -> int:
    """Calculate Internet checksum"""
    if len(data) % 2 == 1:
        data += b'\x00'

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        checksum += word

    # Add carry bits
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = ~checksum & 0xffff

    return checksum


def build_icmp_echo_request(src_ip: str, dst_ip: str, icmp_id: int, sequence: int, data: bytes = b'poodillion') -> bytes:
    """
    Build complete ICMP Echo Request packet (IP + ICMP)

    Args:
        src_ip: Source IP
        dst_ip: Destination IP
        icmp_id: ICMP identifier (usually PID)
        sequence: Sequence number
        data: Ping payload data

    Returns:
        Complete IP packet ready to send
    """
    icmp = build_icmp_packet(8, 0, icmp_id, sequence, data)  # Type 8 = Echo Request
    return build_ip_packet(src_ip, dst_ip, 1, icmp)  # Protocol 1 = ICMP


def build_icmp_echo_reply(src_ip: str, dst_ip: str, icmp_id: int, sequence: int, data: bytes) -> bytes:
    """
    Build ICMP Echo Reply packet

    Args:
        src_ip: Source IP (the replying host)
        dst_ip: Destination IP (original sender)
        icmp_id: ICMP identifier from request
        sequence: Sequence number from request
        data: Data from request

    Returns:
        Complete IP packet ready to send
    """
    icmp = build_icmp_packet(0, 0, icmp_id, sequence, data)  # Type 0 = Echo Reply
    return build_ip_packet(src_ip, dst_ip, 1, icmp)  # Protocol 1 = ICMP


# TCP Packet Support

def parse_tcp_packet(tcp_bytes: bytes) -> dict:
    """
    Parse TCP packet header

    TCP format:
    - Source port (16 bits)
    - Dest port (16 bits)
    - Sequence number (32 bits)
    - Acknowledgment number (32 bits)
    - Data offset (4 bits) + Reserved (4 bits)
    - Flags (8 bits): URG, ACK, PSH, RST, SYN, FIN
    - Window size (16 bits)
    - Checksum (16 bits)
    - Urgent pointer (16 bits)
    - Data (rest)

    Returns:
        dict with TCP header fields
    """
    if len(tcp_bytes) < 20:
        raise ValueError("TCP packet too short")

    src_port = struct.unpack('!H', tcp_bytes[0:2])[0]
    dst_port = struct.unpack('!H', tcp_bytes[2:4])[0]
    seq = struct.unpack('!I', tcp_bytes[4:8])[0]
    ack = struct.unpack('!I', tcp_bytes[8:12])[0]

    data_offset = (tcp_bytes[12] >> 4) * 4  # Header length in bytes
    flags = tcp_bytes[13]

    # Parse flag bits
    flag_fin = bool(flags & 0x01)
    flag_syn = bool(flags & 0x02)
    flag_rst = bool(flags & 0x04)
    flag_psh = bool(flags & 0x08)
    flag_ack = bool(flags & 0x10)
    flag_urg = bool(flags & 0x20)

    window = struct.unpack('!H', tcp_bytes[14:16])[0]
    checksum = struct.unpack('!H', tcp_bytes[16:18])[0]

    data = tcp_bytes[data_offset:]

    return {
        'src_port': src_port,
        'dst_port': dst_port,
        'seq': seq,
        'ack': ack,
        'flags': {
            'FIN': flag_fin,
            'SYN': flag_syn,
            'RST': flag_rst,
            'PSH': flag_psh,
            'ACK': flag_ack,
            'URG': flag_urg,
        },
        'window': window,
        'checksum': checksum,
        'data': data
    }


def build_tcp_packet(src_port: int, dst_port: int, seq: int, ack: int,
                     flags: Dict[str, bool], data: bytes = b'', window: int = 65535) -> bytes:
    """
    Build TCP packet

    Args:
        src_port: Source port
        dst_port: Destination port
        seq: Sequence number
        ack: Acknowledgment number
        flags: Dict with 'SYN', 'ACK', 'FIN', 'RST', 'PSH', 'URG'
        data: Payload data
        window: Window size

    Returns:
        Raw TCP packet bytes
    """
    # Build header (20 bytes minimum)
    header = bytearray(20)

    struct.pack_into('!H', header, 0, src_port)
    struct.pack_into('!H', header, 2, dst_port)
    struct.pack_into('!I', header, 4, seq)
    struct.pack_into('!I', header, 8, ack)

    # Data offset (5 = 20 bytes) + reserved
    header[12] = (5 << 4)

    # Flags
    flag_byte = 0
    if flags.get('FIN'): flag_byte |= 0x01
    if flags.get('SYN'): flag_byte |= 0x02
    if flags.get('RST'): flag_byte |= 0x04
    if flags.get('PSH'): flag_byte |= 0x08
    if flags.get('ACK'): flag_byte |= 0x10
    if flags.get('URG'): flag_byte |= 0x20
    header[13] = flag_byte

    struct.pack_into('!H', header, 14, window)
    # Checksum (simplified - set to 0)
    struct.pack_into('!H', header, 16, 0)
    # Urgent pointer
    struct.pack_into('!H', header, 18, 0)

    return bytes(header) + data


def build_tcp_syn(src_ip: str, dst_ip: str, src_port: int, dst_port: int, seq: int = 0) -> bytes:
    """Build TCP SYN packet (connection initiation)"""
    tcp = build_tcp_packet(src_port, dst_port, seq, 0, {'SYN': True})
    return build_ip_packet(src_ip, dst_ip, 6, tcp)  # Protocol 6 = TCP


def build_tcp_syn_ack(src_ip: str, dst_ip: str, src_port: int, dst_port: int, seq: int, ack: int) -> bytes:
    """Build TCP SYN-ACK packet (connection acknowledgment)"""
    tcp = build_tcp_packet(src_port, dst_port, seq, ack, {'SYN': True, 'ACK': True})
    return build_ip_packet(src_ip, dst_ip, 6, tcp)


def build_tcp_ack(src_ip: str, dst_ip: str, src_port: int, dst_port: int, seq: int, ack: int) -> bytes:
    """Build TCP ACK packet"""
    tcp = build_tcp_packet(src_port, dst_port, seq, ack, {'ACK': True})
    return build_ip_packet(src_ip, dst_ip, 6, tcp)


def build_tcp_data(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                   seq: int, ack: int, data: bytes) -> bytes:
    """Build TCP data packet"""
    tcp = build_tcp_packet(src_port, dst_port, seq, ack, {'PSH': True, 'ACK': True}, data)
    return build_ip_packet(src_ip, dst_ip, 6, tcp)


def build_tcp_fin(src_ip: str, dst_ip: str, src_port: int, dst_port: int, seq: int, ack: int) -> bytes:
    """Build TCP FIN packet (connection termination)"""
    tcp = build_tcp_packet(src_port, dst_port, seq, ack, {'FIN': True, 'ACK': True})
    return build_ip_packet(src_ip, dst_ip, 6, tcp)


# UDP Packet Support

def parse_udp_packet(udp_bytes: bytes) -> dict:
    """
    Parse UDP packet header

    UDP format:
    - Source port (16 bits)
    - Dest port (16 bits)
    - Length (16 bits)
    - Checksum (16 bits)
    - Data (rest)

    Returns:
        dict with UDP header fields
    """
    if len(udp_bytes) < 8:
        raise ValueError("UDP packet too short")

    src_port = struct.unpack('!H', udp_bytes[0:2])[0]
    dst_port = struct.unpack('!H', udp_bytes[2:4])[0]
    length = struct.unpack('!H', udp_bytes[4:6])[0]
    checksum = struct.unpack('!H', udp_bytes[6:8])[0]
    data = udp_bytes[8:]

    return {
        'src_port': src_port,
        'dst_port': dst_port,
        'length': length,
        'checksum': checksum,
        'data': data
    }


def build_udp_packet(src_port: int, dst_port: int, data: bytes) -> bytes:
    """
    Build UDP packet

    Args:
        src_port: Source port
        dst_port: Destination port
        data: Payload data

    Returns:
        Raw UDP packet bytes
    """
    length = 8 + len(data)

    header = bytearray(8)
    struct.pack_into('!H', header, 0, src_port)
    struct.pack_into('!H', header, 2, dst_port)
    struct.pack_into('!H', header, 4, length)
    # Checksum (simplified - set to 0)
    struct.pack_into('!H', header, 6, 0)

    return bytes(header) + data


def build_udp_datagram(src_ip: str, dst_ip: str, src_port: int, dst_port: int, data: bytes) -> bytes:
    """Build complete UDP datagram (IP + UDP)"""
    udp = build_udp_packet(src_port, dst_port, data)
    return build_ip_packet(src_ip, dst_ip, 17, udp)  # Protocol 17 = UDP
