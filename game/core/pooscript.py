"""
PooScript - Safe Python-like scripting language for Poodillion game binaries
Allows players to create and modify executable scripts in the virtual filesystem

PooScript is the heart of Poodillion - it's what makes every command, even the
shell itself, into a modifiable, exploitable, and hackable program!
"""

import ast
from typing import Any, Dict, List, Optional, Tuple
from io import StringIO


class VFSInterface:
    """Safe VFS access for scripts"""

    def __init__(self, vfs, cwd: int, uid: int, gid: int):
        self.vfs = vfs
        self.cwd = cwd
        self.uid = uid
        self.gid = gid

    def list(self, path: str) -> List[str]:
        """List directory contents"""
        entries = self.vfs.list_dir(path, self.cwd)
        if entries is None:
            raise RuntimeError(f"Cannot list directory: {path}")
        return [name for name, _ in entries if name not in ('.', '..')]

    def read(self, path: str) -> str:
        """Read file contents as string"""
        content = self.vfs.read_file(path, self.cwd)
        if content is None:
            raise RuntimeError(f"Cannot read file: {path}")
        return content.decode('utf-8', errors='ignore')

    def read_bytes(self, path: str) -> bytes:
        """Read file contents as bytes"""
        content = self.vfs.read_file(path, self.cwd)
        if content is None:
            raise RuntimeError(f"Cannot read file: {path}")
        return content

    def write(self, path: str, content: str) -> None:
        """Write string to existing file"""
        data = content.encode('utf-8')
        success = self.vfs.write_file(path, data, self.cwd)
        if not success:
            raise RuntimeError(f"Cannot write to file: {path}")

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes to existing file"""
        success = self.vfs.write_file(path, content, self.cwd)
        if not success:
            raise RuntimeError(f"Cannot write to file: {path}")

    def create(self, path: str, mode: int, content: str = "") -> None:
        """Create a new file"""
        data = content.encode('utf-8')
        result = self.vfs.create_file(path, mode, self.uid, self.gid, data, self.cwd)
        if result is None:
            raise RuntimeError(f"Cannot create file: {path}")

    def mkdir(self, path: str, mode: int = 0o755) -> None:
        """Create a directory"""
        success = self.vfs.mkdir(path, mode, self.uid, self.gid, self.cwd)
        if not success:
            raise RuntimeError(f"Cannot create directory: {path}")

    def unlink(self, path: str) -> None:
        """Remove a file or empty directory"""
        success = self.vfs.unlink(path, self.cwd)
        if not success:
            raise RuntimeError(f"Cannot remove: {path}")

    def stat(self, path: str) -> Dict[str, Any]:
        """Get file information"""
        inode = self.vfs.stat(path, self.cwd)
        if inode is None:
            raise RuntimeError(f"Cannot stat file: {path}")
        return {
            'size': inode.size,
            'mode': inode.mode,
            'uid': inode.uid,
            'gid': inode.gid,
            'is_file': inode.is_file(),
            'is_dir': inode.is_dir(),
            'is_symlink': inode.is_symlink(),
            'nlink': inode.nlink,
            'mtime': inode.mtime,
            'atime': inode.atime,
            'ctime': inode.ctime,
        }

    def exists(self, path: str) -> bool:
        """Check if path exists"""
        return self.vfs.stat(path, self.cwd) is not None

    def chmod(self, path: str, mode: int) -> None:
        """Change file permissions"""
        inode = self.vfs.stat(path, self.cwd)
        if inode is None:
            raise RuntimeError(f"Cannot chmod: {path} not found")
        # Preserve file type, update permissions
        inode.mode = (inode.mode & 0o170000) | (mode & 0o7777)

    def chown(self, path: str, uid: int, gid: int) -> None:
        """Change file ownership"""
        inode = self.vfs.stat(path, self.cwd)
        if inode is None:
            raise RuntimeError(f"Cannot chown: {path} not found")
        inode.uid = uid
        inode.gid = gid

    def listdetail(self, path: str) -> List[Dict[str, Any]]:
        """List directory with full details"""
        entries = self.vfs.list_dir(path, self.cwd)
        if entries is None:
            raise RuntimeError(f"Cannot list directory: {path}")

        result = []
        for name, ino in entries:
            if name in ('.', '..'):
                continue
            inode = self.vfs.inodes.get(ino)
            if inode:
                result.append({
                    'name': name,
                    'ino': ino,
                    'size': inode.size,
                    'mode': inode.mode,
                    'uid': inode.uid,
                    'gid': inode.gid,
                    'is_file': inode.is_file(),
                    'is_dir': inode.is_dir(),
                    'is_symlink': inode.is_symlink(),
                    'nlink': inode.nlink,
                    'mtime': inode.mtime,
                    'atime': inode.atime,
                    'ctime': inode.ctime,
                })
        return result

    def getcwd(self) -> str:
        """Get current working directory as path"""
        return self._inode_to_path(self.cwd)

    def _inode_to_path(self, ino: int, visited=None) -> str:
        """Convert inode to path"""
        if ino == 1:
            return '/'

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


class NetworkInterface:
    """Safe network access for scripts"""

    def __init__(self, network, local_ip):
        self.network = network
        self.local_ip = local_ip

    def get_local_ip(self) -> str:
        """Get local IP address"""
        return self.local_ip

    def can_reach(self, target_ip: str, port: int = 0) -> bool:
        """Check if we can reach a target IP"""
        if not self.network:
            return False
        return self.network.can_connect(self.local_ip, target_ip, port)

    def scan_network(self, subnet: str) -> List[str]:
        """Scan network for hosts"""
        if not self.network:
            return []
        return self.network.scan_network(self.local_ip, subnet)

    def port_scan(self, target_ip: str) -> List[int]:
        """Scan ports on target"""
        if not self.network:
            return []
        return self.network.port_scan(self.local_ip, target_ip)

    def get_route(self, target_ip: str) -> Optional[str]:
        """Get route to target (returns gateway or None)"""
        if not self.network:
            return None
        if self.can_reach(target_ip):
            return target_ip
        return None

    def http_get(self, url: str) -> str:
        """
        HTTP GET request
        Returns the response body as a string

        Args:
            url: Full URL (http://host/path) or just path if host implied

        Returns:
            Response body as string, or empty string on error
        """
        if not self.network:
            return ""

        # Parse URL
        if url.startswith('http://'):
            # Full URL: http://host/path
            url = url[7:]  # Remove http://
            if '/' in url:
                host, path = url.split('/', 1)
                path = '/' + path
            else:
                host = url
                path = '/'
        elif url.startswith('https://'):
            # HTTPS not supported in 1990!
            return ""
        else:
            # Just a path, no host specified
            # This shouldn't happen in pooget but handle gracefully
            return ""

        # Resolve hostname to IP if needed
        target_ip = host
        if not self._is_ip_address(host):
            # Try to resolve hostname via network
            target_ip = self.network.resolve_hostname(host) if hasattr(self.network, 'resolve_hostname') else None
            if not target_ip:
                # Try looking it up in the systems
                for ip, system in self.network.systems.items():
                    if system.hostname == host:
                        target_ip = ip
                        break
                if not target_ip or not self._is_ip_address(target_ip):
                    return ""

        # Check if we can reach the target
        if not self.can_reach(target_ip, 80):
            return ""

        # Get target system
        target_system = self.network.systems.get(target_ip)
        if not target_system:
            return ""

        # Send HTTP GET request
        # Look for the file in the target's VFS
        try:
            # HTTP servers typically serve from /www/ or /var/www/
            # Try both locations
            for www_root in ['/www', '/var/www']:
                file_path = www_root + path

                # If path ends with /, try default files
                paths_to_try = [file_path]
                if path.endswith('/'):
                    paths_to_try.extend([
                        file_path + 'index.html',
                        file_path + 'default.html',
                        file_path + 'default.bbs',
                        file_path + 'index.bbs',
                        file_path[:-1] + '.html',
                        file_path[:-1] + '.bbs',
                    ])

                for try_path in paths_to_try:
                    try:
                        content = target_system.vfs.read_file(try_path, 1)  # Read as root
                        if content is not None:
                            return content.decode('utf-8', errors='ignore')
                    except (RuntimeError, FileNotFoundError):
                        # File doesn't exist, try next
                        continue

            # File not found in any location
            return ""

        except Exception as e:
            # Error reading file
            return ""

    def _is_ip_address(self, s: str) -> bool:
        """Check if string is an IP address"""
        parts = s.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False


class SystemInterface:
    """Safe system access for scripts (firewall, routing, etc)"""

    def __init__(self, system):
        self._system = system
        self.hostname = system.hostname
        self.local_ip = system.ip
        self.interfaces = system.interfaces
        self.firewall_rules = system.firewall_rules
        self.routing_table = system.routing_table
        self.default_gateway = getattr(system, 'default_gateway', None)
        self.ip_forward = system.ip_forward

    def add_firewall_rule(self, rule: dict) -> None:
        """Add a firewall rule"""
        self._system.firewall_rules.append(rule)

    def clear_firewall_rules(self) -> None:
        """Clear all firewall rules"""
        self._system.firewall_rules.clear()

    def add_route(self, route: dict) -> None:
        """Add a routing table entry"""
        self._system.routing_table.append(route)

    def set_default_gateway(self, gateway: str) -> None:
        """Set default gateway"""
        self._system.default_gateway = gateway

    def shutdown(self) -> None:
        """Gracefully shutdown the system"""
        self._system.shutdown()

    def crash(self) -> None:
        """Simulate a system crash"""
        self._system.crash()

    def is_alive(self) -> bool:
        """Check if system is running"""
        return self._system.is_alive()


class KernelInterface:
    """Low-level kernel syscall interface for scripts"""

    def __init__(self, kernel, pid: int):
        """
        Initialize kernel interface

        Args:
            kernel: Kernel instance (from core.kernel)
            pid: Process ID making syscalls
        """
        self._kernel = kernel
        self._pid = pid

    # File operations
    def open(self, path: str, flags: int = 0, mode: int = 0o644) -> int:
        """Open file and return file descriptor"""
        return self._kernel.sys_open(self._pid, path, flags, mode)

    def read(self, fd: int, count: int) -> bytes:
        """Read from file descriptor"""
        result = self._kernel.sys_read(self._pid, fd, count)
        return result if result is not None else b''

    def write(self, fd: int, data: bytes) -> int:
        """Write to file descriptor"""
        return self._kernel.sys_write(self._pid, fd, data)

    def close(self, fd: int) -> int:
        """Close file descriptor"""
        return self._kernel.sys_close(self._pid, fd)

    def stat(self, path: str) -> dict:
        """Get file status"""
        result = self._kernel.sys_stat(self._pid, path)
        if result is None:
            raise RuntimeError(f"stat: {path}: No such file or directory")
        return result

    # Directory operations
    def mkdir(self, path: str, mode: int = 0o755) -> int:
        """Create directory"""
        return self._kernel.sys_mkdir(self._pid, path, mode)

    def unlink(self, path: str) -> int:
        """Remove file or directory"""
        return self._kernel.sys_unlink(self._pid, path)

    def readdir(self, path: str) -> list:
        """Read directory contents"""
        result = self._kernel.sys_readdir(self._pid, path)
        if result is None:
            raise RuntimeError(f"readdir: {path}: No such file or directory")
        return result

    def chdir(self, path: str) -> int:
        """Change working directory"""
        return self._kernel.sys_chdir(self._pid, path)

    def getcwd(self) -> int:
        """Get current working directory inode"""
        result = self._kernel.sys_getcwd(self._pid)
        return result if result is not None else 1

    # Process operations
    def fork(self) -> int:
        """Fork process"""
        return self._kernel.sys_fork(self._pid)

    def exec(self, path: str, args: list, env: dict) -> int:
        """Execute program"""
        return self._kernel.sys_exec(self._pid, path, args, env)

    def exit(self, code: int = 0) -> None:
        """Exit process"""
        self._kernel.sys_exit(self._pid, code)
        raise SystemExit(code)

    def wait(self, child_pid: int) -> tuple:
        """Wait for child process"""
        return self._kernel.sys_wait(self._pid, child_pid)

    def kill(self, target_pid: int, signal: int = 15) -> int:
        """Send signal to process"""
        return self._kernel.sys_kill(self._pid, target_pid, signal)

    def getpid(self) -> int:
        """Get process ID"""
        return self._pid

    def getppid(self) -> int:
        """Get parent process ID"""
        return self._kernel.sys_getppid(self._pid)

    def getuid(self) -> int:
        """Get real user ID"""
        return self._kernel.sys_getuid(self._pid)

    def getgid(self) -> int:
        """Get real group ID"""
        return self._kernel.sys_getgid(self._pid)

    # Constants for open() flags
    O_RDONLY = 0
    O_WRONLY = 1
    O_RDWR = 2
    O_CREAT = 0x100
    O_APPEND = 0x200
    O_TRUNC = 0x400


class ProcessInterface:
    """Safe process access for scripts"""

    def __init__(self, process, process_manager, shell_executor, network_interface=None, system_interface=None):
        self.uid = process.uid
        self.gid = process.gid
        self.euid = process.euid
        self.egid = process.egid
        self.cwd = process.cwd
        self.pid = process.pid
        self._process = process
        self._process_manager = process_manager
        self._shell_executor = shell_executor
        self._network_interface = network_interface
        self._system_interface = system_interface

    def spawn(self, command: str, args: List[str], env: Dict[str, str]) -> int:
        """
        Spawn a new process
        Returns PID of spawned process
        """
        pid = self._process_manager.spawn(
            parent_pid=self.pid,
            uid=self.euid,  # Use effective UID
            gid=self.egid,  # Use effective GID
            euid=self.euid,
            egid=self.egid,
            command=command,
            args=args,
            cwd=self.cwd,
            env=env,
            tags=[]
        )
        if pid is None:
            raise RuntimeError(f"Failed to spawn process: {command}")
        return pid

    def execute(self, command: str, input_data: str = "") -> Tuple[int, str, str]:
        """
        Execute a command and return (exit_code, stdout, stderr)
        This is a higher-level API that uses the shell executor
        """
        from core.shell import ShellParser, Pipeline, Command

        # Parse command
        parser = ShellParser()
        try:
            pipeline = parser.parse_pipeline(command)
        except Exception as e:
            return 1, "", f"Parse error: {e}"

        # Execute
        input_bytes = input_data.encode('utf-8')
        exit_code, stdout, stderr = self._shell_executor.execute_pipeline(
            pipeline, self.pid, input_bytes
        )

        return exit_code, stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')

    def wait(self, pid: int) -> int:
        """
        Wait for a process to complete
        Returns exit code
        """
        child = self._process_manager.get_process(pid)
        if not child:
            raise RuntimeError(f"Process {pid} not found")

        # In a real implementation, this would block
        # For now, return exit code if available
        if child.exit_code is not None:
            return child.exit_code
        return 0

    def kill(self, pid: int, signal: int = 15) -> None:
        """
        Send signal to a process
        signal: 9=SIGKILL, 15=SIGTERM
        """
        success = self._process_manager.kill_process(pid, signal)
        if not success:
            raise RuntimeError(f"Cannot kill process {pid}")

    def list_all(self) -> List[Dict[str, Any]]:
        """List all running processes"""
        processes = self._process_manager.list_processes()
        result = []
        for p in processes:
            result.append({
                'pid': p.pid,
                'ppid': p.ppid,
                'uid': p.uid,
                'gid': p.gid,
                'command': p.command,
                'args': p.args,
                'state': p.state.value,
            })
        return result

    def getpid(self) -> int:
        """Get current process PID"""
        return self.pid

    def getppid(self) -> int:
        """Get parent process PID"""
        return self._process.ppid

    def chdir(self, path: str) -> None:
        """Change current working directory"""
        # Resolve path
        target_ino = self._shell_executor.vfs._resolve_path(path, self.cwd)
        if target_ino is None:
            raise RuntimeError(f"chdir: {path}: No such file or directory")

        target_inode = self._shell_executor.vfs.inodes.get(target_ino)
        if not target_inode or not target_inode.is_dir():
            raise RuntimeError(f"chdir: {path}: Not a directory")

        # Update process cwd
        self._process.cwd = target_ino
        self.cwd = target_ino

    def getcwd_path(self) -> str:
        """Get current working directory as path"""
        # Use the VFS interface's method
        from core.vfs import VFS
        vfs = self._shell_executor.vfs

        def inode_to_path(ino: int, visited=None) -> str:
            """Convert inode to path"""
            if ino == 1:
                return '/'

            if visited is None:
                visited = set()

            if ino in visited:
                return '???'

            visited.add(ino)

            # Search all directories for this inode
            for parent_ino, parent_inode in vfs.inodes.items():
                if not parent_inode.is_dir():
                    continue

                entries = parent_inode.content
                if not isinstance(entries, dict):
                    continue

                for name, child_ino in entries.items():
                    if child_ino == ino and name not in ('.', '..'):
                        parent_path = inode_to_path(parent_ino, visited)
                        if parent_path == '/':
                            return f'/{name}'
                        return f'{parent_path}/{name}'

            return '???'

        return inode_to_path(self.cwd)

    def get_network(self) -> Optional['NetworkInterface']:
        """Get network interface"""
        return self._network_interface

    def get_system(self) -> Optional['SystemInterface']:
        """Get system interface for configuration"""
        return self._system_interface


class PooScriptInterpreter:
    """
    Safe Python subset interpreter for PooScript
    Supports: variables, if/elif/else, for loops, while loops, basic operations
    Restricted: no imports, no exec, no eval, no file I/O outside VFS
    """

    def __init__(self):
        # Allowed AST node types for safety
        self.allowed_nodes = {
            ast.Module, ast.Expr, ast.Assign, ast.AugAssign,
            ast.If, ast.For, ast.While, ast.Break, ast.Continue,
            ast.FunctionDef, ast.Return, ast.Pass,
            ast.Try, ast.ExceptHandler, ast.Raise,  # Exception handling
            # Expressions
            ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
            ast.Name, ast.Constant, ast.Num, ast.Str, ast.List, ast.Dict, ast.Tuple,
            ast.Subscript, ast.Index, ast.Slice,
            ast.Call, ast.Attribute, ast.keyword,  # keyword for keyword arguments
            ast.IfExp,  # Ternary operator (a if cond else b)
            ast.JoinedStr, ast.FormattedValue,  # f-strings
            ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp,  # Comprehensions
            ast.comprehension,  # comprehension node for list/dict/set comprehensions
            ast.Lambda,  # Lambda functions
            ast.arguments, ast.arg,  # Function arguments
            # Operators
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
            ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
            ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.In, ast.NotIn, ast.Is, ast.IsNot,
            ast.UAdd, ast.USub, ast.Invert,
            # Store/Load contexts
            ast.Store, ast.Load, ast.Del,
        }

        # Built-in functions available to scripts
        self.builtins = {
            'print': self._builtin_print,
            'error': self._builtin_error,
            'exit': self._builtin_exit,
            'input': self._builtin_input,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'min': min,
            'max': max,
            'sum': sum,
            'sorted': sorted,
            'reversed': reversed,
        }

        # Callbacks for interactive I/O
        self.input_callback = None
        self.output_callback = None
        self.error_callback = None

    def _builtin_print(self, *args, **kwargs):
        """Built-in print function - writes to stdout buffer"""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        output = text + end

        # Write to buffer
        self.stdout.write(output)

        # If we have an output callback, flush immediately
        if self.output_callback:
            self.output_callback(output)

    def _builtin_error(self, *args, **kwargs):
        """Built-in error function - writes to stderr buffer"""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        output = text + end

        # Write to buffer
        self.stderr.write(output)

        # If we have an error callback, flush immediately
        if self.error_callback:
            self.error_callback(output)

    def _builtin_exit(self, code=0):
        """Built-in exit function - raises special exception"""
        raise SystemExit(code)

    def _builtin_input(self, prompt=''):
        """Built-in input function - reads from interactive input"""
        if self.input_callback:
            return self.input_callback(prompt)
        else:
            # No callback, return empty string
            return ''

    def _validate_ast(self, node):
        """Recursively validate AST to ensure only safe operations"""
        node_type = type(node)

        if node_type not in self.allowed_nodes:
            raise SyntaxError(f"Operation not allowed: {node_type.__name__}")

        # Recursively check child nodes
        for child in ast.walk(node):
            if type(child) not in self.allowed_nodes:
                raise SyntaxError(f"Operation not allowed: {type(child).__name__}")

    def execute(self, script: str, args: List[str], stdin: str, env: Dict[str, str],
                vfs, process, process_manager=None, shell_executor=None,
                input_callback=None, network=None, local_ip=None, kernel=None) -> Tuple[int, bytes, bytes]:
        """
        Execute a PooScript

        Args:
            script: The script code
            args: Command line arguments
            stdin: Standard input as string
            env: Environment variables
            vfs: VFS instance
            process: Process object
            process_manager: ProcessManager instance (optional)
            shell_executor: ShellExecutor instance (optional)
            network: Virtual network instance (optional)
            local_ip: Local IP address (optional)
            kernel: Kernel instance for syscalls (optional)

        Returns:
            (exit_code, stdout, stderr) as bytes
        """
        # Setup I/O buffers
        self.stdout = StringIO()
        self.stderr = StringIO()

        # Setup callbacks
        self.input_callback = input_callback
        # Output callbacks will be set by the executor

        # Setup execution environment
        vfs_interface = VFSInterface(vfs, process.cwd, process.euid, process.egid)

        # Setup network interface if available
        network_interface = None
        if network and local_ip:
            network_interface = NetworkInterface(network, local_ip)

        # Setup system interface if available
        system_interface = None
        if shell_executor and hasattr(shell_executor, 'system'):
            system_interface = SystemInterface(shell_executor.system)

        process_interface = ProcessInterface(process, process_manager, shell_executor, network_interface, system_interface)

        # Setup kernel interface if available
        kernel_interface = None
        if kernel:
            kernel_interface = KernelInterface(kernel, process.pid)

        # Setup shell interface for executing commands
        class ShellInterface:
            """Execute shell commands from PooScript"""
            def __init__(self, proc_interface):
                self._process = proc_interface

            def execute(self, command: str) -> Tuple[int, str, str]:
                """
                Execute a shell command
                Returns: (exit_code, stdout, stderr)
                """
                if not self._process:
                    return 1, "", "No process interface available"
                try:
                    return self._process.execute(command)
                except Exception as e:
                    return 1, "", str(e)

        shell_interface = ShellInterface(process_interface)

        # String utilities for shell scripting
        def split_args(text: str) -> List[str]:
            """Split command line into arguments (simple version)"""
            import shlex
            return shlex.split(text)

        def join_path(*parts: str) -> str:
            """Join path components"""
            result = '/'.join(str(p) for p in parts)
            # Normalize multiple slashes
            while '//' in result:
                result = result.replace('//', '/')
            return result

        def basename(path: str) -> str:
            """Get base name from path"""
            return path.rstrip('/').split('/')[-1] if path else ''

        def dirname(path: str) -> str:
            """Get directory name from path"""
            parts = path.rstrip('/').split('/')[:-1]
            return '/'.join(parts) or '/'

        def format_time(timestamp: float, fmt: str = '%b %d %H:%M') -> str:
            """Format Unix timestamp"""
            import time as time_mod
            return time_mod.strftime(fmt, time_mod.localtime(timestamp))

        def format_mode(mode: int) -> str:
            """Format file mode as permission string (rwxrwxrwx)"""
            perms = ''
            perms += 'r' if mode & 0o400 else '-'
            perms += 'w' if mode & 0o200 else '-'
            perms += 'x' if mode & 0o100 else '-'
            perms += 'r' if mode & 0o040 else '-'
            perms += 'w' if mode & 0o020 else '-'
            perms += 'x' if mode & 0o010 else '-'
            perms += 'r' if mode & 0o004 else '-'
            perms += 'w' if mode & 0o002 else '-'
            perms += 'x' if mode & 0o001 else '-'
            return perms

        def get_filetype_char(mode: int) -> str:
            """Get file type character"""
            if mode & 0o040000:  # Directory
                return 'd'
            elif mode & 0o120000:  # Symlink
                return 'l'
            elif mode & 0o060000:  # Block device
                return 'b'
            elif mode & 0o020000:  # Character device
                return 'c'
            elif mode & 0o010000:  # FIFO
                return 'p'
            elif mode & 0o140000:  # Socket
                return 's'
            else:  # Regular file
                return '-'

        def time() -> float:
            """Get current Unix timestamp"""
            import time as time_mod
            return time_mod.time()

        def time_sleep(seconds: float) -> None:
            """Sleep for specified seconds"""
            import time as time_mod
            time_mod.sleep(seconds)

        # Create namespace for script execution
        namespace = {
            # Built-in functions
            **self.builtins,
            # String utilities
            'split_args': split_args,
            'join_path': join_path,
            'basename': basename,
            'dirname': dirname,
            'format_time': format_time,
            'format_mode': format_mode,
            'get_filetype_char': get_filetype_char,
            'time': time,
            'time_sleep': time_sleep,
            # Alias for sleep
            'sleep': time_sleep,
            # Built-in objects
            'args': args,
            'stdin': stdin,
            'vfs': vfs_interface,
            'env': env,
            'process': process_interface,
            'kernel': kernel_interface,  # Low-level syscall interface
            'net': network_interface,      # Network interface with http_get()
            'shell': shell_interface,      # Shell command execution
        }

        try:
            # Parse script into AST
            tree = ast.parse(script, mode='exec')

            # Validate AST for safety
            self._validate_ast(tree)

            # Compile and execute
            code = compile(tree, '<pooscript>', 'exec')
            exec(code, namespace)

            # Normal exit
            exit_code = 0

        except SystemExit as e:
            # Script called exit()
            exit_code = e.code if isinstance(e.code, int) else 0

        except SyntaxError as e:
            # Script has syntax error
            self.stderr.write(f"Syntax error: {e}\n")
            exit_code = 1

        except Exception as e:
            # Runtime error
            self.stderr.write(f"Runtime error: {type(e).__name__}: {e}\n")
            exit_code = 1

        # Get output
        stdout_data = self.stdout.getvalue().encode('utf-8')
        stderr_data = self.stderr.getvalue().encode('utf-8')

        return exit_code, stdout_data, stderr_data


def is_pooscript(content: bytes) -> bool:
    """Check if file content is a PooScript (starts with shebang)"""
    if not content:
        return False

    lines = content.split(b'\n', 1)
    if not lines:
        return False

    first_line = lines[0].strip()
    return first_line in (b'#!/usr/bin/pooscript', b'#!/bin/pooscript')


def execute_pooscript(content: bytes, args: List[str], stdin: bytes,
                      env: Dict[str, str], vfs, process,
                      process_manager=None, shell_executor=None, input_callback=None,
                      output_callback=None, error_callback=None, network=None, local_ip=None, kernel=None) -> Tuple[int, bytes, bytes]:
    """Execute a PooScript binary"""
    # Remove shebang
    lines = content.split(b'\n', 1)
    if len(lines) > 1:
        script = lines[1].decode('utf-8', errors='ignore')
    else:
        script = ''

    # Convert stdin to string
    stdin_str = stdin.decode('utf-8', errors='ignore')

    # Execute
    interpreter = PooScriptInterpreter()

    # Set output callbacks for real-time flushing
    interpreter.output_callback = output_callback
    interpreter.error_callback = error_callback

    return interpreter.execute(script, args, stdin_str, env, vfs, process,
                              process_manager, shell_executor, input_callback, network, local_ip, kernel)
