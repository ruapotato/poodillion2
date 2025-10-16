"""
User and permission management
Unix-style users, groups, and permission checking
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class User:
    """Unix user account"""
    uid: int
    username: str
    gid: int  # Primary group
    home: str
    shell: str
    password_hash: Optional[str] = None  # Simple hash for game purposes
    groups: Set[int] = field(default_factory=set)  # Additional groups


@dataclass
class Group:
    """Unix group"""
    gid: int
    name: str
    members: Set[int] = field(default_factory=set)  # User IDs


class PermissionSystem:
    """Manage users, groups, and permission checks"""

    def __init__(self):
        self.users: Dict[int, User] = {}
        self.groups: Dict[int, Group] = {}
        self.username_map: Dict[str, int] = {}
        self.groupname_map: Dict[str, int] = {}

        # Create root user and group
        self.add_user(0, 'root', 0, '/root', '/bin/sh', password='root')
        self.add_group(0, 'root')

        # Create standard groups
        self.add_group(1, 'daemon')
        self.add_group(2, 'bin')
        self.add_group(3, 'sys')
        self.add_group(4, 'adm')
        self.add_group(10, 'wheel')  # Admin group
        self.add_group(100, 'users')

    def add_user(self, uid: int, username: str, gid: int, home: str, shell: str,
                 password: Optional[str] = None) -> bool:
        """Add a new user"""
        if uid in self.users or username in self.username_map:
            return False

        # Simple password "hash" - just prepend 'H:' for game purposes
        # In a real system, you'd use proper hashing
        password_hash = f'H:{password}' if password else None

        user = User(
            uid=uid,
            username=username,
            gid=gid,
            home=home,
            shell=shell,
            password_hash=password_hash
        )

        self.users[uid] = user
        self.username_map[username] = uid
        return True

    def add_group(self, gid: int, name: str) -> bool:
        """Add a new group"""
        if gid in self.groups or name in self.groupname_map:
            return False

        group = Group(gid=gid, name=name)
        self.groups[gid] = group
        self.groupname_map[name] = gid
        return True

    def add_user_to_group(self, uid: int, gid: int) -> bool:
        """Add user to a group"""
        if uid not in self.users or gid not in self.groups:
            return False

        user = self.users[uid]
        group = self.groups[gid]

        user.groups.add(gid)
        group.members.add(uid)
        return True

    def get_user_by_name(self, username: str) -> Optional[User]:
        """Get user by username"""
        uid = self.username_map.get(username)
        return self.users.get(uid) if uid is not None else None

    def get_user(self, uid: int) -> Optional[User]:
        """Get user by UID"""
        return self.users.get(uid)

    def get_group(self, gid: int) -> Optional[Group]:
        """Get group by GID"""
        return self.groups.get(gid)

    def get_group_by_name(self, name: str) -> Optional[Group]:
        """Get group by name"""
        gid = self.groupname_map.get(name)
        return self.groups.get(gid) if gid is not None else None

    def check_password(self, username: str, password: str) -> bool:
        """Check if password is correct for user"""
        user = self.get_user_by_name(username)
        if not user or not user.password_hash:
            return False

        # Simple check - compare with "hash"
        return user.password_hash == f'H:{password}'

    def has_permission(self, uid: int, inode_mode: int, inode_uid: int, inode_gid: int,
                       need_read: bool = False, need_write: bool = False, need_exec: bool = False) -> bool:
        """
        Check if user has permission to access an inode

        Args:
            uid: User ID requesting access
            inode_mode: File mode (includes type and permissions)
            inode_uid: File owner UID
            inode_gid: File owner GID
            need_read: Need read permission
            need_write: Need write permission
            need_exec: Need execute permission
        """
        # Root can do anything
        if uid == 0:
            return True

        user = self.users.get(uid)
        if not user:
            return False

        perms = inode_mode & 0o777

        # Determine which permission bits to check
        if uid == inode_uid:
            # Owner permissions
            shift = 6
        elif inode_gid == user.gid or inode_gid in user.groups:
            # Group permissions
            shift = 3
        else:
            # Other permissions
            shift = 0

        mode_bits = (perms >> shift) & 7

        if need_read and not (mode_bits & 4):
            return False
        if need_write and not (mode_bits & 2):
            return False
        if need_exec and not (mode_bits & 1):
            return False

        return True

    def can_execute(self, uid: int, inode_mode: int, inode_uid: int, inode_gid: int) -> bool:
        """Check if user can execute a file"""
        return self.has_permission(uid, inode_mode, inode_uid, inode_gid, need_exec=True)

    def can_read(self, uid: int, inode_mode: int, inode_uid: int, inode_gid: int) -> bool:
        """Check if user can read a file"""
        return self.has_permission(uid, inode_mode, inode_uid, inode_gid, need_read=True)

    def can_write(self, uid: int, inode_mode: int, inode_uid: int, inode_gid: int) -> bool:
        """Check if user can write a file"""
        return self.has_permission(uid, inode_mode, inode_uid, inode_gid, need_write=True)

    def is_suid(self, mode: int) -> bool:
        """Check if file has SUID bit set"""
        return bool(mode & 0o4000)

    def is_sgid(self, mode: int) -> bool:
        """Check if file has SGID bit set"""
        return bool(mode & 0o2000)

    def get_effective_uid(self, running_uid: int, file_mode: int, file_uid: int) -> int:
        """Get effective UID when executing a file (handles SUID)"""
        if self.is_suid(file_mode):
            return file_uid
        return running_uid

    def get_effective_gid(self, running_gid: int, file_mode: int, file_gid: int) -> int:
        """Get effective GID when executing a file (handles SGID)"""
        if self.is_sgid(file_mode):
            return file_gid
        return running_gid

    def list_users(self) -> List[User]:
        """List all users"""
        return sorted(self.users.values(), key=lambda u: u.uid)

    def list_groups(self) -> List[Group]:
        """List all groups"""
        return sorted(self.groups.values(), key=lambda g: g.gid)
