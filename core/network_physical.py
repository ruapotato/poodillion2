"""
Network Physical Layer - The "Wire"

This module provides minimal packet transport between systems.
It has NO intelligence - just moves raw bytes between interfaces.

All network logic (routing, DNS, DHCP, etc.) is in PooScript.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class NetworkInterface:
    """
    Physical network interface (like eth0, eth1)
    Just buffers for RX/TX packets
    """
    name: str  # eth0, eth1, lo
    mac: str  # MAC address (e.g., "08:00:27:12:34:56")
    rx_buffer: List[bytes] = field(default_factory=list)  # Received packets
    tx_buffer: List[bytes] = field(default_factory=list)  # Packets to send
    segment: Optional['NetworkSegment'] = None  # Which segment we're on
    up: bool = True  # Interface up/down

    def send_raw(self, packet: bytes):
        """Send raw packet onto the wire (broadcast to segment)"""
        if not self.up or not self.segment:
            return False

        # Broadcast to all systems on this segment
        self.segment.broadcast_packet(packet, sender_mac=self.mac)
        return True

    def recv_raw(self) -> Optional[bytes]:
        """Receive raw packet from wire (non-blocking)"""
        if self.rx_buffer:
            return self.rx_buffer.pop(0)
        return None

    def has_packets(self) -> bool:
        """Check if there are packets waiting"""
        return len(self.rx_buffer) > 0


class NetworkSegment:
    """
    A network segment (like a hub/switch)
    Broadcasts packets to all connected interfaces
    """

    def __init__(self, segment_id: str):
        self.segment_id = segment_id
        self.interfaces: List[NetworkInterface] = []

    def attach_interface(self, interface: NetworkInterface):
        """Attach an interface to this segment"""
        if interface not in self.interfaces:
            self.interfaces.append(interface)
            interface.segment = self

    def detach_interface(self, interface: NetworkInterface):
        """Detach an interface from this segment"""
        if interface in self.interfaces:
            self.interfaces.remove(interface)
            interface.segment = None

    def broadcast_packet(self, packet: bytes, sender_mac: str):
        """
        Broadcast packet to all interfaces on this segment
        (except the sender)
        """
        for iface in self.interfaces:
            if iface.mac != sender_mac and iface.up:
                # Put packet in interface's RX buffer
                iface.rx_buffer.append(packet)


class PhysicalNetwork:
    """
    Physical network topology
    Manages segments and how systems connect
    """

    def __init__(self):
        self.segments: Dict[str, NetworkSegment] = {}
        self.systems: Dict[str, 'UnixSystem'] = {}  # IP -> system mapping for convenience

    def create_segment(self, segment_id: str) -> NetworkSegment:
        """Create a network segment"""
        if segment_id not in self.segments:
            self.segments[segment_id] = NetworkSegment(segment_id)
        return self.segments[segment_id]

    def connect_to_segment(self, interface: NetworkInterface, segment_id: str):
        """Connect an interface to a segment"""
        segment = self.create_segment(segment_id)
        segment.attach_interface(interface)

    def register_system(self, system: 'UnixSystem', ip: str):
        """Register a system (for convenience lookups)"""
        self.systems[ip] = system

    def get_system_by_ip(self, ip: str) -> Optional['UnixSystem']:
        """Get system by IP address"""
        return self.systems.get(ip)

    def disconnect_interface(self, interface: NetworkInterface):
        """Disconnect interface from its segment"""
        if interface.segment:
            interface.segment.detach_interface(interface)
