#!/usr/bin/env python3
"""
Interactive Test Environment for Poodillion
Provides a better way to explore and test the virtual world
"""

import sys
import readline  # For command history
import time
import threading
from world_1990 import create_december_1990_world
from core.world_life import WorldLife

class InteractiveWorld:
    def __init__(self):
        print("="*70)
        print("INITIALIZING POODILLION WORLD...")
        print("="*70)

        # Create world
        self.attacker, self.network, self.all_systems = create_december_1990_world()

        # Initialize shell
        self.attacker.shell_pid = self.attacker.processes.spawn(
            parent_pid=1, uid=0, gid=0, euid=0, egid=0,
            command='pooshell', args=['pooshell'],
            cwd=self.attacker.vfs._resolve_path('/root', 1),
            env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'},
            tags=[]
        )

        # Initialize world life system
        self.world_life = WorldLife(self.network, self.all_systems)
        self.show_notifications = True
        self.command_count = 0

        print("\n✓ World initialized")
        print(f"✓ Connected as root on {self.attacker.hostname} ({self.attacker.ip})")
        print("✓ Background activity enabled")
        self.show_status()

    def show_status(self):
        """Show current world status"""
        print("\n" + "-"*70)
        print("NETWORK STATUS:")
        active_servers = 0
        for ip, system in self.network.systems.items():
            if ip == self.attacker.ip:
                continue
            httpd_procs = [p for p in system.processes.list_processes() if 'httpd' in p.command]
            if httpd_procs:
                active_servers += 1

        # Count active users
        total_users = sum(len(users) for users in self.world_life.active_users.values())

        print(f"  • {len(self.network.systems)-1} remote systems online")
        print(f"  • {active_servers} web servers running (httpd)")
        print(f"  • {total_users} users active on network (simulated)")
        print(f"  • Your IP: {self.attacker.ip}")

        # Show recent events
        recent_events = self.world_life.get_recent_events(count=3)
        if recent_events:
            print(f"\n  RECENT NETWORK ACTIVITY:")
            for event in recent_events:
                time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
                print(f"    [{time_str}] {event.message}")

        print("-"*70 + "\n")

    def check_for_events(self):
        """Check for and display new world events"""
        new_events = self.world_life.update()

        if new_events and self.show_notifications:
            for event in new_events:
                if event.visible_to_player:
                    time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
                    print(f"\n\033[93m[{time_str}] NETWORK EVENT: {event.message}\033[0m\n")
                    # Re-show prompt
                    self.show_prompt()

    def execute(self, command):
        """Execute a command and return the output"""
        if not command.strip():
            return

        # Special commands
        if command.strip() == 'help':
            self.show_help()
            return
        elif command.strip() == 'status':
            self.show_status()
            return
        elif command.strip() == 'events':
            self.show_events()
            return
        elif command.strip() == 'notify on':
            self.show_notifications = True
            print("✓ Event notifications enabled")
            return
        elif command.strip() == 'notify off':
            self.show_notifications = False
            print("✓ Event notifications disabled")
            return
        elif command.strip() in ['exit', 'quit', 'q']:
            print("\n" + "="*70)
            print("Disconnecting from the network...")
            print("See you in cyberspace, traveler.")
            print("="*70)
            sys.exit(0)

        # Execute command
        try:
            exit_code, stdout, stderr = self.attacker.execute_command(command)

            # Show output
            if stdout:
                print(stdout)
            if stderr:
                print(f"\033[91m{stderr}\033[0m")  # Red color for errors

            # Show exit code if non-zero
            if exit_code != 0:
                print(f"\033[93m[Exit code: {exit_code}]\033[0m")  # Yellow

        except Exception as e:
            print(f"\033[91mERROR: {e}\033[0m")

    def show_events(self):
        """Show recent events"""
        print("\n" + "="*70)
        print("RECENT NETWORK EVENTS:")
        print("="*70)

        events = self.world_life.get_recent_events(count=10, visible_only=False)
        if not events:
            print("No recent events")
        else:
            for event in events:
                time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
                visibility = "👁 " if event.visible_to_player else "🔒 "
                print(f"{visibility}[{time_str}] {event.message}")

        print("="*70 + "\n")

    def show_prompt(self):
        """Show the prompt without waiting for input"""
        prompt = f"\033[92mroot@{self.attacker.hostname}\033[0m:\033[94m~\033[0m$ "
        print(prompt, end='', flush=True)

    def show_help(self):
        """Show help message"""
        print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    INTERACTIVE TEST MODE                          ║
╚═══════════════════════════════════════════════════════════════════╝

SPECIAL COMMANDS:
  help                  - Show this help
  status                - Show world status
  events                - Show recent network events
  notify on/off         - Enable/disable event notifications
  exit, quit, q         - Exit the session

EXPLORATION COMMANDS:
  lynx                  - Browse the default web portal
  lynx <site>           - Visit a specific site
  nmap 192.168.1.0/24   - Scan the network
  ping <ip>             - Check if host is alive
  ssh <ip>              - Connect to remote system

WEB COMMANDS:
  lynx bbs.cyberspace.net              - Visit main BBS
  lynx underground.bbs                 - Visit underground
  lynx bbs.cyberspace.net/time.poo     - Dynamic content!
  lynx bbs.cyberspace.net/serverinfo.poo - Server info

SYSTEM COMMANDS:
  ls, cd, pwd, cat      - File operations
  ps                    - List processes
  ifconfig              - Network config
  whoami                - Current user

MISSIONS:
  cat /missions/README  - View available missions

TIP: Use UP/DOWN arrows for command history!

Press ENTER to continue...
""")
        input()

    def run(self):
        """Main interactive loop"""
        print("Type 'help' for commands, 'exit' to quit")
        print("\033[93mTIP: The world is alive! Events happen in the background.\033[0m")
        print()

        while True:
            try:
                # Check for world events every few commands
                if self.command_count % 3 == 0:
                    self.check_for_events()
                self.command_count += 1

                # Get prompt
                prompt = f"\033[92mroot@{self.attacker.hostname}\033[0m:\033[94m~\033[0m$ "
                command = input(prompt)

                # Execute
                self.execute(command)

            except KeyboardInterrupt:
                print("\n\nUse 'exit' to quit")
                continue
            except EOFError:
                print("\n\nDisconnected.")
                break


def main():
    """Entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║            POODILLION INTERACTIVE TEST ENVIRONMENT                ║
║                                                                   ║
║          A better way to explore the virtual world!               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    world = InteractiveWorld()
    world.run()


if __name__ == '__main__':
    main()
