"""
Process management commands
ps, kill, killall, etc.
"""

from typing import Tuple


class ProcessCommands:
    """Collection of process commands"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_ps(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """List processes"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        show_all = '-a' in command.args or '-e' in command.args
        show_full = '-f' in command.args

        # Get processes to display
        procs = self.processes.list_processes()

        if not show_all:
            # Only show processes for current user
            procs = [p for p in procs if p.uid == process.uid]

        # Sort by PID
        procs.sort(key=lambda p: p.pid)

        # Format output
        lines = []
        if show_full:
            lines.append('UID        PID  PPID  C STIME   TIME CMD')
            for p in procs:
                user = self.permissions.get_user(p.uid)
                username = user.username if user else str(p.uid)
                cmd = ' '.join([p.command] + p.args)
                lines.append(f'{username:8} {p.pid:5} {p.ppid:5}  0 00:00  00:00 {cmd}')
        else:
            lines.append('  PID TTY          TIME CMD')
            for p in procs:
                cmd = p.command
                lines.append(f'{p.pid:5} ?        00:00:00 {cmd}')

        return 0, '\n'.join(lines).encode() + b'\n', b''

    def cmd_kill(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Send signal to process"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse signal
        signal = 15  # Default SIGTERM
        pids = []

        for arg in command.args:
            if arg.startswith('-'):
                try:
                    signal = int(arg[1:])
                except ValueError:
                    return 1, b'', f'kill: invalid signal {arg}\n'.encode()
            else:
                try:
                    pids.append(int(arg))
                except ValueError:
                    return 1, b'', f'kill: invalid PID {arg}\n'.encode()

        if not pids:
            return 1, b'', b'kill: missing PID\n'

        # Kill processes
        for pid in pids:
            target = self.processes.get_process(pid)
            if not target:
                return 1, b'', f'kill: ({pid}) - No such process\n'.encode()

            # Check permissions (can only kill own processes unless root)
            if process.uid != 0 and target.uid != process.uid:
                return 1, b'', f'kill: ({pid}) - Operation not permitted\n'.encode()

            success = self.processes.kill_process(pid, signal)
            if not success:
                return 1, b'', f'kill: ({pid}) - Operation not permitted\n'.encode()

        return 0, b'', b''

    def cmd_killall(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Kill processes by name"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            return 1, b'', b'killall: missing process name\n'

        proc_name = command.args[0]
        signal = 15  # Default SIGTERM

        # Find processes by name
        targets = self.processes.find_by_name(proc_name)
        if not targets:
            return 1, b'', f'killall: no process found\n'.encode()

        killed = 0
        for target in targets:
            # Check permissions
            if process.uid != 0 and target.uid != process.uid:
                continue

            if self.processes.kill_process(target.pid, signal):
                killed += 1

        if killed == 0:
            return 1, b'', f'killall: permission denied\n'.encode()

        return 0, b'', b''

    def cmd_exploit(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """
        Game mechanic: Exploit a vulnerable process
        Usage: exploit <pid> [damage]
        """
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            return 1, b'', b'exploit: missing PID\n'

        try:
            target_pid = int(command.args[0])
        except ValueError:
            return 1, b'', f'exploit: invalid PID\n'.encode()

        damage = 50  # Default damage
        if len(command.args) > 1:
            try:
                damage = int(command.args[1])
            except ValueError:
                pass

        target = self.processes.get_process(target_pid)
        if not target:
            return 1, b'', f'exploit: no such process\n'.encode()

        # Check if process is exploitable (has certain tags)
        exploitable_tags = ['vulnerable', 'webserver', 'service']
        if not any(tag in target.tags for tag in exploitable_tags):
            return 1, b'', f'exploit: target not vulnerable\n'.encode()

        # Attempt exploit
        success = self.processes.damage_process(target_pid, damage)
        if success:
            if target.health <= 0:
                return 0, f'[+] Exploit successful! Process {target_pid} terminated.\n'.encode(), b''
            else:
                return 0, f'[+] Exploit successful! Process health: {target.health}\n'.encode(), b''
        else:
            return 1, b'', f'exploit: failed\n'.encode()

    def cmd_pstree(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Show process tree"""
        tree = self.processes.get_process_tree()

        lines = []
        self._format_tree(1, tree, '', lines, set())

        return 0, '\n'.join(lines).encode() + b'\n', b''

    def _format_tree(self, pid: int, tree: dict, prefix: str, lines: list, visited: set):
        """Recursively format process tree"""
        if pid in visited:
            return

        visited.add(pid)

        process = self.processes.get_process(pid)
        if not process:
            return

        lines.append(f'{prefix}{process.command}({pid})')

        children = tree.get(pid, [])
        for i, child_pid in enumerate(children):
            is_last = i == len(children) - 1
            new_prefix = prefix + ('    ' if is_last else '│   ')
            child_marker = '└── ' if is_last else '├── '
            self._format_tree(child_pid, tree, prefix + child_marker, lines, visited)
