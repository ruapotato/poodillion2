#!/usr/bin/env python3
"""
Test script for new fun features in Poodillion OS
Tests: fun commands, error messages, websites, Easter eggs
"""

from core.system import UnixSystem
from core.vfs import VFS
from core.permissions import PermissionSystem
from core.process import ProcessManager
from core.shell import Shell
from core.script_installer import install_scripts


def test_fun_features():
    """Test all the fun new features"""

    print("=" * 60)
    print("TESTING FUN FEATURES IN POODILLION OS")
    print("=" * 60)
    print()

    # Create the system
    print("Creating system...")
    system = UnixSystem()
    vfs = system.vfs
    shell = system.shell

    # Get root process
    root_pid = 1

    # Test 1: Command not found errors
    print("\n" + "=" * 60)
    print("TEST 1: Fun Command Not Found Messages")
    print("=" * 60)

    test_commands = ['sl', 'help', 'hack', 'python', 'vim', 'apt', 'asdfghjkl']
    for cmd in test_commands:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stderr:
            print(stderr.decode('utf-8'), end='')

    # Test 2: Fun commands
    print("\n" + "=" * 60)
    print("TEST 2: Fun Commands")
    print("=" * 60)

    fun_commands = [
        'fortune',
        'cowsay Hello from Poodillion!',
        'banner HELLO',
        'whoami',
        'uptime',
        'rev hello world',
        'yes | head',
    ]

    for cmd in fun_commands:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stdout:
            print(stdout.decode('utf-8'), end='')
        if stderr:
            print(stderr.decode('utf-8'), end='')

    # Test 3: Special fun commands
    print("\n" + "=" * 60)
    print("TEST 3: Special Fun Commands")
    print("=" * 60)

    special_commands = [
        'sl',
        'cake',
        'matrix',
        'hack',
        'lolcat Hello Rainbow!',
    ]

    for cmd in special_commands:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stdout:
            print(stdout.decode('utf-8'), end='')

    # Test 4: Websites
    print("\n" + "=" * 60)
    print("TEST 4: Virtual Websites")
    print("=" * 60)

    websites = [
        'curl index.html',
        'curl news.poo',
        'curl hackernews.poo',
        'curl weather.poo',
    ]

    for cmd in websites:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stdout:
            # Show first 500 chars
            output = stdout.decode('utf-8')
            if len(output) > 500:
                print(output[:500] + "\n... (truncated)")
            else:
                print(output, end='')
        if stderr:
            print(stderr.decode('utf-8'), end='')

    # Test 5: Easter Eggs
    print("\n" + "=" * 60)
    print("TEST 5: Easter Eggs Discovery")
    print("=" * 60)

    easter_egg_commands = [
        'ls -a /secrets',
        'cat /secrets/.hidden_treasure',
        'cat /etc/motd',
        'ls /var/log',
        'cat /var/log/definitely_not_passwords.log | head -n 20',
    ]

    for cmd in easter_egg_commands:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stdout:
            output = stdout.decode('utf-8')
            if len(output) > 500:
                print(output[:500] + "\n... (truncated)")
            else:
                print(output, end='')

    # Test 6: Filesystem exploration
    print("\n" + "=" * 60)
    print("TEST 6: Filesystem Exploration")
    print("=" * 60)

    explore_commands = [
        'ls /bin | head -n 20',
        'ls /www',
        'ls -la /secrets',
        'ls /tmp',
    ]

    for cmd in explore_commands:
        print(f"\n> {cmd}")
        exit_code, stdout, stderr = shell.execute(cmd, root_pid)
        if stdout:
            print(stdout.decode('utf-8'), end='')

    # Summary
    print("\n" + "=" * 60)
    print("TESTING COMPLETE!")
    print("=" * 60)
    print()
    print("Summary of New Features:")
    print("✓ Fun command-not-found error messages")
    print("✓ Fun commands: fortune, cowsay, banner, sl, matrix, etc.")
    print("✓ Virtual websites browseable with curl")
    print("✓ Easter eggs hidden throughout the filesystem")
    print("✓ Discoverable secrets in logs and hidden files")
    print()
    print("Try exploring the system interactively!")
    print("Run: python3 play.py")


if __name__ == '__main__':
    test_fun_features()
