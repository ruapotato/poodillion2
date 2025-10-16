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

    def __init__(self):
        self.inodes: Dict[int, Inode] = {}
        self.next_ino = 2  # Start at 2 (1 is reserved for root in real systems)

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

    def read_file(self, path: str, current_dir_ino: int = 1) -> Optional[bytes]:
        """Read file contents"""
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return None

        inode = self.inodes.get(ino)
        if not inode or not inode.is_file():
            return None

        inode.atime = time.time()
        return inode.content if isinstance(inode.content, bytes) else None

    def write_file(self, path: str, content: bytes, current_dir_ino: int = 1) -> bool:
        """Write to existing file"""
        ino = self._resolve_path(path, current_dir_ino)
        if ino is None:
            return False

        inode = self.inodes.get(ino)
        if not inode or not inode.is_file():
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

    def create_device(self, path: str, is_char: bool, uid: int, gid: int, current_dir_ino: int = 1) -> bool:
        """Create a device file"""
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
            content=b''
        )

        self.inodes[new_ino] = new_dev
        entries[name] = new_ino
        parent.mtime = now

        return True
