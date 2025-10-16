"""
Main Unix system implementation
Brings together VFS, permissions, processes, shell, and network
"""

from core.vfs import VFS, FileType
from core.permissions import PermissionSystem
from core.process import ProcessManager
from core.shell import Shell
from core.network import VirtualNetwork, NetworkCommands
from commands.fs import FilesystemCommands
from commands.proc import ProcessCommands
from commands.system import SystemCommands
from typing import Optional, Tuple


class UnixSystem:
    """
    Complete Unix-like system
    Manages VFS, users, processes, and provides shell interface
    """

    def __init__(self, hostname: str = 'localhost', ip: str = '127.0.0.1'):
        self.hostname = hostname
        self.ip = ip

        # Initialize core systems
        self.vfs = VFS()
        self.permissions = PermissionSystem()
        self.processes = ProcessManager()
        self.shell = Shell(self.vfs, self.permissions, self.processes)
        self.network: Optional[VirtualNetwork] = None

        # Current user shell process
        self.shell_pid: Optional[int] = None

        # Initialize filesystem
        self._init_filesystem()

        # Register commands
        self._register_commands()

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

        # Create device files
        self.vfs.create_device('/dev/null', True, 0, 0)
        self.vfs.create_device('/dev/zero', True, 0, 0)
        self.vfs.create_device('/dev/random', True, 0, 0)
        self.vfs.create_device('/dev/tty', True, 0, 0)

        # Populate /bin with "executable" files (just placeholders)
        binaries = ['ls', 'cat', 'grep', 'ps', 'kill', 'echo', 'mkdir', 'rm',
                    'touch', 'sh', 'bash', 'cp', 'mv', 'chmod', 'chown', 'tar',
                    'gzip', 'gunzip', 'date', 'hostname', 'netstat', 'mount']

        for binary in binaries:
            self.vfs.create_file(f'/bin/{binary}', 0o755, 0, 0,
                                b'#!/bin/sh\n# Binary placeholder\n', 1)

        # Populate /usr/bin
        usr_binaries = ['find', 'which', 'whoami', 'id', 'env', 'less', 'more',
                       'head', 'tail', 'wc', 'sort', 'uniq', 'diff', 'patch',
                       'make', 'gcc', 'perl', 'python', 'awk', 'sed', 'vi',
                       'nmap', 'telnet', 'ftp', 'wget', 'curl', 'ssh', 'uptime']

        for binary in usr_binaries:
            self.vfs.create_file(f'/usr/bin/{binary}', 0o755, 0, 0,
                                b'#!/bin/sh\n# Binary placeholder\n', 1)

        # Populate /sbin
        sbin_binaries = ['ifconfig', 'route', 'iptables', 'init', 'shutdown',
                        'reboot', 'fdisk', 'fsck', 'mkfs']

        for binary in sbin_binaries:
            self.vfs.create_file(f'/sbin/{binary}', 0o755, 0, 0,
                                b'#!/bin/sh\n# Binary placeholder\n', 1)

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

    def _register_commands(self):
        """Register all available commands"""
        # Filesystem commands
        fs_cmds = FilesystemCommands(self.vfs, self.permissions, self.processes)
        self.shell.register_builtin('cd', fs_cmds.cmd_cd)
        self.shell.register_command('pwd', fs_cmds.cmd_pwd)
        self.shell.register_command('ls', fs_cmds.cmd_ls)
        self.shell.register_command('cat', fs_cmds.cmd_cat)
        self.shell.register_command('mkdir', fs_cmds.cmd_mkdir)
        self.shell.register_command('touch', fs_cmds.cmd_touch)
        self.shell.register_command('rm', fs_cmds.cmd_rm)
        self.shell.register_command('echo', fs_cmds.cmd_echo)
        self.shell.register_command('grep', fs_cmds.cmd_grep)
        self.shell.register_command('find', fs_cmds.cmd_find)

        # Process commands
        proc_cmds = ProcessCommands(self.vfs, self.permissions, self.processes)
        self.shell.register_command('ps', proc_cmds.cmd_ps)
        self.shell.register_command('kill', proc_cmds.cmd_kill)
        self.shell.register_command('killall', proc_cmds.cmd_killall)
        self.shell.register_command('exploit', proc_cmds.cmd_exploit)
        self.shell.register_command('pstree', proc_cmds.cmd_pstree)

        # System commands
        sys_cmds = SystemCommands(self.vfs, self.permissions, self.processes, self.hostname)
        self.shell.register_command('whoami', sys_cmds.cmd_whoami)
        self.shell.register_command('hostname', sys_cmds.cmd_hostname)
        self.shell.register_command('uname', sys_cmds.cmd_uname)
        self.shell.register_command('which', sys_cmds.cmd_which)
        self.shell.register_command('date', sys_cmds.cmd_date)
        self.shell.register_command('uptime', sys_cmds.cmd_uptime)
        self.shell.register_command('id', sys_cmds.cmd_id)
        self.shell.register_command('env', sys_cmds.cmd_env)
        self.shell.register_command('clear', sys_cmds.cmd_clear)
        self.shell.register_command('history', sys_cmds.cmd_history)
        self.shell.register_command('man', sys_cmds.cmd_man)

    def add_network(self, network: VirtualNetwork):
        """Attach system to a virtual network"""
        self.network = network
        network.register_system(self.ip, self)

        # Register network commands
        net_cmds = NetworkCommands(self.vfs, self.permissions, self.processes, network)
        self.shell.register_command('ifconfig', net_cmds.cmd_ifconfig)
        self.shell.register_command('netstat', net_cmds.cmd_netstat)
        self.shell.register_command('nmap', net_cmds.cmd_nmap)
        self.shell.register_command('ssh', net_cmds.cmd_ssh)

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
        Execute a command in the current shell
        Returns (exit_code, stdout, stderr) as strings
        """
        if self.shell_pid is None:
            return 1, '', 'Not logged in'

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
        fs_cmds = FilesystemCommands(self.vfs, self.permissions, self.processes)
        cwd = fs_cmds._inode_to_path(cwd_ino)

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
