#!/usr/bin/env python3
"""Test web server functionality"""

from world_1990 import create_december_1990_world

print("="*70)
print("TESTING WEB SERVER FUNCTIONALITY")
print("="*70)
print()

# Create the world
attacker, network, all_systems = create_december_1990_world()

# Initialize shell for the attacker system
attacker.shell_pid = attacker.processes.spawn(
    parent_pid=1,
    uid=0,
    gid=0,
    euid=0,
    egid=0,
    command='pooshell',
    args=['pooshell'],
    cwd=attacker.vfs.resolve_path('/root', 1),
    env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'},
    tags=[]
)

print("✓ World created")
print()

# Test 1: Check if httpd processes are running on servers
print("TEST 1: Checking if httpd is running on servers")
print("-" * 70)

servers_to_check = [
    ('bbs.cyberspace.net', '192.168.1.10'),
    ('underground.bbs', '192.168.1.11'),
    ('vax.university.edu', '192.168.3.100'),
]

for name, ip in servers_to_check:
    system = network.systems.get(ip)
    if system:
        httpd_processes = [p for p in system.processes.list_processes() if 'httpd' in p.command]
        if httpd_processes:
            print(f"  ✓ {name:25s} - httpd running (PID {httpd_processes[0].pid})")
        else:
            print(f"  ✗ {name:25s} - httpd NOT running")

print()

# Test 2: Test lynx locally
print("TEST 2: Test lynx command (local)")
print("-" * 70)

exit_code, stdout, stderr = attacker.execute_command("lynx", attacker.shell_pid)
if exit_code == 0:
    print("✓ lynx executed successfully")
    # Show first few lines
    lines = stdout.decode('utf-8').split('\n')
    for line in lines[:20]:
        if line.strip():
            print(f"  {line}")
else:
    print(f"✗ lynx failed with exit code {exit_code}")
    print(f"  stderr: {stderr.decode('utf-8')}")

print()

# Test 3: Test http-get locally
print("TEST 3: Test http-get for default page")
print("-" * 70)

exit_code, stdout, stderr = attacker.execute_command("http-get /default.bbs", attacker.shell_pid)
if exit_code == 0:
    print("✓ http-get executed successfully")
    lines = stdout.decode('utf-8').split('\n')
    for line in lines[:15]:
        if line.strip():
            print(f"  {line}")
else:
    print(f"✗ http-get failed with exit code {exit_code}")
    if stderr:
        print(f"  stderr: {stderr.decode('utf-8')}")

print()

# Test 4: Test dynamic .poo page
print("TEST 4: Test dynamic serverinfo.poo page")
print("-" * 70)

exit_code, stdout, stderr = attacker.execute_command("http-get /serverinfo.poo", attacker.shell_pid)
if exit_code == 0:
    print("✓ serverinfo.poo executed successfully")
    lines = stdout.decode('utf-8').split('\n')
    for line in lines[:20]:
        if line.strip():
            print(f"  {line}")
else:
    print(f"✗ serverinfo.poo failed with exit code {exit_code}")
    if stderr:
        print(f"  stderr: {stderr.decode('utf-8')}")

print()

# Test 5: Check network connectivity
print("TEST 5: Network connectivity test")
print("-" * 70)

exit_code, stdout, stderr = attacker.execute_command("ping 192.168.1.10", attacker.shell_pid)
print(stdout.decode('utf-8')[:500])

print()

# Test 6: Test ps to see httpd processes
print("TEST 6: List processes on attacker")
print("-" * 70)

exit_code, stdout, stderr = attacker.execute_command("ps", attacker.shell_pid)
print(stdout.decode('utf-8'))

print()
print("="*70)
print("TEST COMPLETE")
print("="*70)
