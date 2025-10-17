"""
Shell command parser and executor
Supports pipes, redirects, variables, job control
"""

import shlex
import re
import random
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from io import BytesIO
from core.pooscript import is_pooscript, execute_pooscript


def get_command_not_found_message(command: str) -> str:
    """Generate a fun, personality-filled 'command not found' message"""

    # Easter eggs for specific typos
    easter_eggs = {
        'sl': "Did you mean 'ls'? Or were you trying to ride the Steam Locomotive? choo choo!",
        'cta': "Did you mean 'cat'? Even cats make typos.",
        'pign': "Did you mean 'ping'? Your fingers are doing the QWERTY shuffle!",
        'mroe': "Did you mean 'more'? I can tell you want mroe!",
        'grpe': "Did you mean 'grep'? Don't let your typos grep you!",
        'hotsname': "Did you mean 'hostname'? That's one hot sname!",
        'suod': "Did you mean 'sudo'? SUOD: Super User... Oh Damn!",
        'cd..': "Did you mean 'cd ..'? Space: the final frontier.",
        'quit': "This isn't vim. Try 'exit' instead.",
        'q': "This isn't vim. Try 'exit' instead.",
        ':q': "This isn't vim. Try 'exit' instead.",
        ':wq': "This isn't vim. Try 'exit' instead.",
        'help': "You're in Poodillion. Try 'ls /bin' to see available commands, or just... explore!",
        'man': "There are no manuals here, only mysteries. Try commands and see what happens!",
        'apt': "This ain't Debian! But I like your style. Try 'ls /bin' instead.",
        'yum': "This ain't RedHat! But yum... Try 'ls /bin' for tasty commands.",
        'brew': "This ain't macOS! But I appreciate the caffeine reference.",
        'hack': "Now we're talking! Try 'nmap', 'ssh', or 'exploit' for actual hacking.",
        'hax': "l33t sp34k detected! Try 'nmap' or 'exploit' for real hax.",
        'python': "You're already IN Python! This whole OS is Python! Mind = blown.",
        'bash': "This IS a shell! You're already bashing! Try some commands.",
        'zsh': "Sorry, we're more of a 'PooshShell' kind of place.",
        'vim': "No vim here. But you can 'cat' files and dream of modal editing.",
        'emacs': "No emacs here. But you can 'cat' files and dream of meta keys.",
        'nano': "No nano here. But you can 'cat' files and pretend you're editing.",
        'please': "Politeness won't help you here. Try 'sudo' if you need power.",
        'sudo please': "Well since you asked nicely... just kidding, still not found!",
        'fuck': "I know you're frustrated. Take a breath. Try 'ls /bin' to see what's available.",
    }

    if command.lower() in easter_eggs:
        return easter_eggs[command.lower()]

    # Different random messages for variety
    messages = [
        f"{command}: command not found (did you make that up?)",
        f"{command}: command not found (nice try though!)",
        f"{command}: command not found (maybe in another universe?)",
        f"{command}: not found (did you mean something else?)",
        f"bash: {command}: command not found (this is classic!)",
        f"{command}: command not found (have you tried turning it off and on again?)",
        f"{command}: not found (try 'ls /bin' to see what's available)",
        f"{command}: command not found (it's not you, it's me... wait, it's you)",
        f"{command}: not found in PATH (or anywhere else for that matter)",
        f"{command}: command not found (404: command not found)",
        f"Error 404: {command} not found (wrong error, right vibe)",
        f"{command}: command not found (are you sure you didn't just slam the keyboard?)",
        f"{command}: not found (maybe it's hiding? try 'find')",
        f"{command}: command not found (spellcheck says: ¯\\_(ツ)_/¯)",
        f"{command}: not found (this command has left the building)",
    ]

    # Add helpful suggestions for common patterns
    if command.startswith('install'):
        return f"{command}: command not found (this is a virtual OS! Everything's already here. Try 'ls /bin')"
    elif command.startswith('download'):
        return f"{command}: command not found (no downloads here! This is a self-contained world)"
    elif len(command) > 30:
        return f"{command}: command not found (that's quite a command! maybe try something shorter?)"
    elif ' ' in command:
        return f"{command}: command not found (are you missing quotes?)"
    elif command.isupper():
        return f"{command}: command not found (STOP YELLING! try lowercase)"

    return random.choice(messages)


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

    def __init__(self, vfs, permissions, processes, network=None, local_ip=None, system=None):
        """
        Args:
            vfs: VFS instance
            permissions: PermissionSystem instance
            processes: ProcessManager instance
            network: VirtualNetwork instance (optional)
            local_ip: Local IP address (optional)
            system: UnixSystem instance (optional, for system configuration)
        """
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes
        self.network = network
        self.local_ip = local_ip
        self.system = system  # Store system reference
        self.builtins: Dict[str, Callable] = {}
        self.commands: Dict[str, Callable] = {}
        self.path_dirs = ['/bin', '/usr/bin', '/sbin', '/usr/sbin', '/usr/local/bin']
        self.input_callback = None  # For interactive shells
        self.output_callback = None  # For real-time output
        self.error_callback = None   # For real-time errors

    def register_builtin(self, name: str, func: Callable):
        """Register a shell builtin command"""
        self.builtins[name] = func

    def register_command(self, name: str, func: Callable):
        """Register an executable command"""
        self.commands[name] = func

    def find_binary(self, name: str, cwd: int) -> Optional[str]:
        """
        Check if a binary exists in PATH or as absolute/relative path
        Returns binary path if found, None otherwise
        """
        # If name contains '/', treat it as a path (absolute or relative)
        if '/' in name:
            inode = self.vfs.stat(name, cwd)
            if inode and inode.is_file():
                return name
            return None

        # Otherwise search in PATH
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
        else:
            # For all other commands, check if binary exists in filesystem
            binary_path = self.find_binary(command.executable, process.cwd)
            if not binary_path:
                error_msg = get_command_not_found_message(command.executable)
                return 127, b'', f'{error_msg}\n'.encode()

            # Check execute permissions
            binary_inode = self.vfs.stat(binary_path, process.cwd)
            if not binary_inode:
                error_msg = get_command_not_found_message(command.executable)
                return 127, b'', f'{error_msg}\n'.encode()

            if not self.permissions.can_execute(process.uid, binary_inode.mode,
                                               binary_inode.uid, binary_inode.gid):
                return 126, b'', f'{command.executable}: Permission denied\n'.encode()

            # Handle SUID/SGID privilege escalation
            original_euid = process.euid
            original_egid = process.egid

            # Check for SUID bit - if set, run with file owner's privileges
            if self.permissions.is_suid(binary_inode.mode):
                process.euid = binary_inode.uid

            # Check for SGID bit - if set, run with file group's privileges
            if self.permissions.is_sgid(binary_inode.mode):
                process.egid = binary_inode.gid

            # Check if binary is a PooScript
            binary_content = self.vfs.read_file(binary_path, process.cwd)
            if binary_content and is_pooscript(binary_content):
                # Execute as PooScript with full system access
                exit_code, stdout, stderr = execute_pooscript(
                    binary_content,
                    command.args,
                    input_data,
                    process.env,
                    self.vfs,
                    process,
                    self.processes,  # Pass process manager
                    self,            # Pass shell executor (self)
                    self.input_callback,  # Pass input callback for interactive shells
                    self.output_callback, # Pass output callback for real-time output
                    self.error_callback,  # Pass error callback for real-time errors
                    self.network,         # Pass network for networking commands
                    self.local_ip,        # Pass local IP address
                    self.system.kernel if self.system else None  # NEW: Pass kernel for syscalls
                )
            elif command.executable in self.commands:
                # Execute as Python command handler
                func = self.commands[command.executable]
                exit_code, stdout, stderr = func(command, current_pid, input_data)
            else:
                # Binary exists but no handler - treat as error
                exit_code, stdout, stderr = 127, b'', f'{command.executable}: not implemented\n'.encode()

            # Restore original effective UID/GID after execution
            process.euid = original_euid
            process.egid = original_egid

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

    def __init__(self, vfs, permissions, processes, network=None, local_ip=None, system=None):
        self.parser = ShellParser()
        self.executor = ShellExecutor(vfs, permissions, processes, network, local_ip, system)
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes
        self.network = network
        self.local_ip = local_ip
        self.system = system

        # Set default variables
        self.parser.set_variable('PATH', '/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin')
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
