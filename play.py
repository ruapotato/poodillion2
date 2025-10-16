#!/usr/bin/env python3
"""
Poodillion 2 - Virtual Unix Hacking Game
Main entry point with scenario selection
"""

import sys
import readline
from scenarios import SCENARIOS, list_scenarios


def print_banner():
    """Print game banner"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗  ██████╗  ██████╗ ██████╗ ██╗██╗     ██╗ ██████╗  ║
║   ██╔══██╗██╔═══██╗██╔═══██╗██╔══██╗██║██║     ██║██╔═══██╗ ║
║   ██████╔╝██║   ██║██║   ██║██║  ██║██║██║     ██║██║   ██║ ║
║   ██╔═══╝ ██║   ██║██║   ██║██║  ██║██║██║     ██║██║   ██║ ║
║   ██║     ╚██████╔╝╚██████╔╝██████╔╝██║███████╗██║╚██████╔╝ ║
║   ╚═╝      ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝╚══════╝╚═╝ ╚═════╝  ║
║                                                               ║
║              Virtual Unix Hacking Environment                ║
║                    Version 2.0 - PooScript                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_scenario_menu():
    """Print scenario selection menu"""
    print("\n=== SELECT YOUR MISSION ===\n")

    scenarios = list_scenarios()

    for scenario in scenarios:
        diff_color = {
            'Tutorial': '📘',
            'Easy': '🟢',
            'Medium': '🟡',
            'Hard': '🔴',
        }.get(scenario['difficulty'], '⚪')

        print(f"[{scenario['key']}] {diff_color} {scenario['title']}")
        print(f"    {scenario['description']}")
        print(f"    Difficulty: {scenario['difficulty']}")
        print()

    print("[Q] Quit")
    print()


def interactive_shell(system, network, username='root', password='root'):
    """
    Run interactive shell on a system with SSH support

    Args:
        system: The UnixSystem to connect to
        network: The VirtualNetwork containing all systems
        username: Username to login as
        password: Password for authentication
    """
    print(f'\n=== {system.hostname} ({system.ip}) ===')
    print(f'Logging in as {username}...')

    # Auto-login
    if not system.login(username, password):
        print('Login failed!')
        return False

    # Show MOTD
    motd = system.vfs.read_file('/etc/motd', 1)
    if motd:
        print(motd.decode('utf-8', errors='ignore'))

    print()

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

    # SSH context tracking
    ssh_stack = []

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

    # Execute shell and check for SSH requests
    try:
        exit_code, stdout, stderr = system.shell.execute('/bin/pooshell', system.shell_pid, b'')

        # Check if SSH was requested
        ssh_request = system.vfs.read_file('/tmp/.ssh_request', 1)
        if ssh_request:
            request = ssh_request.decode('utf-8', errors='ignore').strip()
            if '|' in request:
                target_user, target_host = request.split('|', 1)

                # Clear the request
                system.vfs.write_file('/tmp/.ssh_request', b'', 1)

                # Find target system in network
                target_system = network.systems.get(target_host)
                if target_system:
                    # Recursively connect to target system
                    ssh_stack.append(system)
                    success = interactive_shell(target_system, network, target_user, 'root')

                    # After returning from SSH, continue current shell
                    if success:
                        print(f'\nConnection to {target_host} closed.')
                        print(f'Back on {system.hostname} ({system.ip})')
                        # Continue shell on current system
                        return interactive_shell(system, network, username, password)
                else:
                    print(f'\nssh: Could not resolve hostname {target_host}')
                    # Continue shell on current system
                    return interactive_shell(system, network, username, password)

    except KeyboardInterrupt:
        print('\n^C')
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)

    return True


def play_scenario(scenario_key):
    """Play a specific scenario"""
    if scenario_key not in SCENARIOS:
        print(f"Error: Unknown scenario '{scenario_key}'")
        return

    print(f"\n{'='*60}")
    print("LOADING SCENARIO...")
    print(f"{'='*60}\n")

    # Create scenario
    create_scenario = SCENARIOS[scenario_key]
    attacker, network, metadata = create_scenario()

    # Print mission briefing
    print(f"\n{'='*60}")
    print(f"MISSION: {metadata['title']}")
    print(f"{'='*60}")
    print(f"\n{metadata['description']}")
    print(f"\nObjective: {metadata['objective']}")
    print(f"Difficulty: {metadata['difficulty']}")
    print(f"\nSystems on network: {len(metadata['systems'])}")

    for sys in metadata['systems']:
        print(f"  - {sys.hostname} ({sys.ip})")

    print(f"\n{'='*60}")

    # Boot ALL systems in the network
    print('\n=== Booting Network Systems ===\n')
    for system in metadata['systems']:
        print(f"Booting {system.hostname} ({system.ip})...")
        system.boot()

    print("\n✓ All systems online")
    print("✓ Network fully emulated")
    print("\nYou are now connected to your attacking machine.")
    print("Use 'ssh <ip>' to connect to other systems.")
    print("Good luck!\n")

    # Start interactive shell on attacker system
    interactive_shell(attacker, network)

    # Post-game
    print("\n\nThanks for playing!")
    print("Did you complete the objective? Try a harder scenario!\n")


def main():
    """Main entry point"""
    print_banner()

    while True:
        print_scenario_menu()

        try:
            choice = input("Select a scenario (0-3, Q to quit): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            sys.exit(0)

        if choice == 'Q':
            print("\nExiting...")
            sys.exit(0)

        if choice in SCENARIOS:
            play_scenario(choice)
            # After scenario ends, return to menu
            print("\n" + "="*60)
            input("Press Enter to return to main menu...")
        else:
            print(f"\nInvalid choice: {choice}")
            print("Please select 0, 1, 2, 3, or Q")


if __name__ == '__main__':
    main()
