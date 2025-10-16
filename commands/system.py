"""
System information and utility commands
whoami, hostname, uname, which, date, etc.
"""

import time
from typing import Tuple


class SystemCommands:
    """Collection of system utility commands"""

    def __init__(self, vfs, permissions, processes, hostname='localhost'):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes
        self.hostname = hostname

    def cmd_whoami(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print current username"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        user = self.permissions.get_user(process.uid)
        username = user.username if user else str(process.uid)

        return 0, f'{username}\n'.encode(), b''

    def cmd_hostname(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print system hostname"""
        return 0, f'{self.hostname}\n'.encode(), b''

    def cmd_uname(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print system information"""
        show_all = '-a' in command.args

        if show_all:
            output = f'Linux {self.hostname} 2.0.38 #1 Sun Jan 10 20:21:09 EST 1999 i586 GNU/Linux\n'
        else:
            output = 'Linux\n'

        return 0, output.encode(), b''

    def cmd_which(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Locate a command"""
        if not command.args:
            return 1, b'', b'which: missing argument\n'

        # Check if command exists in our registered commands
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        cmd_name = command.args[0]

        # Check builtins and commands
        from core.shell import Shell
        # This is a bit hacky but works for now
        # In reality we'd check $PATH and look for executables

        # Common command locations
        common_paths = {
            'ls': '/bin/ls',
            'cat': '/bin/cat',
            'grep': '/bin/grep',
            'ps': '/bin/ps',
            'kill': '/bin/kill',
            'echo': '/bin/echo',
            'mkdir': '/bin/mkdir',
            'rm': '/bin/rm',
            'touch': '/bin/touch',
            'find': '/usr/bin/find',
            'whoami': '/usr/bin/whoami',
            'hostname': '/bin/hostname',
            'uname': '/bin/uname',
            'which': '/usr/bin/which',
            'date': '/bin/date',
            'uptime': '/usr/bin/uptime',
            'nmap': '/usr/bin/nmap',
            'ifconfig': '/sbin/ifconfig',
            'netstat': '/bin/netstat',
        }

        if cmd_name in common_paths:
            return 0, f'{common_paths[cmd_name]}\n'.encode(), b''
        else:
            return 1, b'', f'which: no {cmd_name} in PATH\n'.encode()

    def cmd_date(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print current date and time"""
        current_time = time.strftime('%a %b %d %H:%M:%S %Z %Y')
        return 0, f'{current_time}\n'.encode(), b''

    def cmd_uptime(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Show how long system has been running"""
        # Fake uptime for game purposes
        output = ' 14:23:17 up 3 days,  2:15,  1 user,  load average: 0.08, 0.12, 0.09\n'
        return 0, output.encode(), b''

    def cmd_id(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print user and group IDs"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        user = self.permissions.get_user(process.uid)
        username = user.username if user else 'unknown'

        output = f'uid={process.uid}({username}) gid={process.gid} groups={process.gid}\n'
        return 0, output.encode(), b''

    def cmd_env(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print environment variables"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        lines = []
        for key, value in sorted(process.env.items()):
            lines.append(f'{key}={value}')

        return 0, '\n'.join(lines).encode() + b'\n', b''

    def cmd_clear(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Clear the screen"""
        # ANSI escape code to clear screen
        return 0, b'\033[2J\033[H', b''

    def cmd_history(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Show command history (placeholder)"""
        output = """  1  ls
  2  cd /etc
  3  cat /etc/passwd
  4  whoami
"""
        return 0, output.encode(), b''

    def cmd_man(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Manual pages (simplified)"""
        if not command.args:
            return 1, b'', b'What manual page do you want?\n'

        cmd = command.args[0]

        manpages = {
            'ls': 'ls - list directory contents\nUsage: ls [-la] [path...]',
            'cat': 'cat - concatenate files and print\nUsage: cat [file...]',
            'grep': 'grep - search for patterns\nUsage: grep pattern [file...]',
            'ps': 'ps - report process status\nUsage: ps [-aef]',
            'kill': 'kill - send signal to process\nUsage: kill [-signal] pid',
            'exploit': 'exploit - attack vulnerable process (GAME)\nUsage: exploit <pid> [damage]',
            'nmap': 'nmap - network scanner (GAME)\nUsage: nmap <target>',
        }

        if cmd in manpages:
            return 0, f'{manpages[cmd]}\n'.encode(), b''
        else:
            return 1, b'', f'No manual entry for {cmd}\n'.encode()
