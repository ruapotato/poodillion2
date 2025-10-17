#!/usr/bin/env python3
"""
Automated Demo/Walkthrough
Shows off the key features of Poodillion with pauses and explanations
"""

import time
import sys
from world_1990 import create_december_1990_world

def pause(seconds=2, message=""):
    """Pause with optional message"""
    if message:
        print(f"\n\033[96m{message}\033[0m")
    time.sleep(seconds)

def type_command(command, delay=0.05):
    """Simulate typing a command"""
    print("\n\033[92m$\033[0m ", end='', flush=True)
    for char in command:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()  # newline

def run_demo():
    """Run the full demo"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                   POODILLION DEMO & WALKTHROUGH                   ║
║                                                                   ║
║              December 24, 1990 - 03:47:22 GMT                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

Welcome to Poodillion - a virtual Unix hacking environment set in 1990.

This demo will showcase:
  • Network exploration and mapping
  • Web servers and dynamic content
  • BBS systems and underground networks
  • The mysterious Nexus...

Press ENTER to begin...
""")
    input()

    print("\n" + "="*70)
    print("INITIALIZING WORLD...")
    print("="*70)

    # Create world
    attacker, network, all_systems = create_december_1990_world()

    # Initialize shell
    attacker.shell_pid = attacker.processes.spawn(
        parent_pid=1, uid=0, gid=0, euid=0, egid=0,
        command='pooshell', args=['pooshell'],
        cwd=attacker.vfs._resolve_path('/root', 1),
        env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'},
        tags=[]
    )

    print("\n✓ World initialized")
    print(f"✓ You are: root@{attacker.hostname} ({attacker.ip})")

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 1: Network Discovery
    print("\n" + "="*70)
    print("DEMO 1: NETWORK DISCOVERY")
    print("="*70)
    pause(1, "Let's scan the network to see what's out there...")

    type_command("nmap 192.168.1.0/24")
    exit_code, stdout, stderr = attacker.execute_command("nmap 192.168.1.0/24")
    print(stdout)

    pause(2, "We found some systems! Let's ping one...")
    type_command("ping 192.168.1.10")
    exit_code, stdout, stderr = attacker.execute_command("ping 192.168.1.10")
    print(stdout[:500])

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 2: Web Browsing
    print("\n" + "="*70)
    print("DEMO 2: WEB BROWSING")
    print("="*70)
    pause(1, "Let's browse the web using lynx (text-based browser)...")

    type_command("lynx")
    exit_code, stdout, stderr = attacker.execute_command("lynx")
    lines = stdout.split('\n')[:30]
    print('\n'.join(lines))

    pause(3, "That's the main portal! Let's visit a specific BBS...")
    type_command("lynx underground.bbs")
    exit_code, stdout, stderr = attacker.execute_command("lynx underground.bbs")
    lines = stdout.split('\n')[:25]
    print('\n'.join(lines))

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 3: Dynamic Content
    print("\n" + "="*70)
    print("DEMO 3: DYNAMIC WEB CONTENT")
    print("="*70)
    pause(1, "Web servers can execute .poo scripts (like PHP)...")
    pause(1, "Let's check server info...")

    type_command("lynx bbs.cyberspace.net/serverinfo.poo")
    exit_code, stdout, stderr = attacker.execute_command("http-get /serverinfo.poo")
    lines = stdout.split('\n')[:30]
    print('\n'.join(lines))

    pause(3, "See? That content is generated in REAL-TIME on the server!")

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 4: Missions
    print("\n" + "="*70)
    print("DEMO 4: MISSIONS")
    print("="*70)
    pause(1, "There are multiple missions to complete...")

    type_command("cat /missions/README")
    exit_code, stdout, stderr = attacker.execute_command("cat /missions/README")
    lines = stdout.split('\n')[:35]
    print('\n'.join(lines))

    pause(3, "Each mission takes you deeper into the network...")

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 5: The Nexus
    print("\n" + "="*70)
    print("DEMO 5: THE MYSTERIOUS NEXUS")
    print("="*70)
    pause(1, "There's something strange on the network...")
    pause(1, "At nexus.unknown (192.168.99.1)...")

    type_command("ping 192.168.99.1")
    exit_code, stdout, stderr = attacker.execute_command("ping 192.168.99.1")
    print(stdout[:500])

    pause(2, "It responds... but what IS it?")
    pause(2, "You'll have to explore to find out...")

    pause(2, "Press ENTER to continue...")
    input()

    # Demo 6: System Processes
    print("\n" + "="*70)
    print("DEMO 6: SYSTEM STATUS")
    print("="*70)
    pause(1, "Let's check what processes are running...")

    type_command("ps")
    exit_code, stdout, stderr = attacker.execute_command("ps")
    print(stdout)

    pause(2, "Everything is a real Unix process in the virtual kernel!")

    pause(2, "Press ENTER to continue...")
    input()

    # Finale
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("""
You've seen:
  ✓ Network scanning and discovery
  ✓ Web browsing with lynx
  ✓ Dynamic server-side content (.poo scripts)
  ✓ Mission system
  ✓ The mysterious Nexus
  ✓ Real Unix processes and filesystem

Now it's YOUR turn to explore!

To start playing:
  ./play.py              - Full interactive game
  ./interactive_test.py  - Interactive test mode (recommended)

The network awaits...

                        December 24, 1990
                     Something is happening...
                      Are you ready to find out?

""")

    pause(2, "Press ENTER to exit...")
    input()


if __name__ == '__main__':
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
        sys.exit(0)
