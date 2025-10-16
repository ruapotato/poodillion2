#!/usr/bin/env python3
"""
Demo script for the Virtual Unix System
Shows basic functionality and interactive shell
"""

import sys
import readline
from core.system import UnixSystem
from core.network import VirtualNetwork


def create_scenario():
    """Create a basic hacking scenario with router"""
    # Create network
    network = VirtualNetwork()

    # Create attacker system (external network)
    attacker = UnixSystem('kali-box', '10.0.0.100')
    attacker.default_gateway = '10.0.0.1'
    attacker.add_network(network)

    # Add tools and notes to attacker
    attacker.vfs.create_file(
        '/root/notes.txt',
        0o644, 0, 0,
        b'Target: 192.168.1.50 (behind router)\n'
        b'Gateway: 10.0.0.1 (routes to 192.168.1.1)\n'
        b'Objective: Gain root access and exfiltrate data\n\n'
        b'Try these commands:\n'
        b'  ping 192.168.1.50       # Test multi-hop routing\n'
        b'  cat /proc/net/arp       # View ARP cache\n'
        b'  cat /proc/net/route     # View routing table\n'
        b'  nmap 192.168.1.50       # Scan target ports\n',
        1
    )

    # Create router/gateway with 2 interfaces
    router = UnixSystem('gateway', {
        'eth0': '10.0.0.1',       # External (internet-facing)
        'eth1': '192.168.1.1'     # Internal (corporate LAN)
    })
    router.ip_forward = True  # Enable routing between networks
    router.add_network(network)

    # Create target system (internal network)
    target = UnixSystem('corporate-web', '192.168.1.50')
    target.default_gateway = '192.168.1.1'
    target.add_network(network)

    # Add some users
    target.add_user('webadmin', 'password123', 1001, '/home/webadmin')
    target.add_user('dbuser', 'mysql2020', 1002, '/home/dbuser')

    # Create some interesting files
    target.create_vulnerable_file(
        '/home/webadmin/.bash_history',
        b'ls -la\ncat /etc/shadow\nmysql -u root -p\n# Oops, entered password: MyS3cr3tP@ss\nsudo systemctl restart apache2\n',
        hint='Command history might contain sensitive info'
    )

    target.create_vulnerable_file(
        '/var/www/config.php',
        b'<?php\n$db_host = "localhost";\n$db_user = "root";\n$db_pass = "MyS3cr3tP@ss";\n$db_name = "webapp";\n?>\n',
        hint='Web config files often contain credentials'
    )

    target.vfs.create_file(
        '/home/webadmin/todo.txt',
        0o644, 1001, 100,
        b'- Update Apache to latest version (currently vulnerable)\n- Change default passwords\n- Review firewall rules\n',
        1
    )

    # Spawn some vulnerable services
    target.spawn_service('apache2', ['service', 'webserver', 'vulnerable'], uid=33)
    target.spawn_service('mysqld', ['service', 'database', 'vulnerable'], uid=27)
    target.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Layer-2 network connectivity
    # Attacker <-> Router (external)
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.100')

    # Router (internal) <-> Target
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')

    # Multi-hop routing will work automatically because router has ip_forward=True

    return attacker, target, network


def interactive_shell(system: UnixSystem):
    """Run interactive pooshell"""
    print(f'\n=== {system.hostname} ===')
    print('Login as root')

    # Auto-login as root
    if not system.login('root', 'root'):
        print('Login failed!')
        return

    # Show MOTD
    motd = system.vfs.read_file('/etc/motd', 1)
    if motd:
        print(motd.decode('utf-8', errors='ignore'))

    print()

    # Set up tab completion using readline
    def completer(text, state):
        """Tab completion function for readline"""
        if state == 0:
            # First call - generate list of matches
            line = readline.get_line_buffer()
            begin_idx = readline.get_begidx()

            # Get current process
            process = system.processes.get_process(system.shell_pid)
            if not process:
                return None

            # Determine what we're completing based on position in line
            if begin_idx == 0:
                # Completing command name (first word)
                matches = []

                # Search /bin directories for matching commands
                for bin_dir in ['/bin', '/usr/bin', '/sbin', '/usr/sbin']:
                    try:
                        entries = system.vfs.list_dir(bin_dir, 1)
                        if entries:
                            for name, _ in entries:
                                if name.startswith(text) and name not in ('.', '..'):
                                    matches.append(name)
                    except:
                        pass

                completer.matches = sorted(set(matches))
            else:
                # Completing file path argument
                # Determine directory and filename parts
                if '/' in text:
                    last_slash = text.rfind('/')
                    dir_part = text[:last_slash] or '/'
                    file_part = text[last_slash + 1:]
                else:
                    dir_part = '.'
                    file_part = text

                matches = []
                try:
                    entries = system.vfs.list_dir(dir_part, process.cwd)
                    if entries:
                        for name, ino in entries:
                            if name.startswith(file_part) and name not in ('.', '..'):
                                if dir_part == '.':
                                    matches.append(name)
                                elif dir_part == '/':
                                    matches.append('/' + name)
                                else:
                                    matches.append(dir_part + '/' + name)
                except:
                    pass

                completer.matches = sorted(matches)

        # Return next match
        try:
            return completer.matches[state]
        except (IndexError, AttributeError):
            return None

    completer.matches = []

    # Configure readline
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    readline.set_completer_delims(' \t\n;')

    # Set up I/O callbacks for pooshell
    def input_callback(prompt):
        """Provide input to PooScript"""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return 'exit'

    def output_callback(text):
        """Flush output immediately to real stdout"""
        print(text, end='')
        sys.stdout.flush()

    def error_callback(text):
        """Flush errors immediately to real stderr"""
        print(text, end='', file=sys.stderr)
        sys.stderr.flush()

    # Set the callbacks on the shell
    system.shell.executor.input_callback = input_callback
    system.shell.executor.output_callback = output_callback
    system.shell.executor.error_callback = error_callback

    # Set the callbacks on the VFS for device file I/O
    system.vfs.input_callback = input_callback
    system.vfs.output_callback = output_callback
    system.vfs.error_callback = error_callback

    # Execute pooshell interactively
    try:
        exit_code, stdout, stderr = system.shell.execute('/bin/pooshell', system.shell_pid, b'')

        # Don't print buffered output - callbacks already handled real-time output
        # The stdout/stderr buffers still accumulate but we've already printed everything via callbacks

    except KeyboardInterrupt:
        print('\n^C')
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)


def demo_basic():
    """Demo basic system functionality"""
    print('=== Poodillion 2: Basic Demo ===\n')

    system = UnixSystem('demo-host')

    # Boot the system
    system.boot()

    # Login
    print('\nLogging in as root...')
    system.login('root', 'root')

    # Run some commands
    commands = [
        'pwd',
        'ls /',
        'ls -l /etc',
        'cat /etc/hostname',
        'echo "Hello World"',
        'echo "test content" > /tmp/test.txt',
        'cat /tmp/test.txt',
        'mkdir /tmp/mydir',
        'ls -l /tmp',
        'ps -f',
    ]

    for cmd in commands:
        print(f'\n$ {cmd}')
        exit_code, stdout, stderr = system.execute_command(cmd)
        if stdout:
            print(stdout, end='')
        if stderr:
            print(f'ERROR: {stderr}', file=sys.stderr)


def demo_scenario():
    """Demo hacking scenario"""
    print('=== Poodillion 2: Virtual Hacking Scenario ===\n')

    attacker, target, network = create_scenario()

    # Boot the attacker system
    print('\n=== Booting Attacker System ===\n')
    attacker.boot()

    print('\nYou are on the attacker machine.')
    print('Target system is at 192.168.1.50')
    print('Goal: Compromise the target!\n')

    interactive_shell(attacker)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'basic':
        demo_basic()
    else:
        demo_scenario()
