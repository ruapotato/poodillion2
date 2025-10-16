"""
Additional Unix utility commands
Text viewers, processors, archive tools, network tools, etc.
"""

import time
import base64
import zlib
from typing import Tuple, List


class TextUtilities:
    """Text viewing and processing utilities"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_head(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Display first lines of a file"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        num_lines = 10  # default
        if '-n' in command.args:
            idx = command.args.index('-n')
            if idx + 1 < len(command.args):
                try:
                    num_lines = int(command.args[idx + 1])
                except ValueError:
                    return 1, b'', b'head: invalid number of lines\n'

        # Get files (filter out options)
        files = [arg for arg in command.args if not arg.startswith('-') and not arg.isdigit()]

        if not files:
            # Read from stdin
            lines = input_data.decode('utf-8', errors='ignore').splitlines()
            output = '\n'.join(lines[:num_lines])
            return 0, output.encode() + b'\n' if output else b'', b''

        # Read from files
        output = []
        for path in files:
            content = self.vfs.read_file(path, process.cwd)
            if content is None:
                return 1, b'', f'head: {path}: No such file or directory\n'.encode()

            lines = content.decode('utf-8', errors='ignore').splitlines()
            if len(files) > 1:
                output.append(f'==> {path} <==')
            output.extend(lines[:num_lines])

        return 0, '\n'.join(output).encode() + b'\n', b''

    def cmd_tail(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Display last lines of a file"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        num_lines = 10  # default
        if '-n' in command.args:
            idx = command.args.index('-n')
            if idx + 1 < len(command.args):
                try:
                    num_lines = int(command.args[idx + 1])
                except ValueError:
                    return 1, b'', b'tail: invalid number of lines\n'

        # Get files (filter out options)
        files = [arg for arg in command.args if not arg.startswith('-') and not arg.isdigit()]

        if not files:
            # Read from stdin
            lines = input_data.decode('utf-8', errors='ignore').splitlines()
            output = '\n'.join(lines[-num_lines:])
            return 0, output.encode() + b'\n' if output else b'', b''

        # Read from files
        output = []
        for path in files:
            content = self.vfs.read_file(path, process.cwd)
            if content is None:
                return 1, b'', f'tail: {path}: No such file or directory\n'.encode()

            lines = content.decode('utf-8', errors='ignore').splitlines()
            if len(files) > 1:
                output.append(f'==> {path} <==')
            output.extend(lines[-num_lines:])

        return 0, '\n'.join(output).encode() + b'\n', b''

    def cmd_more(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Page through text (simplified - just outputs all)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            # Read from stdin
            return 0, input_data, b''

        # Read from file
        path = command.args[0]
        content = self.vfs.read_file(path, process.cwd)
        if content is None:
            return 1, b'', f'more: {path}: No such file or directory\n'.encode()

        return 0, content, b''

    def cmd_less(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Page through text (simplified - just outputs all)"""
        # For now, less behaves like more
        return self.cmd_more(command, current_pid, input_data)

    def cmd_wc(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Word, line, character, and byte count"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        show_lines = '-l' in command.args
        show_words = '-w' in command.args
        show_chars = '-c' in command.args
        show_bytes = '-c' in command.args or '-m' in command.args

        # If no options, show all
        if not (show_lines or show_words or show_chars or show_bytes):
            show_lines = show_words = show_chars = True

        # Get files
        files = [arg for arg in command.args if not arg.startswith('-')]

        if not files:
            # Read from stdin
            text = input_data.decode('utf-8', errors='ignore')
            lines = text.count('\n')
            words = len(text.split())
            chars = len(text)

            parts = []
            if show_lines:
                parts.append(f'{lines:8}')
            if show_words:
                parts.append(f'{words:8}')
            if show_chars:
                parts.append(f'{chars:8}')

            return 0, ' '.join(parts).encode() + b'\n', b''

        # Process files
        output = []
        total_lines = total_words = total_chars = 0

        for path in files:
            content = self.vfs.read_file(path, process.cwd)
            if content is None:
                return 1, b'', f'wc: {path}: No such file or directory\n'.encode()

            text = content.decode('utf-8', errors='ignore')
            lines = text.count('\n')
            words = len(text.split())
            chars = len(text)

            total_lines += lines
            total_words += words
            total_chars += chars

            parts = []
            if show_lines:
                parts.append(f'{lines:8}')
            if show_words:
                parts.append(f'{words:8}')
            if show_chars:
                parts.append(f'{chars:8}')
            parts.append(path)

            output.append(' '.join(parts))

        # Show total if multiple files
        if len(files) > 1:
            parts = []
            if show_lines:
                parts.append(f'{total_lines:8}')
            if show_words:
                parts.append(f'{total_words:8}')
            if show_chars:
                parts.append(f'{total_chars:8}')
            parts.append('total')
            output.append(' '.join(parts))

        return 0, '\n'.join(output).encode() + b'\n', b''

    def cmd_sort(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Sort lines of text"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        reverse = '-r' in command.args
        numeric = '-n' in command.args
        unique = '-u' in command.args

        # Get files
        files = [arg for arg in command.args if not arg.startswith('-')]

        if not files:
            # Sort stdin
            lines = input_data.decode('utf-8', errors='ignore').splitlines()
        else:
            # Sort file
            all_lines = []
            for path in files:
                content = self.vfs.read_file(path, process.cwd)
                if content is None:
                    return 1, b'', f'sort: {path}: No such file or directory\n'.encode()
                all_lines.extend(content.decode('utf-8', errors='ignore').splitlines())
            lines = all_lines

        # Sort
        if numeric:
            try:
                lines.sort(key=lambda x: float(x) if x else 0, reverse=reverse)
            except ValueError:
                lines.sort(reverse=reverse)
        else:
            lines.sort(reverse=reverse)

        # Remove duplicates if requested
        if unique:
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            lines = unique_lines

        return 0, '\n'.join(lines).encode() + b'\n', b''

    def cmd_uniq(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Remove duplicate adjacent lines"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        count = '-c' in command.args

        # Get file or stdin
        files = [arg for arg in command.args if not arg.startswith('-')]

        if not files:
            lines = input_data.decode('utf-8', errors='ignore').splitlines()
        else:
            content = self.vfs.read_file(files[0], process.cwd)
            if content is None:
                return 1, b'', f'uniq: {files[0]}: No such file or directory\n'.encode()
            lines = content.decode('utf-8', errors='ignore').splitlines()

        # Remove consecutive duplicates
        result = []
        prev = None
        prev_count = 0

        for line in lines:
            if line == prev:
                prev_count += 1
            else:
                if prev is not None:
                    if count:
                        result.append(f'{prev_count:7} {prev}')
                    else:
                        result.append(prev)
                prev = line
                prev_count = 1

        # Don't forget the last line
        if prev is not None:
            if count:
                result.append(f'{prev_count:7} {prev}')
            else:
                result.append(prev)

        return 0, '\n'.join(result).encode() + b'\n', b''

    def cmd_diff(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Compare files (simplified)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if len(command.args) < 2:
            return 1, b'', b'diff: missing operand\n'

        file1 = command.args[0]
        file2 = command.args[1]

        # Read files
        content1 = self.vfs.read_file(file1, process.cwd)
        if content1 is None:
            return 1, b'', f'diff: {file1}: No such file or directory\n'.encode()

        content2 = self.vfs.read_file(file2, process.cwd)
        if content2 is None:
            return 1, b'', f'diff: {file2}: No such file or directory\n'.encode()

        # Simple line-by-line comparison
        lines1 = content1.decode('utf-8', errors='ignore').splitlines()
        lines2 = content2.decode('utf-8', errors='ignore').splitlines()

        if lines1 == lines2:
            return 0, b'', b''  # Files are identical

        # Generate simple diff output
        output = [f'--- {file1}', f'+++ {file2}']
        max_len = max(len(lines1), len(lines2))

        for i in range(max_len):
            line1 = lines1[i] if i < len(lines1) else None
            line2 = lines2[i] if i < len(lines2) else None

            if line1 != line2:
                if line1:
                    output.append(f'< {line1}')
                if line2:
                    output.append(f'> {line2}')

        return 1, '\n'.join(output).encode() + b'\n', b''  # Exit 1 if files differ

    def cmd_patch(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Apply a diff patch (placeholder)"""
        return 1, b'', b'patch: not implemented (complex operation)\n'

    def cmd_awk(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Pattern scanning and processing (simplified)"""
        if not command.args:
            return 1, b'', b'awk: missing program\n'

        program = command.args[0]

        # Very simplified awk - only support print
        lines = input_data.decode('utf-8', errors='ignore').splitlines()
        output = []

        for line in lines:
            fields = line.split()

            # Simple pattern matching
            if 'print' in program:
                if '$0' in program or 'print' == program.strip():
                    output.append(line)
                elif '$1' in program and len(fields) > 0:
                    output.append(fields[0])
                elif '$2' in program and len(fields) > 1:
                    output.append(fields[1])
                # Add more field support as needed

        return 0, '\n'.join(output).encode() + b'\n', b''

    def cmd_sed(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Stream editor (simplified)"""
        if not command.args:
            return 1, b'', b'sed: missing command\n'

        sed_cmd = command.args[0]

        # Only support s/pattern/replacement/ for now
        if sed_cmd.startswith('s/'):
            parts = sed_cmd[2:].split('/')
            if len(parts) >= 2:
                pattern = parts[0]
                replacement = parts[1]
                global_replace = len(parts) > 2 and 'g' in parts[2]

                text = input_data.decode('utf-8', errors='ignore')
                if global_replace:
                    result = text.replace(pattern, replacement)
                else:
                    result = text.replace(pattern, replacement, 1)

                return 0, result.encode(), b''

        return 1, b'', b'sed: invalid command (only s/// supported)\n'

    def cmd_vi(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Text editor (placeholder - can't implement interactive editor)"""
        return 1, b'', b'vi: interactive editor not available in this environment\nUse VirtualScript to create/modify files programmatically\n'


class ArchiveUtilities:
    """Archive and compression utilities"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_tar(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Archive files (simplified)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Parse options
        create = 'c' in ''.join([arg for arg in command.args if arg.startswith('-')])
        extract = 'x' in ''.join([arg for arg in command.args if arg.startswith('-')])
        list_files = 't' in ''.join([arg for arg in command.args if arg.startswith('-')])

        # Get file argument
        file_arg = None
        for i, arg in enumerate(command.args):
            if arg.startswith('-') and 'f' in arg:
                if i + 1 < len(command.args):
                    file_arg = command.args[i + 1]
                    break

        if not file_arg:
            return 1, b'', b'tar: need -f option\n'

        if create:
            # Create tar archive (simplified - just concatenate files)
            files = [arg for arg in command.args if not arg.startswith('-') and arg != file_arg]
            if not files:
                return 1, b'', b'tar: no files to archive\n'

            archive_content = []
            for path in files:
                content = self.vfs.read_file(path, process.cwd)
                if content is None:
                    return 1, b'', f'tar: {path}: No such file or directory\n'.encode()

                # Simple format: filename|content|
                archive_content.append(f'{path}|{len(content)}|'.encode() + content)

            result = self.vfs.create_file(file_arg, 0o644, process.uid, process.gid,
                                         b''.join(archive_content), process.cwd)
            if result is None:
                return 1, b'', f'tar: cannot create {file_arg}\n'.encode()

            return 0, b'', b''

        elif list_files:
            # List archive contents
            content = self.vfs.read_file(file_arg, process.cwd)
            if content is None:
                return 1, b'', f'tar: {file_arg}: No such file or directory\n'.encode()

            # Parse simple format
            output = []
            remaining = content
            while remaining:
                if b'|' not in remaining:
                    break
                header, remaining = remaining.split(b'|', 1)
                if b'|' not in remaining:
                    break
                size_str, remaining = remaining.split(b'|', 1)
                try:
                    size = int(size_str)
                    filename = header.decode('utf-8', errors='ignore')
                    output.append(filename)
                    remaining = remaining[size:]
                except (ValueError, IndexError):
                    break

            return 0, '\n'.join(output).encode() + b'\n', b''

        else:
            return 1, b'', b'tar: need -c, -x, or -t option\n'

    def cmd_gzip(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Compress files"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            # Compress stdin
            compressed = zlib.compress(input_data)
            return 0, compressed, b''

        # Compress file
        path = command.args[0]
        content = self.vfs.read_file(path, process.cwd)
        if content is None:
            return 1, b'', f'gzip: {path}: No such file or directory\n'.encode()

        compressed = zlib.compress(content)

        # Create .gz file
        gz_path = path + '.gz'
        result = self.vfs.create_file(gz_path, 0o644, process.uid, process.gid,
                                     compressed, process.cwd)
        if result is None:
            return 1, b'', f'gzip: cannot create {gz_path}\n'.encode()

        # Remove original file
        self.vfs.unlink(path, process.cwd)

        return 0, b'', b''

    def cmd_gunzip(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Decompress files"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if not command.args:
            # Decompress stdin
            try:
                decompressed = zlib.decompress(input_data)
                return 0, decompressed, b''
            except zlib.error:
                return 1, b'', b'gunzip: invalid compressed data\n'

        # Decompress file
        path = command.args[0]
        content = self.vfs.read_file(path, process.cwd)
        if content is None:
            return 1, b'', f'gunzip: {path}: No such file or directory\n'.encode()

        try:
            decompressed = zlib.decompress(content)
        except zlib.error:
            return 1, b'', f'gunzip: {path}: invalid compressed data\n'.encode()

        # Create decompressed file (remove .gz extension)
        if path.endswith('.gz'):
            output_path = path[:-3]
        else:
            output_path = path + '.out'

        result = self.vfs.create_file(output_path, 0o644, process.uid, process.gid,
                                     decompressed, process.cwd)
        if result is None:
            return 1, b'', f'gunzip: cannot create {output_path}\n'.encode()

        # Remove compressed file
        self.vfs.unlink(path, process.cwd)

        return 0, b'', b''


class NetworkUtilities:
    """Network utilities"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_telnet(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Telnet client (placeholder)"""
        if not command.args:
            return 1, b'', b'telnet: missing host\n'

        host = command.args[0]
        port = command.args[1] if len(command.args) > 1 else '23'

        return 1, b'', f'telnet: connection to {host}:{port} not implemented\nUse ssh command for remote access\n'.encode()

    def cmd_ftp(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """FTP client (placeholder)"""
        return 1, b'', b'ftp: not implemented\n'

    def cmd_wget(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Download files (placeholder)"""
        if not command.args:
            return 1, b'', b'wget: missing URL\n'

        url = command.args[0]
        return 1, b'', f'wget: downloading from {url} not implemented\n'.encode()

    def cmd_curl(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Transfer data from URLs (placeholder)"""
        if not command.args:
            return 1, b'', b'curl: missing URL\n'

        url = command.args[0]
        return 1, b'', f'curl: transfer from {url} not implemented\n'.encode()


class SystemUtilities:
    """System management utilities"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_mount(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Mount filesystems (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Show mounted filesystems
        output = """/dev/hda1 on / type ext2 (rw)
proc on /proc type proc (rw)
devpts on /dev/pts type devpts (rw)
"""
        return 0, output.encode(), b''

    def cmd_route(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Show/manipulate routing table (placeholder)"""
        output = """Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         192.168.1.1     0.0.0.0         UG    0      0        0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
"""
        return 0, output.encode(), b''

    def cmd_iptables(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Firewall configuration (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Only root can use iptables
        if process.uid != 0:
            return 1, b'', b'iptables: Permission denied (must be root)\n'

        output = """Chain INPUT (policy ACCEPT)
target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination
"""
        return 0, output.encode(), b''

    def cmd_init(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Init system (placeholder)"""
        return 1, b'', b'init: already running (PID 1)\n'

    def cmd_shutdown(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Shutdown system (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if process.uid != 0:
            return 1, b'', b'shutdown: Permission denied (must be root)\n'

        return 0, b'Broadcast message: System is going down for reboot NOW!\n', b''

    def cmd_reboot(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Reboot system (placeholder)"""
        return self.cmd_shutdown(command, current_pid, input_data)

    def cmd_fdisk(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Disk partitioning (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if process.uid != 0:
            return 1, b'', b'fdisk: Permission denied (must be root)\n'

        output = """Disk /dev/hda: 8589 MB, 8589934592 bytes
255 heads, 63 sectors/track, 1044 cylinders
Units = cylinders of 16065 * 512 = 8225280 bytes

   Device Boot    Start       End    Blocks   Id  System
/dev/hda1   *         1      1044   8385898+  83  Linux
"""
        return 0, output.encode(), b''

    def cmd_fsck(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Filesystem check (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if process.uid != 0:
            return 1, b'', b'fsck: Permission denied (must be root)\n'

        output = """fsck 1.14, 9-Jan-1999 for EXT2 FS 0.5b, 95/08/09
/dev/hda1: clean, 1234/2048 files, 12345/16384 blocks
"""
        return 0, output.encode(), b''

    def cmd_mkfs(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Make filesystem (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        if process.uid != 0:
            return 1, b'', b'mkfs: Permission denied (must be root)\n'

        return 1, b'', b'mkfs: dangerous operation - not implemented in game\n'


class DevelopmentTools:
    """Development and programming tools"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_make(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Build automation (placeholder)"""
        process = self.processes.get_process(current_pid)
        if not process:
            return 1, b'', b'Process not found\n'

        # Check for Makefile
        if not self.vfs.stat('Makefile', process.cwd):
            return 1, b'', b'make: *** No targets specified and no makefile found.  Stop.\n'

        output = """gcc -c main.c
gcc -c utils.c
gcc -o program main.o utils.o
Build complete!
"""
        return 0, output.encode(), b''

    def cmd_gcc(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """GNU C compiler (placeholder)"""
        if not command.args:
            return 1, b'', b'gcc: no input files\n'

        input_file = command.args[0]
        output = f'gcc: compiling {input_file}...\nCompilation successful!\n'
        return 0, output.encode(), b''

    def cmd_perl(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Perl interpreter (placeholder)"""
        if '-e' in command.args:
            # Execute perl code
            output = "Perl code execution not implemented\n"
            return 0, output.encode(), b''

        return 1, b'', b'perl: script execution not implemented\nUse VirtualScript instead\n'

    def cmd_python(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Python interpreter (placeholder)"""
        if not command.args:
            return 1, b'', b'python: interactive mode not available\nUse VirtualScript instead\n'

        script = command.args[0]
        return 1, b'', f'python: cannot execute {script}\nUse VirtualScript instead\n'.encode()


class ShellUtilities:
    """Shell programs"""

    def __init__(self, vfs, permissions, processes):
        self.vfs = vfs
        self.permissions = permissions
        self.processes = processes

    def cmd_sh(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Bourne shell (placeholder)"""
        return 1, b'', b'sh: nested shell not implemented\n'

    def cmd_bash(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Bash shell (placeholder)"""
        return 1, b'', b'bash: nested shell not implemented\n'

    def cmd_fish(self, command, current_pid: int, input_data: bytes) -> Tuple[int, bytes, bytes]:
        """Fish shell (placeholder)"""
        return 1, b'', b'fish: friendly interactive shell not implemented\nUse VirtualScript to create custom shells\n'
