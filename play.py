#!/usr/bin/env python3
"""
Poodillion 2 - Virtual Unix Hacking Game
December 1990 - The Early Internet

Auto-starts into an immersive hacking world.
Find missions by reading files in /missions/
"""

import sys
import readline
from world_1990 import create_december_1990_world


def print_intro():
    """Print atmospheric introduction"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                    CONNECTING TO HOST...                      ║
║                                                               ║
║                  [████████████████████]                       ║
║                                                               ║
║                    Connection Established                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                      December 24, 1990                        ║
║                        03:47:22 GMT                           ║
║                                                               ║
║   You've accessed a private network through a mysterious     ║
║   invitation. The terminal flickers. Messages scroll by.     ║
║   Something strange is happening on the net tonight...       ║
║                                                               ║
║   Your terminal: kali-box (192.168.13.37)                    ║
║   Location: Unknown                                           ║
║   Access Level: Guest                                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

[SYSTEM] Welcome to the network, traveler.
[SYSTEM] Type 'cat /missions/README' to see available missions.
[SYSTEM] Type 'help' or 'ls /bin' to see available commands.
[SYSTEM] The web browser is 'lynx' - try: lynx bbs.cyberspace.net

Good luck. You'll need it.

""")


def interactive_shell(system, network, username='root', password='root'):
    """
    Run interactive shell on a system with SSH support
    """
    # Auto-login (silent)
    login_result = system.login(username, password)
    if not login_result:
        print('Connection failed!')
        return False

    # Set up tab completion
    def completer(text, state):
        """Tab completion function for readline"""
        if state == 0:
            line = readline.get_line_buffer()
            begin_idx = readline.get_begidx()

            process = system.processes.get_process(system.shell_pid)
            if not process:
                return None

            if begin_idx == 0:
                # Completing command name
                matches = []
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
                # Completing file path
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

        try:
            return completer.matches[state]
        except (IndexError, AttributeError):
            return None

    completer.matches = []

    # Configure readline
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    readline.set_completer_delims(' \t\n;')

    # Set up I/O callbacks
    def input_callback(prompt):
        """Provide input to PooScript"""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return 'exit'

    def output_callback(text):
        """Flush output immediately to stdout"""
        print(text, end='')
        sys.stdout.flush()

    def error_callback(text):
        """Flush errors immediately to stderr"""
        print(text, end='', file=sys.stderr)
        sys.stderr.flush()

    # Set callbacks
    system.shell.executor.input_callback = input_callback
    system.shell.executor.output_callback = output_callback
    system.shell.executor.error_callback = error_callback

    system.vfs.input_callback = input_callback
    system.vfs.output_callback = output_callback
    system.vfs.error_callback = error_callback

    # Main shell loop
    while True:
        try:
            exit_code, stdout, stderr = system.shell.execute('/bin/pooshell', system.shell_pid, b'')

            # Check if system was shut down
            if not system.is_alive():
                print(f'\n[Connection lost: {system.hostname} has shut down]')
                print(f'Connection to {system.ip} closed.')
                return False

            # Check for SSH request
            if exit_code == 255:
                ssh_request = system.vfs.read_file('/tmp/.ssh_request', 1)
                if ssh_request:
                    request = ssh_request.decode('utf-8', errors='ignore').strip()
                    if '|' in request:
                        target_user, target_host = request.split('|', 1)
                        system.vfs.write_file('/tmp/.ssh_request', b'', 1)

                        target_system = network.systems.get(target_host)
                        if target_system:
                            if not target_system.is_alive():
                                print(f'\nssh: connect to host {target_host} port 22: No route to host')
                                continue

                            # Prompt for password
                            try:
                                password = input(f"{target_user}@{target_host}'s password: ")
                            except (EOFError, KeyboardInterrupt):
                                print("\n")
                                continue

                            success = interactive_shell(target_system, network, target_user, password)
                            print(f'\nConnection to {target_host} closed.')
                            print(f'Back on {system.hostname} ({system.ip})')
                            continue
                        else:
                            print(f'\nssh: Could not resolve hostname {target_host}')
                            continue
                break
            else:
                break

        except KeyboardInterrupt:
            print('\n^C')
            break
        except Exception as e:
            print(f'Error: {e}', file=sys.stderr)
            break

    return True


def main():
    """Main entry point - auto-start the world"""
    print_intro()

    # Create the December 1990 world
    print("[SYSTEM] Initializing network...\n")
    attacker, network, systems = create_december_1990_world()

    # Boot all systems
    print("[SYSTEM] Bringing systems online...\n")
    for system in systems:
        system.boot()

    print("[SYSTEM] All systems operational.\n")
    print("="*60)
    print()

    # Start the game
    interactive_shell(attacker, network)

    # Farewell
    print("\n\n╔═══════════════════════════════════════════════════════════════╗")
    print("║              Connection terminated.                           ║")
    print("║              See you in the network, traveler.                ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")


if __name__ == '__main__':
    main()
