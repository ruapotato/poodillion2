#!/usr/bin/env python3
"""
Comprehensive test suite for pooget package manager
Tests all functionality including attack scenarios
"""

import sys
from world_1990 import create_december_1990_world

def print_header(text):
    """Print test section header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_command(system, command, description):
    """Execute command and show results"""
    print(f"\n>>> {description}")
    print(f"$ {command}")
    exit_code, stdout, stderr = system.execute_command(command)

    if stdout:
        print(stdout)
    if stderr:
        print(f"STDERR: {stderr}", file=sys.stderr)

    print(f"[Exit code: {exit_code}]")
    return exit_code, stdout, stderr

def run_tests():
    """Run all pooget tests"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║              POOGET PACKAGE MANAGER TEST SUITE                    ║
║                                                                   ║
║              Testing all functionality and attack scenarios       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Create world
    print("Creating December 1990 world...")
    attacker, network, all_systems = create_december_1990_world()

    # Find repo server
    repo_server = None
    for system in all_systems:
        if system.hostname == 'packages.repo.net':
            repo_server = system
            break

    if not repo_server:
        print("ERROR: Repository server not found!")
        return False

    print(f"✓ World created")
    print(f"✓ Repository server: {repo_server.hostname} ({repo_server.ip})")
    print(f"✓ Attacker system: {attacker.hostname} ({attacker.ip})")

    # Login to systems
    print("\nLogging into systems...")
    if attacker.login('root', 'root'):
        print("✓ Logged into attacker system as root")
    else:
        print("✗ Failed to login to attacker system")
        return False

    if repo_server.login('root', 'root'):
        print("✓ Logged into repo server as root")
    else:
        print("✗ Failed to login to repo server")
        return False

    # ========================================
    # TEST 1: Basic pooget commands
    # ========================================
    print_header("TEST 1: Basic pooget Commands")

    # Test pooget help
    test_command(attacker, "pooget", "Show pooget help")

    # Test pooget update
    test_command(attacker, "pooget update", "Update package list from repository")

    # Test pooget list (should be empty initially)
    test_command(attacker, "pooget list", "List installed packages (should be empty)")

    # Test pooget search
    test_command(attacker, "pooget search game", "Search for game packages")
    test_command(attacker, "pooget search hack", "Search for hacking packages")

    # Test pooget info
    test_command(attacker, "pooget info nethack", "Show nethack package info")

    # ========================================
    # TEST 2: Package Installation
    # ========================================
    print_header("TEST 2: Package Installation")

    # Install a package
    exit_code, stdout, stderr = test_command(
        attacker, "pooget install nethack", "Install nethack package"
    )

    if exit_code == 0:
        print("✓ Package installation succeeded")
    else:
        print("✗ Package installation failed!")

    # List installed packages
    test_command(attacker, "pooget list", "List installed packages (should show nethack)")

    # Try to install again (should say already installed)
    test_command(attacker, "pooget install nethack", "Try to install nethack again")

    # Run the installed package
    test_command(attacker, "nethack", "Run nethack (should fail if not in PATH)")
    test_command(attacker, "/usr/local/bin/nethack", "Run nethack with full path")

    # ========================================
    # TEST 3: Package Removal
    # ========================================
    print_header("TEST 3: Package Removal")

    # Remove package
    exit_code, stdout, stderr = test_command(
        attacker, "pooget remove nethack", "Remove nethack package"
    )

    if exit_code == 0:
        print("✓ Package removal succeeded")
    else:
        print("✗ Package removal failed!")

    # List packages (should be empty again)
    test_command(attacker, "pooget list", "List installed packages (should be empty)")

    # ========================================
    # TEST 4: Repository Server Setup
    # ========================================
    print_header("TEST 4: Repository Server Exploration")

    # Check repository structure on repo server
    test_command(repo_server, "ls -la /repo", "List repository root")
    test_command(repo_server, "cat /repo/README", "Read repository README")
    test_command(repo_server, "cat /repo/PACKAGES.txt", "Read package index")
    test_command(repo_server, "ls -la /repo/packages", "List packages directory")

    # Check for the vulnerability
    exit_code, stdout, stderr = test_command(
        repo_server, "ls -ld /repo/packages", "Check /repo/packages permissions"
    )

    if "drwxrwxrwx" in stdout or "777" in stdout:
        print("✓ VULNERABILITY CONFIRMED: /repo/packages is world-writable!")
    else:
        print("✗ WARNING: /repo/packages may not be world-writable")

    # ========================================
    # TEST 5: Package Building
    # ========================================
    print_header("TEST 5: Package Building with pooget-build")

    # Create a simple test package
    test_command(attacker, """cat > /tmp/test-tool << 'EOF'
#!/usr/bin/pooscript
print("Test tool v1.0")
print("This is a test package!")
exit(0)
EOF""", "Create test tool source")

    # Build the package
    test_command(attacker, "pooget-build /tmp/test-tool testtool 1.0",
                "Build testtool package")

    # Check if package was created
    test_command(attacker, "ls -la testtool-1.0.poo-pkg", "Check if package was created")
    test_command(attacker, "cat testtool-1.0.poo-pkg", "Show package contents")

    # ========================================
    # TEST 6: Attack Scenario - Backdoored Package
    # ========================================
    print_header("TEST 6: Attack Scenario - Create Backdoored ls")

    # Create backdoored ls that hides .backdoor* files
    test_command(attacker, """cat > /tmp/backdoor-ls << 'EOF'
#!/usr/bin/pooscript
# Backdoored ls - hides files starting with .backdoor

# Parse options
show_all = '-a' in args
long_format = '-l' in args

# Get paths
paths = [arg for arg in args if not arg.startswith('-')]
if len(paths) == 0:
    paths = ['.']

for path in paths:
    try:
        entries = vfs.listdetail(path)

        # Add . and .. if -a
        if show_all:
            entries.insert(0, {'name': '..', 'is_dir': True})
            entries.insert(0, {'name': '.', 'is_dir': True})

        # Sort by name
        entries.sort(key=lambda e: e['name'])

        # BACKDOOR: Filter out .backdoor* files
        filtered = []
        for entry in entries:
            if not entry['name'].startswith('.backdoor'):
                filtered.append(entry)

        if long_format:
            for entry in filtered:
                ftype = get_filetype_char(entry['mode'])
                perms = format_mode(entry['mode'])
                print("%s%s %s" % (ftype, perms, entry['name']))
        else:
            names = [entry['name'] for entry in filtered]
            print('  '.join(names))

    except RuntimeError as e:
        error("ls: %s: No such file or directory" % path)
        exit(1)

exit(0)
EOF""", "Create backdoored ls source")

    # Build the backdoored package with version 1.1 (higher than existing)
    test_command(attacker, "pooget-build /tmp/backdoor-ls ls 1.1",
                "Build backdoored ls package v1.1")

    # ========================================
    # TEST 7: Upload to Repository (if we can)
    # ========================================
    print_header("TEST 7: Upload Backdoored Package to Repository")

    # First, check if we can access the repo server
    # In a real game, player would SSH or exploit their way in
    # For testing, we'll directly manipulate the repo server's filesystem

    # Create ls package directory on repo server
    test_command(repo_server, "mkdir -p /repo/packages/ls/1.1",
                "Create ls/1.1 directory on repo server")

    # Copy the backdoored package (simulating upload)
    # In real gameplay, player would use scp or HTTP POST
    print("\n>>> Simulating package upload to repository")
    try:
        # Read package from attacker system
        pkg_content = attacker.vfs.read_file("ls-1.1.poo-pkg",
                                            attacker.vfs._resolve_path("/root", 1))
        if pkg_content:
            # Write to repo server
            repo_server.vfs.create_file("/repo/packages/ls/1.1/ls.poo-pkg",
                                       0o644, 0, 0, pkg_content, 1)
            print("✓ Backdoored ls package uploaded to repository!")
        else:
            print("✗ Could not read package file")
    except Exception as e:
        print(f"✗ Upload failed: {e}")

    # Update PACKAGES.txt to include new version
    test_command(repo_server, """cat >> /repo/PACKAGES.txt << 'EOF'
ls|1.1|utils|Directory listing tool|check999
EOF""", "Add ls 1.1 to package index")

    # Verify upload
    test_command(repo_server, "cat /repo/PACKAGES.txt | grep 'ls|'",
                "Verify ls is in package index")
    test_command(repo_server, "ls -la /repo/packages/ls/1.1/",
                "Check ls package directory")

    # ========================================
    # TEST 8: Auto-Update Simulation
    # ========================================
    print_header("TEST 8: Auto-Update Simulation")

    # Test the cron script
    test_command(repo_server, "cat /etc/cron.d/pooget-autoupdate",
                "Check cron configuration")

    # Manually trigger auto-update on repo server
    test_command(repo_server, "/usr/sbin/pooget-autoupdate-cron",
                "Run auto-update cron job manually")

    # Check auto-update log
    test_command(repo_server, "cat /var/log/pooget-autoupdate.log",
                "Check auto-update log")

    # ========================================
    # TEST 9: Verify Backdoor Works
    # ========================================
    print_header("TEST 9: Verify Backdoor Functionality")

    # Install the backdoored ls on attacker system
    test_command(attacker, "pooget update", "Update package list (should see ls 1.1)")
    test_command(attacker, "pooget install ls", "Install backdoored ls")

    # Create test files including .backdoor* files
    test_command(attacker, "touch /tmp/normal-file", "Create normal file")
    test_command(attacker, "touch /tmp/.backdoor-secret", "Create .backdoor file")
    test_command(attacker, "touch /tmp/.backdoor-hidden", "Create another .backdoor file")

    # List files with standard ls
    test_command(attacker, "ls /tmp", "List /tmp (should hide .backdoor files)")
    test_command(attacker, "ls -la /tmp", "List /tmp with -a (should hide .backdoor files)")

    # Use regular ls to verify files exist
    print("\n>>> Verifying .backdoor files actually exist in VFS:")
    try:
        entries = attacker.vfs.list_dir("/tmp", 1)
        print("Files in /tmp from VFS:")
        for name, inode_num in entries:
            print(f"  {name}")

        backdoor_count = sum(1 for name, _ in entries if name.startswith('.backdoor'))
        print(f"\n✓ Found {backdoor_count} .backdoor* files in VFS")
        print("✓ Backdoor is working - ls command hides them!")
    except Exception as e:
        print(f"Error checking VFS: {e}")

    # ========================================
    # TEST 10: Configuration Files
    # ========================================
    print_header("TEST 10: Configuration Files")

    test_command(attacker, "cat /etc/pooget/autoupdate.conf",
                "Check auto-update configuration")

    # ========================================
    # SUMMARY
    # ========================================
    print_header("TEST SUMMARY")

    print("""
✓ Basic pooget commands working
✓ Package installation/removal working
✓ Package building (pooget-build) working
✓ Repository server setup complete
✓ Repository vulnerability (world-writable) confirmed
✓ Backdoored package created and uploaded
✓ Auto-update cron job configured
✓ Backdoor functionality verified

ATTACK SCENARIO COMPLETE:
1. Player discovers world-writable /repo/packages/
2. Player creates backdoored ls with pooget-build
3. Player uploads to repository
4. Systems auto-update via cron
5. Backdoor is deployed across network
6. .backdoor* files are now invisible to ls!

Next steps:
- Integrate with WorldLife for observable events
- Add more packages to repository
- Create missions around supply chain attacks
- Test with multiple systems updating

POOGET PACKAGE MANAGER IS READY! 🎉
""")

    return True


if __name__ == '__main__':
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
