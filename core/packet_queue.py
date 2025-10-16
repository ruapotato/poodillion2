"""
Packet queue for device-based networking
Handles packet queueing, routing, and delivery
"""

from typing import Optional, List
import struct
import time


class Packet:
    """Network packet with headers"""
    def __init__(self, raw_bytes: bytes):
        self.raw = raw_bytes
        self.timestamp = time.time()

    def __bytes__(self):
        return self.raw


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

    def send_packet(self, packet_bytes: bytes) -> bool:
        """
        Send a packet through the network
        Parses the packet, routes it, and delivers to destination

        Args:
            packet_bytes: Raw packet bytes (IP packet)

        Returns:
            True if packet was sent successfully
        """
        if not self.network:
            return False

        # Parse IP header to get destination
        try:
            ip_header = parse_ip_packet(packet_bytes)
            dest_ip = ip_header['dst']
            src_ip = ip_header['src']

            # Find route to destination
            path = self.network._find_route_path(src_ip, dest_ip)
            if not path:
                return False

            # Get destination system
            dest_system = self.network.systems.get(dest_ip)
            if not dest_system:
                return False

            # Deliver packet to destination's inbound queue
            if hasattr(dest_system, 'packet_queue'):
                packet = Packet(packet_bytes)
                dest_system.packet_queue.inbound.append(packet)

                # Auto-respond to ICMP Echo Request (ping)
                if ip_header['protocol'] == 1:  # ICMP
                    icmp = parse_icmp_packet(ip_header['data'])
                    if icmp and icmp['type'] == 8:  # Echo Request
                        # Build Echo Reply
                        reply_packet = build_icmp_echo_reply(
                            dest_ip, src_ip,
                            icmp['id'], icmp['sequence'],
                            icmp['data']
                        )
                        # Send reply back to source
                        if hasattr(self.system, 'packet_queue'):
                            reply_pkt = Packet(reply_packet)
                            self.system.packet_queue.inbound.append(reply_pkt)

                return True

        except Exception as e:
            # Packet parsing failed
            return False

        return False

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
    - Source IP (32 bits)
    - Destination IP (32 bits)
    - Data (rest)

    Returns:
        dict with 'version', 'protocol', 'src', 'dst', 'data'
    """
    if len(packet_bytes) < 20:
        raise ValueError("Packet too short")

    # Parse header (simplified - first 20 bytes)
    version_ihl = packet_bytes[0]
    version = version_ihl >> 4
    ihl = (version_ihl & 0x0F) * 4  # Header length in bytes

    protocol = packet_bytes[9]

    # Extract IPs (bytes 12-15 = source, 16-19 = dest)
    src_ip = '.'.join(str(b) for b in packet_bytes[12:16])
    dst_ip = '.'.join(str(b) for b in packet_bytes[16:20])

    # Data starts after header
    data = packet_bytes[ihl:]

    return {
        'version': version,
        'protocol': protocol,
        'src': src_ip,
        'dst': dst_ip,
        'data': data
    }


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
