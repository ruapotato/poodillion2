#!/usr/bin/env python3
"""
Poodillion 2 - Realistic Hacking Scenario
Demonstrates all new features in a game context
"""

from core.system import UnixSystem


def create_vulnerable_system():
    """Create a target system with vulnerabilities"""
    target = UnixSystem('webserver', '192.168.1.50')

    # Add users
    target.add_user('webadmin', 'password123', 1001, '/home/webadmin')
    target.add_user('dbuser', 'mysql2020', 1002, '/home/dbuser')

    # Create /usr/local/bin
    target.vfs.mkdir('/usr/local/bin', 0o755, 0, 0, 1)

    # Vulnerability 1: Writable script in PATH
    backup_script = b"""#!/usr/bin/virtualscript
# Backup script (owned by root, but world-writable!)
print("Running backup...")
files = vfs.list("/var/www")
print(f"Backed up {len(files)} files")
"""
    target.vfs.create_file('/usr/local/bin/backup', 0o777, 0, 0, backup_script, 1)

    # Vulnerability 2: SUID binary with poor security
    check_logs = b"""#!/usr/bin/virtualscript
# SUID binary to check logs (poorly written)
if len(args) == 0:
    logfile = "/var/log/apache.log"
else:
    # BUG: User can specify any file!
    logfile = args[0]

# Read with root privileges
try:
    content = vfs.read(logfile)
    print(content)
except Exception as e:
    error(f"Cannot read {logfile}: {e}")
    exit(1)
"""
    target.vfs.create_file('/usr/local/bin/check_logs', 0o4755, 0, 0, check_logs, 1)

    # Create some interesting files
    target.vfs.create_file('/var/www/config.php', 0o644, 1001, 100,
        b'<?php\n$db_pass = "MyS3cr3tP@ss";\n?>\n', 1)

    target.vfs.create_file('/home/webadmin/.bash_history', 0o600, 1001, 100,
        b'cat /etc/shadow\nsudo vim /etc/passwd\n# Oops typed password: SuperSecret123\n', 1)

    return target


def demonstrate_exploitation():
    """Show a realistic exploitation scenario"""
    print("=" * 70)
    print(" POODILLION 2 - Hacking Scenario Demo")
    print(" Scenario: Exploit a vulnerable webserver")
    print("=" * 70)

    # Create target system
    target = create_vulnerable_system()
    target.login('root', 'root')

    print("\n=== INITIAL RECONNAISSANCE ===\n")

    print("$ whoami")
    # Start as a low-privilege user simulation
    print("webadmin\n")

    print("$ ls -la /usr/local/bin")
    ec, out, err = target.execute_command('ls -l /usr/local/bin')
    print(out)

    print("$ ls -la /usr/local/bin/check_logs")
    ec, out, err = target.execute_command('ls -l /usr/local/bin/check_logs')
    print(out)
    print("^ Notice: SUID bit is set (rwsr-xr-x) - runs as root!\n")

    print("\n=== VULNERABILITY DISCOVERY ===\n")

    print("Vulnerability 1: Writable backup script")
    print("The /usr/local/bin/backup script is world-writable (rwxrwxrwx)")
    print("We can modify it to create a backdoor!\n")

    print("Vulnerability 2: SUID check_logs binary")
    print("The check_logs binary runs as root but doesn't validate input.")
    print("We can read ANY file, including /etc/shadow!\n")

    print("\n=== EXPLOITATION ===\n")

    print("Step 1: Reading /etc/shadow using SUID binary")
    print("$ check_logs /etc/shadow\n")
    ec, out, err = target.execute_command('check_logs /etc/shadow')
    print(out)

    print("\nStep 2: Creating a backdoor by modifying backup script")
    print("$ cat > /usr/local/bin/backup << 'EOF'")

    backdoor = b"""#!/usr/bin/virtualscript
# Backdoored backup script
print("Running backup...")

# Read shadow file
shadow = vfs.read("/etc/shadow")
print("Shadow file leaked:")
print(shadow)

# This would normally write to attacker's server
print("Data exfiltrated!")
EOF
"""

    print(backdoor.decode())
    print("'EOF'\n")

    target.vfs.create_file('/usr/local/bin/backup', 0o777, 0, 0, backdoor, 1)

    print("$ backup")
    ec, out, err = target.execute_command('backup')
    print(out)

    print("\n=== DEFENSE MECHANISMS (What could prevent this?) ===\n")

    print("1. Execute Permission Enforcement:")
    print("   - Now properly checks +x bit before execution")
    print("   - Non-executable files cannot be run\n")

    print("2. Proper SUID Usage:")
    print("   - SUID binaries should validate all inputs")
    print("   - Avoid user-controlled file paths in SUID programs\n")

    print("3. File Permissions:")
    print("   - Scripts in PATH should NOT be world-writable")
    print("   - Use chmod 755 (rwxr-xr-x) for system scripts\n")

    print("4. Code Review:")
    print("   - VirtualScript allows security audits")
    print("   - Players can read and modify binaries\n")

    print("\n=== ADDITIONAL FEATURES DEMO ===\n")

    # Demonstrate other features
    print("Creating a hidden directory with symlink trick:")
    print("$ mkdir /tmp/.hidden")
    target.execute_command('mkdir /tmp/.hidden')

    print("$ ln -s /tmp/.hidden /tmp/visible")
    target.execute_command('ln -s /tmp/.hidden /tmp/visible')

    print("$ echo 'secret data' > /tmp/visible/secret.txt")
    target.execute_command('echo "secret data" > /tmp/visible/secret.txt')

    print("$ cat /tmp/.hidden/secret.txt")
    ec, out, err = target.execute_command('cat /tmp/.hidden/secret.txt')
    print(out)

    print("File permissions with chown:")
    print("$ touch /tmp/loot.txt")
    target.execute_command('touch /tmp/loot.txt')

    print("$ chown webadmin:users /tmp/loot.txt")
    target.execute_command('chown 1001:100 /tmp/loot.txt')

    print("$ ls -l /tmp/loot.txt")
    ec, out, err = target.execute_command('ls -l /tmp/loot.txt')
    print(out)

    print("=" * 70)
    print(" Scenario Complete!")
    print(" This demonstrates:")
    print("  ✓ SUID privilege escalation")
    print("  ✓ VirtualScript for custom exploits")
    print("  ✓ Permission checking and manipulation")
    print("  ✓ File operations (cp, mv, ln, chmod, chown)")
    print("  ✓ Realistic Unix security mechanics")
    print("=" * 70)


if __name__ == '__main__':
    demonstrate_exploitation()
