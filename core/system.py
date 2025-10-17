"""
Main Unix system implementation
Brings together VFS, permissions, processes, shell, and network
"""

from core.vfs import VFS, FileType
from core.permissions import PermissionSystem
from core.process import ProcessManager
from core.shell import Shell
from core.network import VirtualNetwork, NetworkCommands
from core.packet_queue import PacketQueue
from core.network_physical import NetworkInterface
from core.daemon import DaemonManager
from core.script_installer import install_scripts
from core.kernel import Kernel  # NEW: Kernel layer
from core.tty import TTYManager, TTY  # NEW: TTY virtualization
from typing import Optional, Tuple, Dict


class UnixSystem:
    """
    Complete Unix-like system
    Manages VFS, users, processes, and provides shell interface
    """

    def __init__(self, hostname: str = 'localhost', ip_or_interfaces = None):
        """
        Initialize Unix system

        Args:
            hostname: System hostname
            ip_or_interfaces: Either:
                - String: Single IP address (legacy, creates eth0 with this IP)
                - Dict: interface_name -> ip_address (e.g., {'eth0': '192.168.1.1', 'eth1': '10.0.0.1'})
                - None: No network (loopback only)
        """
        self.hostname = hostname

        # Network interfaces: {'eth0': '192.168.1.1', 'eth1': '10.0.0.1'}
        if isinstance(ip_or_interfaces, str):
            # Legacy: single IP address, create eth0
            self.interfaces = {'lo': '127.0.0.1', 'eth0': ip_or_interfaces}
        elif isinstance(ip_or_interfaces, dict):
            # New: multiple interfaces
            self.interfaces = {'lo': '127.0.0.1', **ip_or_interfaces}
        else:
            # No network (loopback only)
            self.interfaces = {'lo': '127.0.0.1'}

        # Primary IP (first non-loopback interface)
        self.ip = self._get_primary_ip()

        # Physical network interfaces (NetworkInterface objects)
        # Maps interface name to NetworkInterface (e.g., {'eth0': NetworkInterface(...), 'eth1': ...})
        self.net_interfaces: Dict[str, NetworkInterface] = {}
        self._init_network_interfaces()

        # Local packet queue for packets delivered to localhost
        # PooScript netd writes packets here when they're destined for this system
        self.local_packet_queue: list = []

        # Initialize core systems
        self.vfs = VFS()
        self.permissions = PermissionSystem()
        self.processes = ProcessManager()
        self.daemon_manager = DaemonManager()  # Background daemon support
        self.tty_manager = TTYManager()  # NEW: TTY virtualization
        self.network: Optional[VirtualNetwork] = None
        self.packet_queue = PacketQueue(self, self.network)

        # NEW: Initialize kernel (Python becomes the kernel layer)
        self.kernel = Kernel(self.vfs, self.processes, self.permissions, self.network)

        self.shell = Shell(self.vfs, self.permissions, self.processes, self.network, self.ip, system=self)

        # Wire VFS to system (for network device handlers)
        self.vfs.system = self

        # Network configuration
        self.firewall_rules = []     # Firewall rules managed by iptables
        self.routing_table = []      # Routing table entries
        self.ip_forward = False      # IP forwarding enabled (acts as router)
        self.default_gateway = None  # Default gateway for outbound traffic

        # System state
        self.running = False         # Is system currently running/alive
        self.crashed = False         # Has system crashed

        # Current user shell process
        self.shell_pid: Optional[int] = None

        # Initialize filesystem
        self._init_filesystem()

        # Register commands
        self._register_commands()

    def _get_primary_ip(self) -> str:
        """Get primary IP address (first non-loopback interface)"""
        for iface, ip in self.interfaces.items():
            if iface != 'lo' and ip != '127.0.0.1':
                return ip
        return '127.0.0.1'

    def _create_tty_device(self, device_path: str, tty_name: str):
        """Create a TTY device file with integrated TTY object"""
        # Create virtual TTY
        tty = self.tty_manager.create_tty(tty_name)

        # Create device handlers that use this TTY
        def tty_read(size):
            data = tty.read(size)
            return data

        def tty_write(data):
            return tty.write(data)

        # Register handlers
        self.vfs.device_handlers[tty_name] = (tty_read, tty_write)

        # Create device file
        self.vfs.create_device(device_path, True, 0, 0, device_name=tty_name)

    def create_pty_pair(self) -> tuple[str, str, TTY, TTY]:
        """
        Create a PTY pair for a new terminal session
        Returns (master_path, slave_path, master_tty, slave_tty)
        """
        # Create PTY pair
        master, slave = self.tty_manager.create_pty()

        # Create device files
        master_path = f'/dev/ptm/{master.number}'
        slave_path = f'/dev/pts/{slave.number}'

        # Create device handlers for master
        def master_read(size):
            # Read from slave's output (what the shell writes)
            return slave.read_output(size)

        def master_write(data):
            # Write to slave's input (user input)
            slave.process_input(data)
            return len(data)

        self.vfs.device_handlers[master.name] = (master_read, master_write)

        # Create device handlers for slave
        def slave_read(size):
            return slave.read(size)

        def slave_write(data):
            return slave.write(data)

        self.vfs.device_handlers[slave.name] = (slave_read, slave_write)

        # Create device files
        self.vfs.create_device(master_path, True, 0, 0, device_name=master.name)
        self.vfs.create_device(slave_path, True, 0, 0, device_name=slave.name)

        return master_path, slave_path, master, slave

    def _init_network_interfaces(self):
        """Create physical NetworkInterface objects for each interface"""
        for iface_name, ip in self.interfaces.items():
            if iface_name == 'lo':
                continue  # Skip loopback - it's not a real network interface

            # Generate MAC address from IP (deterministic but unique)
            octets = [int(x) for x in ip.split('.')]
            mac = f"08:00:27:{octets[1]:02x}:{octets[2]:02x}:{octets[3]:02x}"

            # Create NetworkInterface object
            net_iface = NetworkInterface(
                name=iface_name,
                mac=mac,
                rx_buffer=[],
                tx_buffer=[],
                segment=None,
                up=True
            )

            self.net_interfaces[iface_name] = net_iface

    def _init_filesystem(self):
        """Create basic Unix filesystem structure"""
        # Create standard directories
        dirs = [
            '/bin', '/sbin', '/usr', '/usr/bin', '/usr/sbin', '/usr/local',
            '/etc', '/var', '/var/log', '/var/www', '/tmp', '/home', '/root',
            '/dev', '/proc', '/sys', '/opt'
        ]

        for path in dirs:
            self.vfs.mkdir(path, 0o755, 0, 0)

        # Create some basic files
        self.vfs.create_file('/etc/passwd', 0o644, 0, 0,
                            b'root:x:0:0:root:/root:/bin/sh\n', 1)

        self.vfs.create_file('/etc/shadow', 0o600, 0, 0,
                            b'root:H:root:18000:0:99999:7:::\n', 1)

        self.vfs.create_file('/etc/hosts', 0o644, 0, 0,
                            b'127.0.0.1\tlocalhost\n', 1)

        self.vfs.create_file('/etc/hostname', 0o644, 0, 0,
                            f'{self.hostname}\n'.encode(), 1)

        self.vfs.create_file('/etc/issue', 0o644, 0, 0,
                            b'Linux 2.0.38 \\n \\l\n', 1)

        # Create network configuration directory
        self.vfs.mkdir('/etc/network', 0o755, 0, 0)

        # Create /etc/network/interfaces file
        # This lists all configured interfaces
        interfaces_content = "# Network interface configuration\n"
        interfaces_content += "# Format: interface ip/netmask\n\n"
        for iface, ip in self.interfaces.items():
            if iface != 'lo':
                interfaces_content += f"{iface} {ip}/24\n"

        self.vfs.create_file('/etc/network/interfaces', 0o644, 0, 0,
                            interfaces_content.encode(), 1)

        # Create /etc/network/routes file
        # This will be populated later when routing is configured
        # Format: destination gateway netmask interface
        routes_content = "# Routing table\n"
        routes_content += "# Format: destination gateway netmask interface\n"
        routes_content += "# Example: 192.168.2.0 192.168.1.1 255.255.255.0 eth0\n\n"

        self.vfs.create_file('/etc/network/routes', 0o644, 0, 0,
                            routes_content.encode(), 1)

        # Create functional device files
        self.vfs.create_device('/dev/null', True, 0, 0, device_name='null')
        self.vfs.create_device('/dev/zero', True, 0, 0, device_name='zero')
        self.vfs.create_device('/dev/random', True, 0, 0, device_name='random')
        self.vfs.create_device('/dev/urandom', True, 0, 0, device_name='urandom')

        # Create virtualized TTY devices
        # Console and standard TTYs
        self._create_tty_device('/dev/console', 'console')
        self._create_tty_device('/dev/tty', 'tty')
        self._create_tty_device('/dev/tty0', 'tty0')
        self._create_tty_device('/dev/tty1', 'tty1')
        self._create_tty_device('/dev/tty2', 'tty2')
        self._create_tty_device('/dev/tty3', 'tty3')

        # Standard streams
        self.vfs.create_device('/dev/stdin', True, 0, 0, device_name='stdin')
        self.vfs.create_device('/dev/stdout', True, 0, 0, device_name='stdout')
        self.vfs.create_device('/dev/stderr', True, 0, 0, device_name='stderr')

        # Additional common devices
        self.vfs.create_device('/dev/full', True, 0, 0, device_name='full')  # Always returns ENOSPC on write
        self.vfs.create_device('/dev/kmsg', True, 0, 0, device_name='kmsg')  # Kernel messages

        # Pseudo-TTY master/slave directory
        self.vfs.mkdir('/dev/pts', 0o755, 0, 0)
        self.vfs.mkdir('/dev/ptm', 0o755, 0, 0)

        # Network devices
        self.vfs.mkdir('/dev/net', 0o755, 0, 0)
        self.vfs.create_device('/dev/net/tun', True, 0, 0, device_name='tun')
        self.vfs.create_device('/dev/net/packet', True, 0, 0, device_name='packet')
        self.vfs.create_device('/dev/net/arp', True, 0, 0, device_name='arp')
        self.vfs.create_device('/dev/net/route', True, 0, 0, device_name='route')

        # Create raw interface devices for PooScript network access
        # /dev/net/eth0_raw, /dev/net/eth1_raw, etc.
        for iface_name in self.net_interfaces.keys():
            device_path = f'/dev/net/{iface_name}_raw'
            device_name = f'{iface_name}_raw'

            # Register handler for this interface
            self.vfs.device_handlers[device_name] = self.vfs._make_interface_handlers(iface_name)

            # Create device file
            self.vfs.create_device(device_path, True, 0, 0, device_name=device_name)

        # Create /dev/net/local for localhost packet delivery
        self.vfs.create_device('/dev/net/local', True, 0, 0, device_name='local')

        # Create /proc/sys/net for network configuration
        self.vfs.mkdir('/proc/sys', 0o555, 0, 0)
        self.vfs.mkdir('/proc/sys/net', 0o555, 0, 0)
        self.vfs.mkdir('/proc/sys/net/ipv4', 0o555, 0, 0)

        # IP forwarding control (0 = disabled, 1 = enabled)
        self.vfs.create_file('/proc/sys/net/ipv4/ip_forward', 0o644, 0, 0, b'0\n', 1)

        # Create /proc/net for network state (as device files for dynamic content)
        self.vfs.mkdir('/proc/net', 0o555, 0, 0)
        self.vfs.create_device('/proc/net/dev', True, 0, 0, device_name='proc_net_dev')
        self.vfs.create_device('/proc/net/arp', True, 0, 0, device_name='proc_net_arp')
        self.vfs.create_device('/proc/net/route', True, 0, 0, device_name='proc_net_route')
        self.vfs.create_device('/proc/net/tcp', True, 0, 0, device_name='proc_net_tcp')
        self.vfs.create_device('/proc/net/udp', True, 0, 0, device_name='proc_net_udp')

        # Install PooScript commands from scripts/ directory (silently)
        install_scripts(self.vfs, verbose=False)

        # Create log files
        self.vfs.create_file('/var/log/messages', 0o644, 0, 0,
                            b'Jan 10 14:23:15 localhost kernel: Linux version 2.0.38\n', 1)

        self.vfs.create_file('/var/log/auth.log', 0o640, 0, 4,
                            b'Jan 10 14:30:22 localhost login[1234]: ROOT LOGIN on tty1\n', 1)

        # Create a welcome message
        motd = b"""
        ================================================
        Welcome to the Virtual Unix System
        ================================================

        This is a simulated Unix environment for hacking challenges.
        Type 'help' for available commands.

        Good luck!
        ================================================
        """
        self.vfs.create_file('/etc/motd', 0o644, 0, 0, motd, 1)

        # Create standard Unix symlinks for realism
        # Note: /bin/sh will point to pooshell after scripts are installed
        self.vfs.symlink('/usr/bin/python3', '/usr/bin/python', 0, 0, 1)  # python -> python3

    def _register_commands(self):
        """Register shell builtins (commands that must modify shell state)"""
        # cd is a true builtin - it needs to modify the shell process's cwd
        def cmd_cd(command, current_pid, input_data):
            """Change directory builtin"""
            process = self.processes.get_process(current_pid)
            if not process:
                return 1, b'', b'Process not found\n'

            if not command.args:
                # cd with no args goes to HOME
                user = self.permissions.get_user(process.uid)
                if user:
                    target = user.home
                else:
                    target = '/'
            else:
                target = command.args[0]

            # Resolve path
            target_ino = self.vfs._resolve_path(target, process.cwd)
            if target_ino is None:
                return 1, b'', f'cd: {target}: No such file or directory\n'.encode()

            target_inode = self.vfs.inodes.get(target_ino)
            if not target_inode or not target_inode.is_dir():
                return 1, b'', f'cd: {target}: Not a directory\n'.encode()

            # Check permissions
            if not self.permissions.can_execute(process.uid, target_inode.mode, target_inode.uid, target_inode.gid):
                return 1, b'', f'cd: {target}: Permission denied\n'.encode()

            # Update process cwd
            self.processes.update_cwd(current_pid, target_ino)
            return 0, b'', b''

        self.shell.register_builtin('cd', cmd_cd)

        # All other commands are now PooScript binaries in /bin, /usr/bin, etc.
        # They are executed by the shell finding them in $PATH

    def boot(self, verbose: bool = True) -> bool:
        """
        Boot the system by running /sbin/init

        Args:
            verbose: If True, print boot messages. If False, boot silently.

        Returns True if boot successful
        """
        # Mark system as running
        self.running = True
        self.crashed = False

        # Check if init exists
        init_binary = self.vfs.stat('/sbin/init', 1)
        if not init_binary:
            if verbose:
                print("Warning: /sbin/init not found, skipping boot sequence")
            return False

        # Execute init as PID 1 (well, through our init process)
        init_proc = self.processes.get_process(1)
        if init_proc:
            exit_code, stdout, stderr = self.shell.execute('/sbin/init', 1)
            if verbose:
                if stdout:
                    print(stdout.decode('utf-8', errors='ignore'), end='')
                if stderr:
                    print(stderr.decode('utf-8', errors='ignore'), end='')

            # After init completes, start network daemon if it exists
            if self.vfs.stat('/sbin/netd', 1):
                # Spawn netd as a TRUE background daemon
                netd_pid = self.daemon_manager.spawn_daemon('netd', '/sbin/netd', self)
                if verbose and netd_pid:
                    print(f"[  OK  ] Network daemon started as background process (PID {netd_pid})")
                if netd_pid:
                    # Give netd a moment to initialize
                    import time
                    time.sleep(0.2)
                elif verbose:
                    print("[WARN ] Failed to start network daemon")

            return exit_code == 0

        return False

    def shutdown(self):
        """Gracefully shutdown the system"""
        self.running = False
        print(f"System {self.hostname} shutting down...")

    def crash(self):
        """Simulate a system crash (ungraceful shutdown)"""
        self.running = False
        self.crashed = True
        print(f"KERNEL PANIC: System {self.hostname} has crashed!")

    def is_alive(self) -> bool:
        """Check if system is running and can process packets"""
        return self.running and not self.crashed

    def add_network(self, network):
        """
        Attach system to a virtual network

        Supports both VirtualNetwork (old) and NetworkAdapter (new)
        """
        self.network = network

        # Update packet queue's network reference
        # NetworkAdapter wraps VirtualNetwork, so use .virtual_network if available
        if hasattr(network, 'virtual_network'):
            self.packet_queue.network = network.virtual_network
            shell_network = network.virtual_network
        else:
            self.packet_queue.network = network
            shell_network = network

        # Register system for ALL its IP addresses (not just primary)
        # This allows routing to work with multi-interface systems
        for interface, ip in self.interfaces.items():
            if interface != 'lo' and ip != '127.0.0.1':
                network.register_system(ip, self)

        # Update shell's network reference
        self.shell.network = shell_network
        self.shell.executor.network = shell_network
        self.shell.executor.local_ip = self.ip

        # Network commands (ifconfig, netstat, nmap, ssh) can be added as PooScripts later
        # For now, they would need special handling for network access
        # TODO: Create PooScript versions or expose network API to scripts

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate user and start shell session
        Returns True if successful
        """
        if not self.permissions.check_password(username, password):
            return False

        user = self.permissions.get_user_by_name(username)
        if not user:
            return False

        # Spawn shell process for this user
        self.shell_pid = self.processes.spawn(
            parent_pid=1,
            uid=user.uid,
            gid=user.gid,
            euid=user.uid,
            egid=user.gid,
            command='sh',
            args=['sh'],
            cwd=self.vfs._resolve_path(user.home, 1) or 1,
            env={
                'PATH': '/bin:/usr/bin:/sbin:/usr/sbin',
                'HOME': user.home,
                'USER': username,
                'SHELL': user.shell,
                'HOSTNAME': self.hostname
            }
        )

        return self.shell_pid is not None

    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """
        Execute a command in the current shell (via PooScript /bin/sh)
        Returns (exit_code, stdout, stderr) as strings
        """
        if self.shell_pid is None:
            return 1, '', 'Not logged in'

        # Check if /bin/pooshell exists as a PooScript
        sh_binary = self.vfs.stat('/bin/pooshell', 1)
        if sh_binary:
            # Execute via PooScript shell
            # The shell script will handle built-ins and execute external commands
            exit_code, stdout, stderr = self.shell.execute(f'/bin/pooshell -c \'{command}\'', self.shell_pid)
        else:
            # Fallback to Python shell
            exit_code, stdout, stderr = self.shell.execute(command, self.shell_pid)

        return exit_code, stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')

    def get_prompt(self) -> str:
        """Get command prompt for current user"""
        if self.shell_pid is None:
            return '> '

        process = self.processes.get_process(self.shell_pid)
        if not process:
            return '> '

        user = self.permissions.get_user(process.uid)
        username = user.username if user else 'unknown'

        # Get current directory
        cwd_ino = process.cwd
        cwd = self.vfs.inode_to_path(cwd_ino)

        # Simplify home directory
        if user and cwd.startswith(user.home):
            cwd = '~' + cwd[len(user.home):]

        prompt_char = '#' if process.uid == 0 else '$'

        return f'{username}@{self.hostname}:{cwd}{prompt_char} '

    def spawn_service(self, name: str, tags: list, uid: int = 0):
        """Spawn a background service/daemon"""
        pid = self.processes.spawn(
            parent_pid=1,
            uid=uid,
            gid=0,
            euid=uid,
            egid=0,
            command=name,
            args=[name],
            cwd=1,
            env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin'},
            tags=tags
        )
        return pid

    def add_user(self, username: str, password: str, uid: int, home: str):
        """Add a new user to the system"""
        # Create user
        success = self.permissions.add_user(uid, username, 100, home, '/bin/sh', password)
        if not success:
            return False

        # Create home directory
        self.vfs.mkdir(home, 0o755, uid, 100)

        # Update /etc/passwd
        passwd_content = self.vfs.read_file('/etc/passwd', 1) or b''
        new_entry = f'{username}:x:{uid}:100:{username}:{home}:/bin/sh\n'
        self.vfs.write_file('/etc/passwd', passwd_content + new_entry.encode(), 1)

        return True

    def create_vulnerable_file(self, path: str, content: bytes, hint: str = ''):
        """Create a file with game clues/vulnerabilities"""
        ino = self.vfs.create_file(path, 0o644, 0, 0, content, 1)
        if ino and hint:
            # Store hint as extended attribute (simplified - just in content)
            pass
        return ino
