"""
Filesystem commands
ls, cat, cd, pwd, mkdir, rm, cp, mv, touch, etc.
"""

import time
import stat as stat_module
from typing import Tuple


class FilesystemCommands:
    """Collection of filesystem commands"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_pwd(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Print working directory"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Reconstruct path from inode
        path = self._inode_to_path(process.cwd)
        return 0, f'{path}\n'.encode(), b''

    def cmd_cd(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Change directory"""
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

    def cmd_ls(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """List directory contents"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        show_all = '-a' in command.args
        long_format = '-l' in command.args

        # Get paths (filter out options)
        paths = [arg for arg in command.args if not arg.startswith('-')]
        if not paths:
            paths = ['.']

        output = []
        for path in paths:
            entries = self.vfs.list_dir(path, process.cwd)
            if entries is None:
                return 1, b'', f'ls: {path}: No such file or directory\n'.encode()

            # Filter hidden files
            if not show_all:
                entries = [(name, ino) for name, ino in entries if not name.startswith('.') or name in ('.', '..')]

            # Sort by name
            entries.sort(key=lambda x: x[0])

            if long_format:
                for name, ino in entries:
                    inode = self.vfs.inodes.get(ino)
                    if inode:
                        output.append(self._format_long_entry(name, inode))
            else:
                for name, ino in entries:
                    output.append(name)

        if long_format:
            return 0, '\n'.join(output).encode() + b'\n', b''
        else:
            return 0, '  '.join(output).encode() + b'\n', b''

    def cmd_cat(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Concatenate and print files"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            # No args, read from stdin
            return 0, input_data, b''

        output = []
        for path in command.args:
            content = self.vfs.read_file(path, process.cwd)
            if content is None:
                return 1, b'', f'cat: {path}: No such file or directory\n'.encode()

            inode = self.vfs.stat(path, process.cwd)
            # Use effective UID for permission checks (supports SUID)
            if inode and not self.permissions.can_read(process.euid, inode.mode, inode.uid, inode.gid):
                return 1, b'', f'cat: {path}: Permission denied\n'.encode()

            output.append(content)

        return 0, b''.join(output), b''

    def cmd_mkdir(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Create directory"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            return 1, b'', b'mkdir: missing operand\n'

        for path in command.args:
            success = self.vfs.mkdir(path, 0o755, process.uid, process.gid, process.cwd)
            if not success:
                return 1, b'', f'mkdir: cannot create directory {path}\n'.encode()

        return 0, b'', b''

    def cmd_touch(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Create empty file or update timestamp"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            return 1, b'', b'touch: missing operand\n'

        for path in command.args:
            # Check if file exists
            inode = self.vfs.stat(path, process.cwd)
            if inode:
                # Update timestamp
                inode.atime = time.time()
                inode.mtime = time.time()
            else:
                # Create new file
                result = self.vfs.create_file(path, 0o644, process.uid, process.gid, b'', process.cwd)
                if result is None:
                    return 1, b'', f'touch: cannot touch {path}\n'.encode()

        return 0, b'', b''

    def cmd_rm(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Remove files or directories"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            return 1, b'', b'rm: missing operand\n'

        recursive = '-r' in command.args or '-rf' in command.args
        force = '-f' in command.args or '-rf' in command.args

        paths = [arg for arg in command.args if not arg.startswith('-')]

        for path in paths:
            success = self.vfs.unlink(path, process.cwd)
            if not success and not force:
                return 1, b'', f'rm: cannot remove {path}\n'.encode()

        return 0, b'', b''

    def cmd_echo(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Echo arguments"""
        output = ' '.join(command.args)
        return 0, output.encode() + b'\n', b''

    def cmd_grep(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Search for pattern in input"""
        if not command.args:
            return 1, b'', b'grep: missing pattern\n'

        pattern = command.args[0]
        case_insensitive = '-i' in command.args

        lines = input_data.decode('utf-8', errors='ignore').splitlines()
        matches = []

        for line in lines:
            if case_insensitive:
                if pattern.lower() in line.lower():
                    matches.append(line)
            else:
                if pattern in line:
                    matches.append(line)

        return 0, '\n'.join(matches).encode() + b'\n' if matches else b'', b''

    def cmd_find(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Find files (simplified version)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Simple find implementation
        start_path = command.args[0] if command.args else '.'
        name_pattern = None

        # Look for -name option
        if '-name' in command.args:
            idx = command.args.index('-name')
            if idx + 1 < len(command.args):
                name_pattern = command.args[idx + 1]

        results = []
        self._find_recursive(start_path, name_pattern, process.cwd, results)

        return 0, '\n'.join(results).encode() + b'\n', b''

    def _find_recursive(self, path: str, name_pattern: str, cwd: int, results: list):
        """Recursive helper for find"""
        entries = self.vfs.list_dir(path, cwd)
        if entries is None:
            return

        for name, ino in entries:
            if name in ('.', '..'):
                continue

            full_path = f'{path}/{name}' if path != '/' else f'/{name}'

            # Check if matches pattern
            if name_pattern is None or name == name_pattern:
                results.append(full_path)

            # Recurse into directories
            inode = self.vfs.inodes.get(ino)
            if inode and inode.is_dir():
                self._find_recursive(full_path, name_pattern, cwd, results)

    def _format_long_entry(self, name: str, inode) -> str:
        """Format entry for ls -l"""
        # Type and permissions
        type_char = inode.get_type_char()
        perms = inode.permission_string()

        # User and group (just show IDs for now)
        user = self.permissions.get_user(inode.uid)
        group = self.permissions.get_group(inode.gid)
        user_name = user.username if user else str(inode.uid)
        group_name = group.name if group else str(inode.gid)

        # Size
        size = inode.size

        # Date (simplified)
        mtime = time.strftime('%b %d %H:%M', time.localtime(inode.mtime))

        return f'{type_char}{perms} {inode.nlink:2} {user_name:8} {group_name:8} {size:8} {mtime} {name}'

    def _inode_to_path(self, ino: int, visited=None) -> str:
        """Convert inode to path (simple version)"""
        if ino == 1:
            return '/'

        # Simple traversal - in production you'd cache this
        if visited is None:
            visited = set()

        if ino in visited:
            return '???'

        visited.add(ino)

        # Search all directories for this inode
        for parent_ino, parent_inode in self.vfs.inodes.items():
            if not parent_inode.is_dir():
                continue

            entries = parent_inode.content
            if not isinstance(entries, dict):
                continue

            for name, child_ino in entries.items():
                if child_ino == ino and name not in ('.', '..'):
                    parent_path = self._inode_to_path(parent_ino, visited)
                    if parent_path == '/':
                        return f'/{name}'
                    return f'{parent_path}/{name}'

        return '???'

    def cmd_chmod(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Change file permissions"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if len(command.args) < 2:
            return 1, b'', b'chmod: missing operand\n'

        mode_str = command.args[0]
        paths = command.args[1:]

        # Parse mode (only support octal for now, e.g., 755)
        try:
            if mode_str.startswith('+') or mode_str.startswith('-'):
                # Symbolic mode (simplified: +x, -x, +w, -w, +r, -r)
                for path in paths:
                    inode = self.vfs.stat(path, process.cwd)
                    if not inode:
                        return 1, b'', f'chmod: {path}: No such file or directory\n'.encode()

                    # Only root or owner can chmod
                    if process.uid != 0 and process.uid != inode.uid:
                        return 1, b'', f'chmod: {path}: Permission denied\n'.encode()

                    current_perms = inode.mode & 0o777
                    if mode_str == '+x':
                        new_perms = current_perms | 0o111  # Add execute for all
                    elif mode_str == '-x':
                        new_perms = current_perms & ~0o111  # Remove execute for all
                    elif mode_str == '+w':
                        new_perms = current_perms | 0o222  # Add write for all
                    elif mode_str == '-w':
                        new_perms = current_perms & ~0o222  # Remove write for all
                    elif mode_str == '+r':
                        new_perms = current_perms | 0o444  # Add read for all
                    elif mode_str == '-r':
                        new_perms = current_perms & ~0o444  # Remove read for all
                    else:
                        return 1, b'', f'chmod: invalid mode: {mode_str}\n'.encode()

                    inode.mode = (inode.mode & ~0o777) | new_perms
                    inode.ctime = time.time()
            else:
                # Octal mode (e.g., 755, 644, 4755 for SUID, 2755 for SGID)
                new_mode = int(mode_str, 8)
                if new_mode > 0o7777:
                    return 1, b'', f'chmod: invalid mode: {mode_str}\n'.encode()

                for path in paths:
                    inode = self.vfs.stat(path, process.cwd)
                    if not inode:
                        return 1, b'', f'chmod: {path}: No such file or directory\n'.encode()

                    # Only root or owner can chmod
                    if process.uid != 0 and process.uid != inode.uid:
                        return 1, b'', f'chmod: {path}: Permission denied\n'.encode()

                    # Preserve file type, update permissions and special bits
                    # Clear old permissions and special bits, set new ones
                    inode.mode = (inode.mode & 0o170000) | (new_mode & 0o7777)
                    inode.ctime = time.time()

        except ValueError:
            return 1, b'', f'chmod: invalid mode: {mode_str}\n'.encode()

        return 0, b'', b''

    def cmd_chown(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Change file ownership"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Only root can chown
        if process.uid != 0:
            return 1, b'', b'chown: Operation not permitted\n'

        if len(command.args) < 2:
            return 1, b'', b'chown: missing operand\n'

        owner_spec = command.args[0]
        paths = command.args[1:]

        # Parse owner:group or just owner
        if ':' in owner_spec:
            owner_str, group_str = owner_spec.split(':', 1)
        else:
            owner_str = owner_spec
            group_str = None

        # Resolve username/UID
        if owner_str.isdigit():
            new_uid = int(owner_str)
        else:
            user = self.permissions.get_user_by_name(owner_str)
            if not user:
                return 1, b'', f'chown: invalid user: {owner_str}\n'.encode()
            new_uid = user.uid

        # Resolve group if specified
        new_gid = None
        if group_str:
            if group_str.isdigit():
                new_gid = int(group_str)
            else:
                group = self.permissions.get_group_by_name(group_str)
                if not group:
                    return 1, b'', f'chown: invalid group: {group_str}\n'.encode()
                new_gid = group.gid

        # Change ownership
        for path in paths:
            inode = self.vfs.stat(path, process.cwd)
            if not inode:
                return 1, b'', f'chown: {path}: No such file or directory\n'.encode()

            inode.uid = new_uid
            if new_gid is not None:
                inode.gid = new_gid
            inode.ctime = time.time()

        return 0, b'', b''

    def cmd_ln(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Create links"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if len(command.args) < 2:
            return 1, b'', b'ln: missing operand\n'

        # Check for -s flag (symbolic link)
        symbolic = '-s' in command.args
        args = [arg for arg in command.args if not arg.startswith('-')]

        if len(args) < 2:
            return 1, b'', b'ln: missing operand\n'

        target = args[0]
        linkpath = args[1]

        if symbolic:
            # Create symbolic link
            success = self.vfs.symlink(target, linkpath, process.uid, process.gid, process.cwd)
            if not success:
                return 1, b'', f'ln: failed to create symbolic link {linkpath}\n'.encode()
        else:
            # Hard links not fully implemented yet
            return 1, b'', b'ln: hard links not yet supported\n'

        return 0, b'', b''

    def cmd_cp(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Copy files"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if len(command.args) < 2:
            return 1, b'', b'cp: missing operand\n'

        # Parse options
        recursive = '-r' in command.args or '-R' in command.args
        paths = [arg for arg in command.args if not arg.startswith('-')]

        if len(paths) < 2:
            return 1, b'', b'cp: missing operand\n'

        source = paths[0]
        dest = paths[1]

        # Get source inode
        source_inode = self.vfs.stat(source, process.cwd)
        if not source_inode:
            return 1, b'', f'cp: {source}: No such file or directory\n'.encode()

        # Check read permission on source
        if not self.permissions.can_read(process.uid, source_inode.mode, source_inode.uid, source_inode.gid):
            return 1, b'', f'cp: {source}: Permission denied\n'.encode()

        # Handle directory copy
        if source_inode.is_dir():
            if not recursive:
                return 1, b'', f'cp: {source}: Is a directory (use -r for recursive copy)\n'.encode()
            else:
                return 1, b'', b'cp: recursive copy not yet implemented\n'

        # Copy file content
        content = self.vfs.read_file(source, process.cwd)
        if content is None:
            return 1, b'', f'cp: {source}: Cannot read file\n'.encode()

        # Check if destination exists
        dest_inode = self.vfs.stat(dest, process.cwd)
        if dest_inode:
            if dest_inode.is_dir():
                # Copy into directory
                source_name = source.rstrip('/').split('/')[-1]
                dest = f'{dest}/{source_name}'

        # Create destination file with source permissions
        result = self.vfs.create_file(dest, source_inode.mode & 0o777, process.uid, process.gid, content, process.cwd)
        if result is None:
            return 1, b'', f'cp: {dest}: Cannot create file\n'.encode()

        return 0, b'', b''

    def cmd_mv(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Move/rename files"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if len(command.args) < 2:
            return 1, b'', b'mv: missing operand\n'

        source = command.args[0]
        dest = command.args[1]

        # Get source inode
        source_inode = self.vfs.stat(source, process.cwd)
        if not source_inode:
            return 1, b'', f'mv: {source}: No such file or directory\n'.encode()

        # Check if destination is a directory
        dest_inode = self.vfs.stat(dest, process.cwd)
        if dest_inode and dest_inode.is_dir():
            # Move into directory
            source_name = source.rstrip('/').split('/')[-1]
            dest = f'{dest}/{source_name}'

        # For simplicity, implement mv as copy + delete
        if source_inode.is_file():
            content = self.vfs.read_file(source, process.cwd)
            if content is None:
                return 1, b'', f'mv: {source}: Cannot read file\n'.encode()

            # Create destination
            result = self.vfs.create_file(dest, source_inode.mode & 0o777, source_inode.uid, source_inode.gid, content, process.cwd)
            if result is None:
                return 1, b'', f'mv: {dest}: Cannot create file\n'.encode()

            # Delete source
            if not self.vfs.unlink(source, process.cwd):
                return 1, b'', f'mv: {source}: Cannot remove source\n'.encode()
        elif source_inode.is_dir():
            # Simple directory move - just update parent directory entry
            # This is simplified - real mv handles cross-filesystem moves differently
            return 1, b'', b'mv: directory move not yet fully implemented\n'
        else:
            return 1, b'', f'mv: {source}: Not a regular file or directory\n'.encode()

        return 0, b'', b''
