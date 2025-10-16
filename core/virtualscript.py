"""
VirtualScript - Safe Python-like scripting language for game binaries
Allows players to create and modify executable scripts in the virtual filesystem
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


class ProcessInterface:
    """Safe process access for scripts"""

    def __init__(self, process, process_manager, shell_executor):
        self.uid = process.uid
        self.gid = process.gid
        self.euid = process.euid
        self.egid = process.egid
        self.cwd = process.cwd
        self.pid = process.pid
        self._process = process
        self._process_manager = process_manager
        self._shell_executor = shell_executor

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


class VirtualScriptInterpreter:
    """
    Safe Python subset interpreter for VirtualScript
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

    def _builtin_print(self, *args, **kwargs):
        """Built-in print function - writes to stdout buffer"""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        self.stdout.write(text + end)

    def _builtin_error(self, *args, **kwargs):
        """Built-in error function - writes to stderr buffer"""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        self.stderr.write(text + end)

    def _builtin_exit(self, code=0):
        """Built-in exit function - raises special exception"""
        raise SystemExit(code)

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
                vfs, process, process_manager=None, shell_executor=None) -> Tuple[int, bytes, bytes]:
        """
        Execute a VirtualScript

        Args:
            script: The script code
            args: Command line arguments
            stdin: Standard input as string
            env: Environment variables
            vfs: VFS instance
            process: Process object
            process_manager: ProcessManager instance (optional)
            shell_executor: ShellExecutor instance (optional)

        Returns:
            (exit_code, stdout, stderr) as bytes
        """
        # Setup I/O buffers
        self.stdout = StringIO()
        self.stderr = StringIO()

        # Setup execution environment
        vfs_interface = VFSInterface(vfs, process.cwd, process.euid, process.egid)
        process_interface = ProcessInterface(process, process_manager, shell_executor)

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

        # Create namespace for script execution
        namespace = {
            # Built-in functions
            **self.builtins,
            # String utilities
            'split_args': split_args,
            'join_path': join_path,
            'basename': basename,
            'dirname': dirname,
            # Built-in objects
            'args': args,
            'stdin': stdin,
            'vfs': vfs_interface,
            'env': env,
            'process': process_interface,
        }

        try:
            # Parse script into AST
            tree = ast.parse(script, mode='exec')

            # Validate AST for safety
            self._validate_ast(tree)

            # Compile and execute
            code = compile(tree, '<virtualscript>', 'exec')
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


def is_virtualscript(content: bytes) -> bool:
    """Check if file content is a VirtualScript (starts with shebang)"""
    if not content:
        return False

    lines = content.split(b'\n', 1)
    if not lines:
        return False

    first_line = lines[0].strip()
    return first_line in (b'#!/usr/bin/virtualscript', b'#!/bin/virtualscript')


def execute_virtualscript(content: bytes, args: List[str], stdin: bytes,
                          env: Dict[str, str], vfs, process,
                          process_manager=None, shell_executor=None) -> Tuple[int, bytes, bytes]:
    """Execute a VirtualScript binary"""
    # Remove shebang
    lines = content.split(b'\n', 1)
    if len(lines) > 1:
        script = lines[1].decode('utf-8', errors='ignore')
    else:
        script = ''

    # Convert stdin to string
    stdin_str = stdin.decode('utf-8', errors='ignore')

    # Execute
    interpreter = VirtualScriptInterpreter()
    return interpreter.execute(script, args, stdin_str, env, vfs, process,
                              process_manager, shell_executor)
