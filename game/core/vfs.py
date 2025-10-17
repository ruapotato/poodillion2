"""
Virtual Filesystem - Unix-like filesystem implementation
Supports inodes, permissions, symbolic links, devices
"""

import time
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import IntEnum


class FileType(IntEnum):
    """Unix file types"""
    REGULAR = 0o100000  # Regular file
    DIRECTORY = 0o040000  # Directory
    SYMLINK = 0o120000  # Symbolic link
    CHARDEV = 0o020000  # Character device
    BLOCKDEV = 0o060000  # Block device
    FIFO = 0o010000  # Named pipe
    SOCKET = 0o140000  # Socket


@dataclass
class Inode:
    """Unix-style inode structure"""
    ino: int  # Inode number
    mode: int  # File type + permissions (e.g., 0o100644)
    uid: int  # Owner user ID
    gid: int  # Owner group ID
    size: int  # File size in bytes
    atime: float  # Access time
    mtime: float  # Modification time
    ctime: float  # Change time (metadata)
    nlink: int = 1  # Number of hard links
    content: Union[bytes, Dict[str, int], str] = b''  # File content, dir entries, or link target

    def is_dir(self) -> bool:
        return (self.mode & 0o170000) == FileType.DIRECTORY

    def is_file(self) -> bool:
        return (self.mode & 0o170000) == FileType.REGULAR

    def is_symlink(self) -> bool:
        return (self.mode & 0o170000) == FileType.SYMLINK

    def is_device(self) -> bool:
        ft = self.mode & 0o170000
        return ft == FileType.CHARDEV or ft == FileType.BLOCKDEV

    def get_type_char(self) -> str:
        """Return ls-style type character"""
        ft = self.mode & 0o170000
        return {
            FileType.REGULAR: '-',
            FileType.DIRECTORY: 'd',
            FileType.SYMLINK: 'l',
            FileType.CHARDEV: 'c',
            FileType.BLOCKDEV: 'b',
            FileType.FIFO: 'p',
            FileType.SOCKET: 's',
        }.get(ft, '?')

    def permission_string(self) -> str:
        """Return ls-style permission string (e.g., rwxr-xr-x, rwsr-xr-x for SUID)"""
        perms = self.mode & 0o777
        special = self.mode & 0o7000
        chars = []

        # Owner permissions
        p = (perms >> 6) & 7
        chars.append('r' if p & 4 else '-')
        chars.append('w' if p & 2 else '-')
        # SUID: s if executable, S if not executable
        if special & 0o4000:  # SUID bit
            chars.append('s' if p & 1 else 'S')
        else:
            chars.append('x' if p & 1 else '-')

        # Group permissions
        p = (perms >> 3) & 7
        chars.append('r' if p & 4 else '-')
        chars.append('w' if p & 2 else '-')
        # SGID: s if executable, S if not executable
        if special & 0o2000:  # SGID bit
            chars.append('s' if p & 1 else 'S')
        else:
            chars.append('x' if p & 1 else '-')

        # Other permissions
        p = perms & 7
        chars.append('r' if p & 4 else '-')
        chars.append('w' if p & 2 else '-')
        # Sticky bit: t if executable, T if not executable
        if special & 0o1000:  # Sticky bit
            chars.append('t' if p & 1 else 'T')
        else:
            chars.append('x' if p & 1 else '-')

        return ''.join(chars)


class VFS:
    """Virtual Filesystem"""

    def __init__(self, system: Optional['UnixSystem'] = None):
        self.inodes: Dict[int, Inode] = {}
        self.next_ino = 2  # Start at 2 (1 is reserved for root in real systems)

        # Device handlers: map device name to (read_handler, write_handler)
        self.device_handlers: Dict[str, tuple] = {}

        # I/O callbacks for device files that need to interact with the outside world
        self.input_callback = None  # For reading from stdin/tty
        self.output_callback = None  # For writing to stdout/tty
        self.error_callback = None  # For writing to stderr

        # Reference to system for network device handlers
        self.system = system

        # Create root directory
        now = time.time()
        root = Inode(
            ino=1,
            mode=FileType.DIRECTORY | 0o755,
            uid=0,
            gid=0,
            size=4096,
            atime=now,
            mtime=now,
            ctime=now,
            content={'.': 1, '..': 1}  # Directory entries map name -> inode
        )
        self.inodes[1] = root

        # Register built-in device handlers
        self._register_device_handlers()

    def _register_device_handlers(self):
        """Register handlers for special device files"""
        import random

        # /dev/null - discards all writes, returns empty on reads
        self.device_handlers['null'] = (
            lambda size: b'',  # read returns nothing
            lambda data: len(data)  # write discards everything, returns bytes written
        )

        # /dev/zero - returns infinite zeros
        self.device_handlers['zero'] = (
            lambda size: b'\x00' * size,
            lambda data: len(data)
        )

        # /dev/random - returns random bytes
        self.device_handlers['random'] = (
            lambda size: bytes(random.getrandbits(8) for _ in range(size)),
            lambda data: len(data)
        )

        # /dev/urandom - returns random bytes (same as random in our impl)
        self.device_handlers['urandom'] = (
            lambda size: bytes(random.getrandbits(8) for _ in range(size)),
            lambda data: len(data)
        )

        # /dev/tty - terminal I/O (uses callbacks)
        def tty_read(size):
            if self.input_callback:
                try:
                    line = self.input_callback("")
                    return (line + '\n').encode()[:size]
                except:
                    return b''
            return b''

        def tty_write(data):
            if self.output_callback:
                self.output_callback(data.decode('utf-8', errors='replace'))
            return len(data)

        self.device_handlers['tty'] = (tty_read, tty_write)
        self.device_handlers['tty0'] = (tty_read, tty_write)
        self.device_handlers['tty1'] = (tty_read, tty_write)
        self.device_handlers['console'] = (tty_read, tty_write)

        # /dev/stdin, /dev/stdout, /dev/stderr
        self.device_handlers['stdin'] = (tty_read, lambda data: 0)  # stdin is read-only

        def stdout_write(data):
            if self.output_callback:
                self.output_callback(data.decode('utf-8', errors='replace'))
            return len(data)

        def stderr_write(data):
            if self.error_callback:
                self.error_callback(data.decode('utf-8', errors='replace'))
            return len(data)

        self.device_handlers['stdout'] = (lambda size: b'', stdout_write)
        self.device_handlers['stderr'] = (lambda size: b'', stderr_write)

        # /dev/full - always full (write fails)
        def full_write(data):
            raise IOError("No space left on device")

        self.device_handlers['full'] = (lambda size: b'\x00' * size, full_write)

        # /dev/kmsg - kernel message buffer (dummy implementation)
        self.kernel_messages = []

        def kmsg_read(size):
            if self.kernel_messages:
                msg = self.kernel_messages.pop(0)
                return msg.encode()[:size]
            return b''

        def kmsg_write(data):
            self.kernel_messages.append(data.decode('utf-8', errors='replace'))
            return len(data)

        self.device_handlers['kmsg'] = (kmsg_read, kmsg_write)

        # Network devices (lazy evaluation - requires system reference)
        def packet_read(size):
            """Read packet from network queue"""
            if self.system and hasattr(self.system, 'packet_queue'):
                packet_bytes = self.system.packet_queue.receive_packet()
                if packet_bytes:
                    return packet_bytes[:size] if size > 0 else packet_bytes
            return b''

        def packet_write(data):
            """Send packet through network"""
            if self.system and hasattr(self.system, 'packet_queue'):
                self.system.packet_queue.send_packet(data)
                return len(data)
            return 0

        self.device_handlers['packet'] = (packet_read, packet_write)

        # /dev/net/eth0_raw, eth1_raw, etc - Raw interface access
        # These are registered dynamically when interfaces are created
        # Handler template function:
        def make_interface_handlers(iface_name: str):
            """Create read/write handlers for a specific interface"""
            def iface_read(size):
                if self.system and hasattr(self.system, 'net_interfaces'):
                    iface = self.system.net_interfaces.get(iface_name)
                    if iface:
                        packet = iface.recv_raw()
                        if packet:
                            return packet[:size] if size > 0 else packet
                return b''

            def iface_write(data):
                if self.system and hasattr(self.system, 'net_interfaces'):
                    iface = self.system.net_interfaces.get(iface_name)
                    if iface:
                        iface.send_raw(data)
                        return len(data)
                return 0

            return (iface_read, iface_write)

        # Store the factory function for later use
        self._make_interface_handlers = make_interface_handlers

        # /dev/net/local - Packets destined for local system (from PooScript network daemon)
        def local_read(size):
            """Read packet destined for localhost"""
            if self.system and hasattr(self.system, 'local_packet_queue'):
                if self.system.local_packet_queue:
                    packet = self.system.local_packet_queue.pop(0)
                    return packet[:size] if size > 0 else packet
            return b''

        def local_write(data):
            """Send packet to local stack"""
            if self.system and hasattr(self.system, 'local_packet_queue'):
                self.system.local_packet_queue.append(data)
                return len(data)
            return 0

        self.device_handlers['local'] = (local_read, local_write)

        # /dev/net/arp - ARP table (placeholder for now)
        def arp_read(size):
            """Read ARP table"""
            # Will be implemented when we add /proc/net generators
            return b''

        def arp_write(data):
            """Manipulate ARP table"""
            # TODO: Parse ARP entry and update table
            return len(data)

        self.device_handlers['arp'] = (arp_read, arp_write)

        # /dev/net/route - Routing table (placeholder for now)
        def route_read(size):
            """Read routing table"""
            # Will be implemented when we add /proc/net generators
            return b''

        def route_write(data):
            """Add/remove routes"""
            # TODO: Parse route entry and update routing table
            return len(data)

        self.device_handlers['route'] = (route_read, route_write)

        # /dev/net/tun - TUN/TAP device (placeholder)
        def tun_read(size):
            return b''

        def tun_write(data):
            return len(data)

        self.device_handlers['tun'] = (tun_read, tun_write)

        # /proc/net/ generators - dynamic network state
        def proc_net_dev_read(size):
            """Generate /proc/net/dev - network interface statistics"""
            if not self.system:
                return b''

            lines = []
            lines.append("Inter-|   Receive                                                |  Transmit")
            lines.append(" face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed")

            for iface, ip in self.system.interfaces.items():
                # Dummy statistics for now
                rx_bytes, rx_packets = 123456, 234
                tx_bytes, tx_packets = 234567, 345
                lines.append(f"  {iface:5s}:{rx_bytes:8d} {rx_packets:7d}    0    0    0     0          0         0 {tx_bytes:8d} {tx_packets:7d}    0    0    0     0       0          0")

            return '\n'.join(lines).encode() + b'\n'

        def proc_net_arp_read(size):
            """Generate /proc/net/arp - ARP cache"""
            if not self.system or not self.system.network:
                return b''

            lines = []
            lines.append("IP address       HW type     Flags       HW address            Mask     Device")

            # Generate ARP entries for systems we can reach
            for iface, ip in self.system.interfaces.items():
                if iface == 'lo':
                    continue

                # Find neighbors on this interface's network
                subnet_prefix = '.'.join(ip.split('.')[:3])

                if self.system.network:
                    for other_ip, other_system in self.system.network.systems.items():
                        if other_ip.startswith(subnet_prefix) and other_ip != ip:
                            # Generate MAC address (fake, but deterministic)
                            octets = [int(x) for x in other_ip.split('.')]
                            mac = f"08:00:27:{octets[1]:02x}:{octets[2]:02x}:{octets[3]:02x}"
                            lines.append(f"{other_ip:16s} 0x1         0x2         {mac:18s}     *        {iface}")

            return '\n'.join(lines).encode() + b'\n'

        def proc_net_route_read(size):
            """Generate /proc/net/route - kernel routing table"""
            if not self.system:
                return b''

            lines = []
            lines.append("Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT")

            # Add routes for each interface
            for iface, ip in self.system.interfaces.items():
                if iface == 'lo':
                    # Loopback route
                    lines.append(f"{iface}\t00000000\t00000000\t0001\t0\t0\t0\t00000000\t0\t0\t0")
                else:
                    # Network route (network/24 via this interface)
                    octets = [int(x) for x in ip.split('.')]
                    dest_hex = f"{octets[3]:02X}{octets[2]:02X}{octets[1]:02X}{octets[0]:02X}"
                    mask_hex = "00FFFFFF"  # 255.255.255.0
                    lines.append(f"{iface}\t{dest_hex}\t00000000\t0001\t0\t0\t0\t{mask_hex}\t0\t0\t0")

                    # Default gateway (if set)
                    if self.system.default_gateway:
                        gw_octets = [int(x) for x in self.system.default_gateway.split('.')]
                        gw_hex = f"{gw_octets[3]:02X}{gw_octets[2]:02X}{gw_octets[1]:02X}{gw_octets[0]:02X}"
                        lines.append(f"{iface}\t00000000\t{gw_hex}\t0003\t0\t0\t0\t00000000\t0\t0\t0")

            return '\n'.join(lines).encode() + b'\n'

        def proc_net_tcp_read(size):
            """Generate /proc/net/tcp - active TCP connections"""
            lines = []
            lines.append("  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode")
            # TODO: Track actual connections
            return '\n'.join(lines).encode() + b'\n'

        def proc_net_udp_read(size):
            """Generate /proc/net/udp - active UDP connections"""
            lines = []
            lines.append("  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode")
            # TODO: Track actual connections
            return '\n'.join(lines).encode() + b'\n'

        # Register /proc/net handlers (read-only)
        self.device_handlers['proc_net_dev'] = (proc_net_dev_read, lambda data: 0)
        self.device_handlers['proc_net_arp'] = (proc_net_arp_read, lambda data: 0)
        self.device_handlers['proc_net_route'] = (proc_net_route_read, lambda data: 0)
        self.device_handlers['proc_net_tcp'] = (proc_net_tcp_read, lambda data: 0)
        self.device_handlers['proc_net_udp'] = (proc_net_udp_read, lambda data: 0)

    def _allocate_inode(self) -> int:
        """Allocate a new inode number"""
        ino = self.next_ino
        self.next_ino += 1
        return ino

    def _resolve_path(self, path: str, current_dir_ino: int = 1, follow_symlinks: bool = True) -> Optional[int]:
        """
        Resolve a path to an inode number
        Returns None if path doesn't exist
        """
        if path.startswith('/'):
            current = 1  # Root
            path = path[1:]
        else:
            current = current_dir_ino

        if not path or path == '.':
            return current

        parts = [p for p in path.split('/') if p and p != '.']

        for i, part in enumerate(parts):
            inode = self.inodes.get(current)
            if not inode:
                return None

            # Follow symlink if needed
            if inode.is_symlink() and follow_symlinks:
                target = inode.content
                if isinstance(target, str):
                    current = self._resolve_path(target, current_dir_ino, follow_symlinks=True)
                    if current is None:
                        return None
                    inode = self.inodes.get(current)
                    if not inode:
                        return None

            if not inode.is_dir():
                return None

            entries = inode.content
            if not isinstance(entries, dict):
                return None

            if part not in entries:
                return None

            current = entries[part]

        # Final symlink resolution
        if follow_symlinks:
            inode = self.inodes.get(current)
            if inode and inode.is_symlink():
                target = inode.content
                if isinstance(target, str):
                    return self._resolve_path(target, current_dir_ino, follow_symlinks=True)

        return current

    def inode_to_path(self, ino: int, visited=None) -> str:
        """
        Convert inode number to path (reverse resolution)
        Returns the path as a string, or '???' if not found
        """
        if ino == 1:
            return '/'

        if visited is None:
            visited = set()

        if ino in visited:
            return '???'

        visited.add(ino)

        # Search all directories for this inode
        for parent_ino, parent_inode in self.inodes.items():
            if not parent_inode.is_dir():
                continue

            entries = parent_inode.content
            if not isinstance(entries, dict):
                continue

            for name, child_ino in entries.items():
                if child_ino == ino and name not in ('.', '..'):
                    parent_path = self.inode_to_path(parent_ino, visited)
                    if parent_path == '/':
                        return f'/{name}'
                    return f'{parent_path}/{name}'

        return '???'

    def mkdir(self, path: str, mode: int, uid: int, gid: int, current_dir_ino: int = 1) -> bool:
        """Create a directory"""
        parent_path = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        name = path.rstrip('/').split('/')[-1]

        parent_ino = self._resolve_path(parent_path, current_dir_ino)
        if parent_ino is None:
            return False

        parent = self.inodes.get(parent_ino)
        if not parent or not parent.is_dir():
            return False

        entries = parent.content
        if not isinstance(entries, dict) or name in entries:
            return False

        # Create new directory
        now = time.time()
        new_ino = self._allocate_inode()
        new_dir = Inode(
            ino=new_ino,
            mode=FileType.DIRECTORY | mode,
            uid=uid,
            gid=gid,
            size=4096,
            atime=now,
            mtime=now,
            ctime=now,
            content={'.': new_ino, '..': parent_ino}
        )

        self.inodes[new_ino] = new_dir
        entries[name] = new_ino
        parent.mtime = now
        parent.ctime = now

        return True

    def create_file(self, path: str, mode: int, uid: int, gid: int,
                    content: bytes = b'', current_dir_ino: int = 1) -> Optional[int]:
        """Create a regular file, returns inode number"""
        parent_path = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        name = path.rstrip('/').split('/')[-1]

        parent_ino = self._resolve_path(parent_path, current_dir_ino)
        if parent_ino is None:
            return None

        parent = self.inodes.get(parent_ino)
        if not parent or not parent.is_dir():
            return None

        entries = parent.content
        if not isinstance(entries, dict):
            return None

        # If file exists, truncate it
        if name in entries:
            existing_ino = entries[name]
            existing = self.inodes.get(existing_ino)
            if existing and existing.is_file():
                now = time.time()
                existing.content = content
                existing.size = len(content)
                existing.mtime = now
                existing.ctime = now
                return existing_ino
            return None

        # Create new file
        now = time.time()
        new_ino = self._allocate_inode()
        new_file = Inode(
            ino=new_ino,
            mode=FileType.REGULAR | mode,
            uid=uid,
            gid=gid,
            size=len(content),
            atime=now,
            mtime=now,
            ctime=now,
            content=content
        )

        self.inodes[new_ino] = new_file
        entries[name] = new_ino
        parent.mtime = now

        return new_ino

    def read_file(self, path: str, current_dir_ino: int = 1, size: int = -1) -> Optional[bytes]:
        """Read file contents"""
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return None

        inode = self.inodes.get(ino)
        if not inode:
            return None

        inode.atime = time.time()

        # Handle device files
        if inode.is_device():
            device_name = inode.content if isinstance(inode.content, str) else ''
            if device_name in self.device_handlers:
                read_handler, _ = self.device_handlers[device_name]
                read_size = size if size > 0 else 4096  # Default read size
                return read_handler(read_size)
            return b''

        # Regular file
        if not inode.is_file():
            return None

        content = inode.content if isinstance(inode.content, bytes) else None
        if content and size > 0:
            return content[:size]
        return content

    def write_file(self, path: str, content: bytes, current_dir_ino: int = 1) -> bool:
        """Write to existing file"""
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return False

        inode = self.inodes.get(ino)
        if not inode:
            return False

        # Handle device files
        if inode.is_device():
            device_name = inode.content if isinstance(inode.content, str) else ''
            if device_name in self.device_handlers:
                _, write_handler = self.device_handlers[device_name]
                write_handler(content)
                return True
            return False

        # Regular file
        if not inode.is_file():
            return False

        now = time.time()
        inode.content = content
        inode.size = len(content)
        inode.mtime = now
        inode.ctime = now

        return True

    def list_dir(self, path: str, current_dir_ino: int = 1) -> Optional[List[tuple]]:
        """
        List directory contents
        Returns list of (name, inode_number) tuples
        """
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return None

        inode = self.inodes.get(ino)
        if not inode or not inode.is_dir():
            return None

        entries = inode.content
        if not isinstance(entries, dict):
            return None

        inode.atime = time.time()
        return [(name, entry_ino) for name, entry_ino in entries.items()]

    def stat(self, path: str, current_dir_ino: int = 1) -> Optional[Inode]:
        """Get inode information for a path"""
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return None
        return self.inodes.get(ino)

    def lstat(self, path: str, current_dir_ino: int = 1) -> Optional[Inode]:
        """Get inode information without following symlinks"""
        ino = self._resolve_path(path, current_dir_ino, follow_symlinks=False)
        if ino is None:
            return None
        return self.inodes.get(ino)

    def exists(self, path: str, current_dir_ino: int = 1) -> bool:
        """Check if a path exists"""
        return self._resolve_path(path, current_dir_ino) is not None

    def unlink(self, path: str, current_dir_ino: int = 1) -> bool:
        """Remove a file or empty directory"""
        parent_path = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        name = path.rstrip('/').split('/')[-1]

        if name in ('.', '..'):
            return False

        parent_ino = self._resolve_path(parent_path, current_dir_ino)
        if parent_ino is None:
            return False

        parent = self.inodes.get(parent_ino)
        if not parent or not parent.is_dir():
            return False

        entries = parent.content
        if not isinstance(entries, dict) or name not in entries:
            return False

        target_ino = entries[name]
        target = self.inodes.get(target_ino)
        if not target:
            return False

        # Check if directory is empty
        if target.is_dir():
            target_entries = target.content
            if isinstance(target_entries, dict) and len(target_entries) > 2:  # More than . and ..
                return False

        # Remove entry
        del entries[name]
        target.nlink -= 1

        # Delete inode if no more links
        if target.nlink == 0:
            del self.inodes[target_ino]

        parent.mtime = time.time()
        return True

    def symlink(self, target: str, linkpath: str, uid: int, gid: int, current_dir_ino: int = 1) -> bool:
        """Create a symbolic link"""
        parent_path = '/'.join(linkpath.rstrip('/').split('/')[:-1]) or '/'
        name = linkpath.rstrip('/').split('/')[-1]

        parent_ino = self._resolve_path(parent_path, current_dir_ino)
        if parent_ino is None:
            return False

        parent = self.inodes.get(parent_ino)
        if not parent or not parent.is_dir():
            return False

        entries = parent.content
        if not isinstance(entries, dict) or name in entries:
            return False

        # Create symlink
        now = time.time()
        new_ino = self._allocate_inode()
        new_link = Inode(
            ino=new_ino,
            mode=FileType.SYMLINK | 0o777,
            uid=uid,
            gid=gid,
            size=len(target),
            atime=now,
            mtime=now,
            ctime=now,
            content=target
        )

        self.inodes[new_ino] = new_link
        entries[name] = new_ino
        parent.mtime = now

        return True

    def create_device(self, path: str, is_char: bool, uid: int, gid: int, current_dir_ino: int = 1, device_name: str = '') -> bool:
        """Create a device file

        Args:
            path: Path to create device file at
            is_char: True for character device, False for block device
            uid, gid: Owner
            current_dir_ino: Current directory inode
            device_name: Name of the device (e.g. 'null', 'zero', 'tty')
        """
        parent_path = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        name = path.rstrip('/').split('/')[-1]

        parent_ino = self._resolve_path(parent_path, current_dir_ino)
        if parent_ino is None:
            return False

        parent = self.inodes.get(parent_ino)
        if not parent or not parent.is_dir():
            return False

        entries = parent.content
        if not isinstance(entries, dict) or name in entries:
            return False

        # If device_name not specified, use the filename
        if not device_name:
            device_name = name

        # Create device
        now = time.time()
        new_ino = self._allocate_inode()
        ftype = FileType.CHARDEV if is_char else FileType.BLOCKDEV
        new_dev = Inode(
            ino=new_ino,
            mode=ftype | 0o666,
            uid=uid,
            gid=gid,
            size=0,
            atime=now,
            mtime=now,
            ctime=now,
            content=device_name  # Store device name for handler lookup
        )

        self.inodes[new_ino] = new_dev
        entries[name] = new_ino
        parent.mtime = now

        return True
