"""
Process management system
Tracks running processes, PIDs, state, etc.
"""

import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class ProcessState(Enum):
    """Process states"""
    RUNNING = "R"
    SLEEPING = "S"
    STOPPED = "T"
    ZOMBIE = "Z"
    DEAD = "D"


@dataclass
class Process:
    """Unix process"""
    pid: int
    ppid: int  # Parent PID
    uid: int  # User ID
    gid: int  # Group ID
    euid: int  # Effective UID (for SUID)
    egid: int  # Effective GID (for SGID)
    command: str  # Command name
    args: List[str]  # Command arguments
    state: ProcessState = ProcessState.RUNNING
    cwd: int = 1  # Current working directory (inode)
    start_time: float = field(default_factory=time.time)
    cpu_time: float = 0.0

    # File descriptors
    stdin: int = 0
    stdout: int = 1
    stderr: int = 2

    # Environment variables
    env: Dict[str, str] = field(default_factory=dict)

    # Controlling terminal (TTY object reference)
    tty: Optional[Any] = None  # TTY object from core.tty

    # Exit status
    exit_code: Optional[int] = None

    # For game mechanics - process "health" (can be damaged/killed by exploits)
    health: int = 100

    # Tags for game mechanics (e.g., "firewall", "ids", "webserver")
    tags: List[str] = field(default_factory=list)


class ProcessManager:
    """Manage processes"""

    def __init__(self):
        self.processes: Dict[int, Process] = {}
        self.next_pid = 2  # PID 1 reserved for init

        # Create init process (PID 1)
        init = Process(
            pid=1,
            ppid=0,
            uid=0,
            gid=0,
            euid=0,
            egid=0,
            command='init',
            args=['init'],
            cwd=1,
            env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'}
        )
        self.processes[1] = init

    def spawn(self, parent_pid: int, uid: int, gid: int, euid: int, egid: int,
              command: str, args: List[str], cwd: int, env: Dict[str, str],
              tags: Optional[List[str]] = None) -> Optional[int]:
        """
        Spawn a new process
        Returns PID or None on failure
        """
        parent = self.processes.get(parent_pid)
        if not parent:
            return None

        pid = self.next_pid
        self.next_pid += 1

        process = Process(
            pid=pid,
            ppid=parent_pid,
            uid=uid,
            gid=gid,
            euid=euid,
            egid=egid,
            command=command,
            args=args,
            cwd=cwd,
            env=env.copy(),
            tags=tags or []
        )

        self.processes[pid] = process
        return pid

    def get_process(self, pid: int) -> Optional[Process]:
        """Get process by PID"""
        return self.processes.get(pid)

    def kill_process(self, pid: int, signal: int = 15) -> bool:
        """
        Kill a process
        Signal 9 = SIGKILL (immediate), 15 = SIGTERM (graceful)
        """
        if pid <= 1:  # Can't kill init
            return False

        process = self.processes.get(pid)
        if not process or process.state == ProcessState.DEAD:
            return False

        # For game purposes, different signals do different things
        if signal == 9:  # SIGKILL
            process.state = ProcessState.DEAD
            process.exit_code = 128 + 9
        elif signal == 15:  # SIGTERM
            process.state = ProcessState.DEAD
            process.exit_code = 0
        elif signal == 19:  # SIGSTOP
            process.state = ProcessState.STOPPED
        elif signal == 18:  # SIGCONT
            if process.state == ProcessState.STOPPED:
                process.state = ProcessState.RUNNING

        # Kill child processes
        if process.state == ProcessState.DEAD:
            for child_pid, child in list(self.processes.items()):
                if child.ppid == pid:
                    child.ppid = 1  # Reparent to init

        return True

    def damage_process(self, pid: int, damage: int) -> bool:
        """
        Damage a process (game mechanic)
        Used for exploit-based attacks
        """
        process = self.processes.get(pid)
        if not process or process.state == ProcessState.DEAD:
            return False

        process.health -= damage
        if process.health <= 0:
            process.health = 0
            return self.kill_process(pid, signal=9)

        return True

    def list_processes(self) -> List[Process]:
        """List all processes"""
        return [p for p in self.processes.values() if p.state != ProcessState.DEAD]

    def get_children(self, pid: int) -> List[Process]:
        """Get child processes of a PID"""
        return [p for p in self.processes.values() if p.ppid == pid and p.state != ProcessState.DEAD]

    def find_by_name(self, name: str) -> List[Process]:
        """Find processes by command name"""
        return [p for p in self.processes.values()
                if p.command == name and p.state != ProcessState.DEAD]

    def find_by_tag(self, tag: str) -> List[Process]:
        """Find processes by tag (game mechanic)"""
        return [p for p in self.processes.values()
                if tag in p.tags and p.state != ProcessState.DEAD]

    def cleanup_dead(self):
        """Remove dead processes (reaping zombies)"""
        dead_pids = [pid for pid, p in self.processes.items()
                     if p.state == ProcessState.DEAD and pid > 1]
        for pid in dead_pids:
            # Keep zombies if parent is still alive
            process = self.processes[pid]
            parent = self.processes.get(process.ppid)
            if not parent or parent.state == ProcessState.DEAD:
                del self.processes[pid]
            else:
                # Mark as zombie if not already
                if process.state != ProcessState.ZOMBIE:
                    process.state = ProcessState.ZOMBIE

    def get_process_tree(self, root_pid: int = 1) -> Dict[int, List[int]]:
        """
        Get process tree as dict of pid -> [child_pids]
        """
        tree: Dict[int, List[int]] = {}
        for pid, process in self.processes.items():
            if process.state == ProcessState.DEAD:
                continue
            if process.ppid not in tree:
                tree[process.ppid] = []
            tree[process.ppid].append(pid)
        return tree

    def update_cwd(self, pid: int, new_cwd: int) -> bool:
        """Update process current working directory"""
        process = self.processes.get(pid)
        if not process:
            return False
        process.cwd = new_cwd
        return True

    def set_env(self, pid: int, key: str, value: str) -> bool:
        """Set environment variable for process"""
        process = self.processes.get(pid)
        if not process:
            return False
        process.env[key] = value
        return True

    def get_env(self, pid: int, key: str) -> Optional[str]:
        """Get environment variable from process"""
        process = self.processes.get(pid)
        if not process:
            return None
        return process.env.get(key)
