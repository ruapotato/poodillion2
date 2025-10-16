"""
Shell command parser and executor
Supports pipes, redirects, variables, job control
"""

import shlex
import re
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from io import BytesIO


@dataclass
class Command:
    """Parsed command"""
    executable: str
    args: List[str]
    stdin_redirect: Optional[str] = None  # File to redirect stdin from
    stdout_redirect: Optional[str] = None  # File to redirect stdout to
    stderr_redirect: Optional[str] = None  # File to redirect stderr to
    append_stdout: bool = False  # Use >> instead of >
    background: bool = False  # Run in background (&)


@dataclass
class Pipeline:
    """Pipeline of commands connected by pipes"""
    commands: List[Command]


class ShellParser:
    """Parse shell command lines"""

    def __init__(self):
        self.variables: Dict[str, str] = {}

    def set_variable(self, name: str, value: str):
        """Set shell variable"""
        self.variables[name] = value

    def expand_variables(self, text: str) -> str:
        """Expand $VAR and ${VAR} in text"""
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            return self.variables.get(var_name, '')

        # Handle ${VAR} and $VAR
        text = re.sub(r'\$\{(\w+)\}|\$(\w+)', replace_var, text)
        return text

    def tokenize(self, line: str) -> List[str]:
        """
        Tokenize command line, handling quotes and escapes
        """
        # Expand variables first
        line = self.expand_variables(line)

        # Use shlex for proper shell-like tokenization
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError:
            # Fallback for malformed input
            tokens = line.split()

        return tokens

    def parse_command(self, tokens: List[str]) -> Command:
        """Parse a single command with redirects"""
        if not tokens:
            raise ValueError("Empty command")

        executable = tokens[0]
        args = []
        stdin_redirect = None
        stdout_redirect = None
        stderr_redirect = None
        append_stdout = False
        background = False

        i = 1
        while i < len(tokens):
            token = tokens[i]

            if token == '<':
                # Stdin redirect
                if i + 1 >= len(tokens):
                    raise ValueError("Expected filename after <")
                stdin_redirect = tokens[i + 1]
                i += 2
            elif token == '>':
                # Stdout redirect
                if i + 1 >= len(tokens):
                    raise ValueError("Expected filename after >")
                stdout_redirect = tokens[i + 1]
                append_stdout = False
                i += 2
            elif token == '>>':
                # Stdout append
                if i + 1 >= len(tokens):
                    raise ValueError("Expected filename after >>")
                stdout_redirect = tokens[i + 1]
                append_stdout = True
                i += 2
            elif token == '2>':
                # Stderr redirect
                if i + 1 >= len(tokens):
                    raise ValueError("Expected filename after 2>")
                stderr_redirect = tokens[i + 1]
                i += 2
            elif token == '&>':
                # Both stdout and stderr
                if i + 1 >= len(tokens):
                    raise ValueError("Expected filename after &>")
                stdout_redirect = tokens[i + 1]
                stderr_redirect = tokens[i + 1]
                i += 2
            elif token == '&':
                # Background job
                background = True
                i += 1
            else:
                args.append(token)
                i += 1

        return Command(
            executable=executable,
            args=args,
            stdin_redirect=stdin_redirect,
            stdout_redirect=stdout_redirect,
            stderr_redirect=stderr_redirect,
            append_stdout=append_stdout,
            background=background
        )

    def parse_pipeline(self, line: str) -> Pipeline:
        """
        Parse a command line into a pipeline
        Handles pipes (|) between commands
        """
        line = line.strip()
        if not line:
            raise ValueError("Empty command line")

        # Check for variable assignment (VAR=value)
        if '=' in line and not any(c in line for c in ['|', '<', '>', ' ']):
            parts = line.split('=', 1)
            if len(parts) == 2 and parts[0].isidentifier():
                self.set_variable(parts[0], parts[1])
                # Return empty pipeline to signal variable assignment
                return Pipeline(commands=[])

        # Split by pipes, but be careful with quotes
        pipe_parts = []
        current = []
        tokens = self.tokenize(line)

        for token in tokens:
            if token == '|':
                if current:
                    pipe_parts.append(current)
                current = []
            else:
                current.append(token)

        if current:
            pipe_parts.append(current)

        # Parse each part as a command
        commands = []
        for part in pipe_parts:
            if part:
                cmd = self.parse_command(part)
                commands.append(cmd)

        return Pipeline(commands=commands)


class ShellExecutor:
    """Execute parsed commands"""

    def __init__(self, vfs, permissions, processes):
        """
        Args:
            vfs: VFS instance
            permissions: PermissionSystem instance
            processes: ProcessManager instance
        """
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes
        self.builtins: Dict[str, Callable] = {}
        self.commands: Dict[str, Callable] = {}
        self.path_dirs = ['/bin', '/usr/bin', '/sbin', '/usr/sbin']

    def register_builtin(self, name: str, func: Callable):
        """Register a shell builtin command"""
        self.builtins[name] = func

    def register_command(self, name: str, func: Callable):
        """Register an executable command"""
        self.commands[name] = func

    def find_binary(self, name: str, cwd: int) -> Optional[str]:
        """
        Check if a binary exists in PATH
        Returns binary path if found, None otherwise
        """
        for path_dir in self.path_dirs:
            binary_path = f'{path_dir}/{name}'
            inode = self.vfs.stat(binary_path, cwd)
            if inode:
                return binary_path
        return None

    def execute_pipeline(self, pipeline: Pipeline, current_pid: int, input_data: bytes = b'') -> Tuple[int, bytes, bytes]:
        """
        Execute a pipeline of commands
        Returns (exit_code, stdout, stderr)
        """
        if not pipeline.commands:
            return 0, b'', b''

        # For single commands, execute directly
        if len(pipeline.commands) == 1:
            return self.execute_command(pipeline.commands[0], current_pid, input_data)

        # For pipelines, chain commands
        current_input = input_data
        for i, command in enumerate(pipeline.commands):
            is_last = i == len(pipeline.commands) - 1

            exit_code, stdout, stderr = self.execute_command(command, current_pid, current_input)

            if not is_last:
                # Pass stdout to next command
                current_input = stdout
            else:
                # Last command, return results
                return exit_code, stdout, stderr

        return 0, b'', b''

    def execute_command(self, command: Command, current_pid: int, input_data: bytes = b'') -> Tuple[int, bytes, bytes]:
        """
        Execute a single command
        Returns (exit_code, stdout, stderr)
        """
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Handle stdin redirect
        if command.stdin_redirect:
            file_content = self.vfs.read_file(command.stdin_redirect, process.cwd)
            if file_content is None:
                return 1, b'', f'Cannot open {command.stdin_redirect}\n'.encode()
            input_data = file_content

        # Check if it's a builtin (builtins don't need filesystem binaries)
        if command.executable in self.builtins:
            func = self.builtins[command.executable]
            exit_code, stdout, stderr = func(command, current_pid, input_data)
        elif command.executable in self.commands:
            # For regular commands, check if binary exists in filesystem
            binary_path = self.find_binary(command.executable, process.cwd)
            if not binary_path:
                return 127, b'', f'{command.executable}: command not found\n'.encode()

            # Check execute permissions
            binary_inode = self.vfs.stat(binary_path, process.cwd)
            if not binary_inode:
                return 127, b'', f'{command.executable}: command not found\n'.encode()

            if not self.permissions.can_execute(process.uid, binary_inode.mode,
                                               binary_inode.uid, binary_inode.gid):
                return 126, b'', f'{command.executable}: Permission denied\n'.encode()

            func = self.commands[command.executable]
            exit_code, stdout, stderr = func(command, current_pid, input_data)
        else:
            return 127, b'', f'{command.executable}: command not found\n'.encode()

        # Handle stdout redirect
        if command.stdout_redirect:
            if command.append_stdout:
                # Append mode
                existing = self.vfs.read_file(command.stdout_redirect, process.cwd) or b''
                self.vfs.write_file(command.stdout_redirect, existing + stdout, process.cwd)
            else:
                # Overwrite mode
                inode = self.vfs.stat(command.stdout_redirect, process.cwd)
                if inode:
                    self.vfs.write_file(command.stdout_redirect, stdout, process.cwd)
                else:
                    # Create new file
                    self.vfs.create_file(command.stdout_redirect, 0o644, process.uid, process.gid, stdout, process.cwd)
            stdout = b''  # Don't return to caller

        # Handle stderr redirect
        if command.stderr_redirect:
            inode = self.vfs.stat(command.stderr_redirect, process.cwd)
            if inode:
                existing = self.vfs.read_file(command.stderr_redirect, process.cwd) or b''
                self.vfs.write_file(command.stderr_redirect, existing + stderr, process.cwd)
            else:
                self.vfs.create_file(command.stderr_redirect, 0o644, process.uid, process.gid, stderr, process.cwd)
            stderr = b''

        return exit_code, stdout, stderr


class Shell:
    """Complete shell implementation"""

    def __init__(self, vfs, permissions, processes):
        self.parser = ShellParser()
        self.executor = ShellExecutor(vfs, permissions, processes)
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

        # Set default variables
        self.parser.set_variable('PATH', '/bin:/usr/bin:/sbin:/usr/sbin')
        self.parser.set_variable('HOME', '/root')
        self.parser.set_variable('USER', 'root')

    def execute(self, line: str, current_pid: int, input_data: bytes = b'') -> Tuple[int, bytes, bytes]:
        """
        Execute a shell command line
        Returns (exit_code, stdout, stderr)
        """
        try:
            pipeline = self.parser.parse_pipeline(line)
            return self.executor.execute_pipeline(pipeline, current_pid, input_data)
        except Exception as e:
            return 1, b'', f'Error: {str(e)}\n'.encode()

    def register_builtin(self, name: str, func: Callable):
        """Register a builtin command"""
        self.executor.register_builtin(name, func)

    def register_command(self, name: str, func: Callable):
        """Register an executable command"""
        self.executor.register_command(name, func)

    def set_variable(self, name: str, value: str):
        """Set shell variable"""
        self.parser.set_variable(name, value)

    def get_variable(self, name: str) -> Optional[str]:
        """Get shell variable"""
        return self.parser.variables.get(name)
