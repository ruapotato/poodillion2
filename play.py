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


def interactive_shell(system):
    """Run interactive shell on a system"""
    print(f'\n=== {system.hostname} ===')
    print('Logging in as root...')

    # Auto-login as root
    if not system.login('root', 'root'):
        print('Login failed!')
        return

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

    # Execute shell
    try:
        exit_code, stdout, stderr = system.shell.execute('/bin/pooshell', system.shell_pid, b'')
    except KeyboardInterrupt:
        print('\n^C')
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)


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

    # Boot attacker system
    print('\n=== Booting Your System ===\n')
    attacker.boot()

    print("\nYou are now connected to your attacking machine.")
    print("Good luck!\n")

    # Start interactive shell
    interactive_shell(attacker)

    # Post-game
    print("\n\nThanks for playing!")
    print("Did you complete the objective? Try a harder scenario!\n")


def main():
    """Main entry point"""
    print_banner()

    while True:
        print_scenario_menu()

        try:
            choice = input("Select a scenario (1-3, Q to quit): ").strip().upper()
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
            print("Please select 1, 2, 3, or Q")


if __name__ == '__main__':
    main()
