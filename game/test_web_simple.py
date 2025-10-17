#!/usr/bin/env python3
"""Simple test of web server functionality"""
import sys
sys.path.insert(0, '.')

from world_1990 import create_december_1990_world

# Create the world
attacker, network, all_systems = create_december_1990_world()

# Initialize shell
attacker.shell_pid = attacker.processes.spawn(
    parent_pid=1, uid=0, gid=0, euid=0, egid=0,
    command='pooshell', args=['pooshell'],
    cwd=attacker.vfs._resolve_path('/root', 1),
    env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'},
    tags=[]
)

print("\n" + "="*70)
print("WEB SERVER TEST")
print("="*70 + "\n")

# Test httpd running on servers
print("Checking httpd processes on servers:")
for ip in ['192.168.1.10', '192.168.1.11', '192.168.3.100']:
    system = network.systems.get(ip)
    if system:
        httpd_procs = [p for p in system.processes.list_processes() if 'httpd' in p.command]
        status = f"✓ httpd running (PID {httpd_procs[0].pid})" if httpd_procs else "✗ httpd NOT running"
        print(f"  {ip}: {status}")

print("\n" + "-"*70 + "\n")

# Test basic command first
print("Testing basic command (ls /bin):")
exit_code, stdout, stderr = attacker.execute_command("ls /bin")
print(f"  Exit code: {exit_code}")
print(f"  Stdout: {stdout[:500]}")
print(f"  Stderr: {stderr[:200]}")

print("\n" + "-"*70 + "\n")

# Test lynx
print("Testing lynx (no args):")
exit_code, stdout, stderr = attacker.execute_command("lynx")
print(f"  Exit code: {exit_code}")
print(f"  Stdout length: {len(stdout)}")
print(f"  Stderr length: {len(stderr)}")
if exit_code == 0 and stdout:
    lines = stdout.split('\n')[:15]
    for line in lines:
        if line.strip():
            print(f"  {line[:68]}")
else:
    print(f"  ERROR (code {exit_code}): {stderr[:300]}")
    if not stderr and stdout:
        print(f"  Stdout: {stdout[:300]}")

print("\n" + "-"*70 + "\n")

# Test http-get
print("Testing http-get /time.poo:")
exit_code, stdout, stderr = attacker.execute_command("http-get /time.poo")
print(f"  Exit code: {exit_code}")
print(f"  Stdout length: {len(stdout)}")
print(f"  Stderr length: {len(stderr)}")
if exit_code == 0 and stdout:
    lines = stdout.split('\n')[:10]
    for line in lines:
        if line.strip():
            print(f"  {line[:68]}")
else:
    print(f"  ERROR (code {exit_code}): {stderr[:300]}")
    if not stderr and stdout:
        print(f"  Stdout: {stdout[:300]}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
