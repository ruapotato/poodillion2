"""
Poodillion Kernel - Core syscall interface

This module provides the kernel layer that PooScript userland programs call.
Think of this as the Linux kernel - it provides low-level operations only.

All userland functionality (shell, commands, utilities) lives in PooScript.
"""

from typing import Optional, Tuple, List, Dict, Any
from enum import IntEnum


class Syscall(IntEnum):
    """Syscall numbers (like real Unix syscalls)"""
    # File operations
    OPEN = 1
    READ = 2
    WRITE = 3
    CLOSE = 4
    STAT = 5
    LSTAT = 6
    FSTAT = 7

    # Directory operations
    MKDIR = 8
    RMDIR = 9
    READDIR = 10
    CHDIR = 11
    GETCWD = 12

    # File management
    UNLINK = 13
    SYMLINK = 14
    READLINK = 15
    CHMOD = 16
    CHOWN = 17

    # Process operations
    FORK = 20
    EXEC = 21
    EXIT = 22
    WAIT = 23
    KILL = 24
    GETPID = 25
    GETPPID = 26
    GETUID = 27
    GETGID = 28
    SETUID = 29
    SETGID = 30

    # Network operations
    SOCKET = 40
    BIND = 41
    LISTEN = 42
    ACCEPT = 43
    CONNECT = 44
    SEND = 45
    RECV = 46
    SENDTO = 47
    RECVFROM = 48

    # I/O operations
    IOCTL = 50


class Kernel:
    """
    The Poodillion kernel

    Provides low-level syscalls for:
    - Filesystem operations (VFS)
    - Process management
    - Network stack
    - Device I/O

    All high-level functionality (shell, commands) is in PooScript userland.
    """

    def __init__(self, vfs, process_manager, permissions, network=None):
        """
        Initialize kernel with subsystems

        Args:
            vfs: Virtual filesystem
            process_manager: Process management
            permissions: Permission system
            network: Network stack (optional)
        """
        self.vfs = vfs
        self.process_manager = process_manager
        self.permissions = permissions
        self.network = network

        # Open file descriptors per process: {pid: {fd: inode}}
        self.file_descriptors = {}

    # =========================================================================
    # FILESYSTEM SYSCALLS
    # =========================================================================

    def sys_open(self, pid: int, path: str, flags: int, mode: int = 0o644) -> int:
        """
        Open a file and return file descriptor

        Args:
            pid: Process ID
            path: File path
            flags: Open flags (O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_APPEND)
            mode: Mode for file creation

        Returns:
            File descriptor number, or -1 on error
        """
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        # Resolve path
        inode_num = self.vfs._resolve_path(path, process.cwd)
        if inode_num is None:
            # File doesn't exist
            if flags & 0x100:  # O_CREAT
                inode_num = self.vfs.create_file(path, mode, process.euid, process.egid, b'', process.cwd)
                if inode_num is None:
                    return -1
            else:
                return -1

        inode = self.vfs.inodes.get(inode_num)
        if not inode:
            return -1

        # Check permissions
        if flags & 0x1:  # O_WRONLY or O_RDWR
            if not self.permissions.can_write(process.euid, inode.mode, inode.uid, inode.gid):
                return -1
        else:  # O_RDONLY
            if not self.permissions.can_read(process.euid, inode.mode, inode.uid, inode.gid):
                return -1

        # Allocate file descriptor
        if pid not in self.file_descriptors:
            self.file_descriptors[pid] = {}

        # Find lowest available FD (starting from 3, since 0-2 are stdin/stdout/stderr)
        fd = 3
        while fd in self.file_descriptors[pid]:
            fd += 1

        self.file_descriptors[pid][fd] = {
            'inode': inode_num,
            'flags': flags,
            'offset': 0
        }

        return fd

    def sys_read(self, pid: int, fd: int, count: int) -> Optional[bytes]:
        """
        Read from file descriptor

        Args:
            pid: Process ID
            fd: File descriptor
            count: Number of bytes to read

        Returns:
            Bytes read, or None on error
        """
        if pid not in self.file_descriptors or fd not in self.file_descriptors[pid]:
            return None

        fd_entry = self.file_descriptors[pid][fd]
        inode_num = fd_entry['inode']
        offset = fd_entry['offset']

        inode = self.vfs.inodes.get(inode_num)
        if not inode:
            return None

        # Get process for permission check
        process = self.process_manager.get_process(pid)
        if not process:
            return None

        # Check read permission
        if not self.permissions.can_read(process.euid, inode.mode, inode.uid, inode.gid):
            return None

        # Handle device files
        if inode.is_device():
            device_name = inode.content
            if device_name in self.vfs.device_handlers:
                handler = self.vfs.device_handlers[device_name]
                if 'read' in handler:
                    return handler['read']()
            return b''

        # Regular file
        content = inode.content if isinstance(inode.content, bytes) else b''
        data = content[offset:offset+count]
        fd_entry['offset'] += len(data)

        return data

    def sys_write(self, pid: int, fd: int, data: bytes) -> int:
        """
        Write to file descriptor

        Args:
            pid: Process ID
            fd: File descriptor
            data: Data to write

        Returns:
            Number of bytes written, or -1 on error
        """
        if pid not in self.file_descriptors or fd not in self.file_descriptors[pid]:
            return -1

        fd_entry = self.file_descriptors[pid][fd]
        inode_num = fd_entry['inode']

        inode = self.vfs.inodes.get(inode_num)
        if not inode:
            return -1

        # Get process for permission check
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        # Check write permission
        if not self.permissions.can_write(process.euid, inode.mode, inode.uid, inode.gid):
            return -1

        # Handle device files
        if inode.is_device():
            device_name = inode.content
            if device_name in self.vfs.device_handlers:
                handler = self.vfs.device_handlers[device_name]
                if 'write' in handler:
                    result = handler['write'](data)
                    return len(data) if result else -1
            return len(data)  # Pretend success for devices without handlers

        # Regular file - append data
        if isinstance(inode.content, bytes):
            offset = fd_entry['offset']
            content = inode.content

            # Write at offset
            new_content = content[:offset] + data + content[offset+len(data):]
            inode.content = new_content
            inode.size = len(new_content)
            fd_entry['offset'] += len(data)

            import time
            inode.mtime = time.time()

            return len(data)

        return -1

    def sys_close(self, pid: int, fd: int) -> int:
        """
        Close file descriptor

        Returns:
            0 on success, -1 on error
        """
        if pid not in self.file_descriptors or fd not in self.file_descriptors[pid]:
            return -1

        del self.file_descriptors[pid][fd]
        return 0

    def sys_stat(self, pid: int, path: str) -> Optional[Dict[str, Any]]:
        """
        Get file status

        Returns:
            Dictionary with file info, or None on error
        """
        process = self.process_manager.get_process(pid)
        if not process:
            return None

        inode = self.vfs.stat(path, process.cwd)
        if not inode:
            return None

        return {
            'size': inode.size,
            'mode': inode.mode,
            'uid': inode.uid,
            'gid': inode.gid,
            'is_file': inode.is_file(),
            'is_dir': inode.is_dir(),
            'is_symlink': inode.is_symlink(),
            'is_device': inode.is_device(),
            'nlink': inode.nlink,
            'mtime': inode.mtime,
            'atime': inode.atime,
            'ctime': inode.ctime,
        }

    def sys_mkdir(self, pid: int, path: str, mode: int) -> int:
        """Create directory"""
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        success = self.vfs.mkdir(path, mode, process.euid, process.egid, process.cwd)
        return 0 if success else -1

    def sys_unlink(self, pid: int, path: str) -> int:
        """Remove file or directory"""
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        success = self.vfs.unlink(path, process.cwd)
        return 0 if success else -1

    def sys_readdir(self, pid: int, path: str) -> Optional[List[Tuple[str, int]]]:
        """Read directory contents"""
        process = self.process_manager.get_process(pid)
        if not process:
            return None

        return self.vfs.list_dir(path, process.cwd)

    def sys_chdir(self, pid: int, path: str) -> int:
        """Change working directory"""
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        target_ino = self.vfs._resolve_path(path, process.cwd)
        if target_ino is None:
            return -1

        target_inode = self.vfs.inodes.get(target_ino)
        if not target_inode or not target_inode.is_dir():
            return -1

        # Check execute permission on directory
        if not self.permissions.can_execute(process.euid, target_inode.mode, target_inode.uid, target_inode.gid):
            return -1

        process.cwd = target_ino
        return 0

    def sys_getcwd(self, pid: int) -> Optional[int]:
        """Get current working directory inode"""
        process = self.process_manager.get_process(pid)
        if not process:
            return None

        return process.cwd

    # =========================================================================
    # PROCESS SYSCALLS
    # =========================================================================

    def sys_fork(self, pid: int) -> int:
        """
        Fork process (create child process)

        Returns:
            Child PID in parent, 0 in child, -1 on error
        """
        # Simplified fork - just spawn a new process
        parent = self.process_manager.get_process(pid)
        if not parent:
            return -1

        child_pid = self.process_manager.spawn(
            parent_pid=pid,
            uid=parent.uid,
            gid=parent.gid,
            euid=parent.euid,
            egid=parent.egid,
            command=parent.command,
            args=parent.args,
            cwd=parent.cwd,
            env=parent.env.copy()
        )

        return child_pid if child_pid else -1

    def sys_exec(self, pid: int, path: str, args: List[str], env: Dict[str, str]) -> int:
        """
        Replace process image with new program

        Returns:
            0 on success, -1 on error (on success, never returns)
        """
        process = self.process_manager.get_process(pid)
        if not process:
            return -1

        # Update process info
        process.command = path
        process.args = args
        process.env = env

        return 0

    def sys_exit(self, pid: int, exit_code: int) -> None:
        """Exit process"""
        process = self.process_manager.get_process(pid)
        if process:
            process.exit_code = exit_code
            self.process_manager.kill_process(pid, 15)  # SIGTERM

    def sys_wait(self, pid: int, child_pid: int) -> Tuple[int, int]:
        """
        Wait for child process

        Returns:
            (child_pid, exit_code)
        """
        child = self.process_manager.get_process(child_pid)
        if not child or child.ppid != pid:
            return (-1, -1)

        # In a real system, this would block until child exits
        # For now, return immediately with exit code if available
        if child.exit_code is not None:
            return (child_pid, child.exit_code)

        return (child_pid, 0)

    def sys_kill(self, pid: int, target_pid: int, signal: int) -> int:
        """
        Send signal to process

        Returns:
            0 on success, -1 on error
        """
        success = self.process_manager.kill_process(target_pid, signal)
        return 0 if success else -1

    def sys_getpid(self, pid: int) -> int:
        """Get process ID"""
        return pid

    def sys_getppid(self, pid: int) -> int:
        """Get parent process ID"""
        process = self.process_manager.get_process(pid)
        return process.ppid if process else -1

    def sys_getuid(self, pid: int) -> int:
        """Get real user ID"""
        process = self.process_manager.get_process(pid)
        return process.uid if process else -1

    def sys_getgid(self, pid: int) -> int:
        """Get real group ID"""
        process = self.process_manager.get_process(pid)
        return process.gid if process else -1

    # =========================================================================
    # NETWORK SYSCALLS (Simplified)
    # =========================================================================

    def sys_socket(self, pid: int, domain: int, type: int, protocol: int) -> int:
        """
        Create socket (simplified)

        Returns:
            Socket file descriptor, or -1 on error
        """
        # Create a socket "file" and return FD
        # This is highly simplified
        return -1  # Not implemented yet

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def syscall(self, syscall_num: int, pid: int, *args) -> Any:
        """
        Generic syscall dispatcher

        Args:
            syscall_num: Syscall number from Syscall enum
            pid: Process ID making the syscall
            *args: Syscall arguments

        Returns:
            Syscall result
        """
        if syscall_num == Syscall.OPEN:
            return self.sys_open(pid, *args)
        elif syscall_num == Syscall.READ:
            return self.sys_read(pid, *args)
        elif syscall_num == Syscall.WRITE:
            return self.sys_write(pid, *args)
        elif syscall_num == Syscall.CLOSE:
            return self.sys_close(pid, *args)
        elif syscall_num == Syscall.STAT:
            return self.sys_stat(pid, *args)
        elif syscall_num == Syscall.MKDIR:
            return self.sys_mkdir(pid, *args)
        elif syscall_num == Syscall.UNLINK:
            return self.sys_unlink(pid, *args)
        elif syscall_num == Syscall.READDIR:
            return self.sys_readdir(pid, *args)
        elif syscall_num == Syscall.CHDIR:
            return self.sys_chdir(pid, *args)
        elif syscall_num == Syscall.GETCWD:
            return self.sys_getcwd(pid)
        elif syscall_num == Syscall.FORK:
            return self.sys_fork(pid)
        elif syscall_num == Syscall.EXEC:
            return self.sys_exec(pid, *args)
        elif syscall_num == Syscall.EXIT:
            return self.sys_exit(pid, *args)
        elif syscall_num == Syscall.WAIT:
            return self.sys_wait(pid, *args)
        elif syscall_num == Syscall.KILL:
            return self.sys_kill(pid, *args)
        elif syscall_num == Syscall.GETPID:
            return self.sys_getpid(pid)
        elif syscall_num == Syscall.GETPPID:
            return self.sys_getppid(pid)
        elif syscall_num == Syscall.GETUID:
            return self.sys_getuid(pid)
        elif syscall_num == Syscall.GETGID:
            return self.sys_getgid(pid)
        else:
            return -1  # Unknown syscall
