#!/usr/bin/env python3
"""
Demo script for the Virtual Unix System
Shows basic functionality and interactive shell
"""

import sys
from core.system import UnixSystem
from core.network import VirtualNetwork


def create_scenario():
    """Create a basic hacking scenario"""
    # Create network
    network = VirtualNetwork()

    # Create target system
    target = UnixSystem('corporate-web', '192.168.1.50')
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

    # Create attacker system
    attacker = UnixSystem('kali-box', '192.168.1.100')
    attacker.add_network(network)

    # Add tools to attacker
    attacker.vfs.create_file(
        '/root/notes.txt',
        0o644, 0, 0,
        b'Target: 192.168.1.50\nObjective: Gain root access and exfiltrate data\n',
        1
    )

    # Connect systems on network
    network.add_route('192.168.1.100', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.100')

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
