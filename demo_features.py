#!/usr/bin/env python3
"""
Demo of new features in Poodillion 2
- chmod, chown, ln, cp, mv commands
- Execute permission enforcement
- SUID/SGID privilege escalation
- VirtualScript interpreter
"""

from core.system import UnixSystem


def main():
    print("=" * 70)
    print(" POODILLION 2 - New Features Demo")
    print("=" * 70)

    system = UnixSystem('demo-system')
    system.login('root', 'root')

    # Create /usr/local/bin
    system.vfs.mkdir('/usr/local/bin', 0o755, 0, 0, 1)

    print("\n### 1. File Management Commands ###\n")

    # Test cp and mv
    print("$ echo 'original content' > /tmp/file1.txt")
    system.execute_command('echo "original content" > /tmp/file1.txt')

    print("$ cp /tmp/file1.txt /tmp/file2.txt")
    system.execute_command('cp /tmp/file1.txt /tmp/file2.txt')

    print("$ cat /tmp/file2.txt")
    ec, out, err = system.execute_command('cat /tmp/file2.txt')
    print(out)

    print("$ mv /tmp/file1.txt /tmp/renamed.txt")
    system.execute_command('mv /tmp/file1.txt /tmp/renamed.txt')

    print("$ ls /tmp/*.txt")
    ec, out, err = system.execute_command('ls /tmp/*.txt 2>/dev/null || echo "file1.txt no longer exists"')
    # Use find instead
    entries = system.vfs.list_dir('/tmp', 1)
    txt_files = [name for name, _ in entries if name.endswith('.txt')]
    print(f"Files in /tmp: {', '.join(txt_files)}\n")

    print("\n### 2. Permissions (chmod) ###\n")

    print("$ touch /tmp/script.sh")
    system.execute_command('touch /tmp/script.sh')

    print("$ chmod 755 /tmp/script.sh")
    system.execute_command('chmod 755 /tmp/script.sh')

    print("$ ls -l /tmp/script.sh")
    ec, out, err = system.execute_command('ls -l /tmp/script.sh')
    print(out)

    print("\n### 3. SUID Bits ###\n")

    print("$ chmod 4755 /tmp/script.sh  # Set SUID bit")
    system.execute_command('chmod 4755 /tmp/script.sh')

    print("$ ls -l /tmp/script.sh")
    ec, out, err = system.execute_command('ls -l /tmp/script.sh')
    print(out)

    print("\n### 4. Symbolic Links ###\n")

    print("$ ln -s /etc/hostname /tmp/hostname_link")
    system.execute_command('ln -s /etc/hostname /tmp/hostname_link')

    print("$ ls -l /tmp/hostname_link")
    ec, out, err = system.execute_command('ls -l /tmp/hostname_link')
    print(out)

    print("$ cat /tmp/hostname_link")
    ec, out, err = system.execute_command('cat /tmp/hostname_link')
    print(out)

    print("\n### 5. VirtualScript - Simple Script ###\n")

    # Create a simple hello world script
    hello_script = b"""#!/usr/bin/virtualscript
# Simple VirtualScript example
print("=== VirtualScript Execution ===")
print(f"Script arguments: {args}")
print(f"Current UID: {process.uid}")
print(f"Current directory inode: {process.cwd}")
"""

    system.vfs.create_file('/usr/local/bin/hello', 0o755, 0, 0, hello_script, 1)

    print("Created /usr/local/bin/hello with VirtualScript content")
    print("$ hello arg1 arg2 arg3")
    ec, out, err = system.execute_command('hello arg1 arg2 arg3')
    print(out)

    print("\n### 6. VirtualScript - VFS Access ###\n")

    # Create a script that lists files
    list_script = b"""#!/usr/bin/virtualscript
# List files using VFS API
if len(args) == 0:
    path = "/etc"
else:
    path = args[0]

print(f"Files in {path}:")
try:
    entries = vfs.list(path)
    for name in entries:
        info = vfs.stat(f"{path}/{name}")
        file_type = "DIR" if info['is_dir'] else "FILE"
        print(f"  [{file_type}] {name}")
except Exception as e:
    error(f"Error: {e}")
    exit(1)
"""

    system.vfs.create_file('/usr/local/bin/lsvfs', 0o755, 0, 0, list_script, 1)

    print("$ lsvfs /bin")
    ec, out, err = system.execute_command('lsvfs /bin')
    print(out)

    print("\n### 7. VirtualScript with SUID - Privilege Escalation ###\n")

    # Create a SUID script that reads privileged files
    suid_script = b"""#!/usr/bin/virtualscript
# SUID script demonstrating privilege escalation
print(f"Real UID: {process.uid}")
print(f"Effective UID: {process.euid}")
print()

if process.euid == 0:
    print("Running with ROOT privileges via SUID!")
    print("Reading /etc/shadow (normally only root can read):")
    print()
    shadow_content = vfs.read("/etc/shadow")
    print(shadow_content)
else:
    error("ERROR: Not running with elevated privileges")
    exit(1)
"""

    system.vfs.create_file('/usr/local/bin/read_shadow', 0o4755, 0, 0, suid_script, 1)

    print("Created /usr/local/bin/read_shadow with SUID bit (mode 4755)")
    print("$ ls -l /usr/local/bin/read_shadow")
    ec, out, err = system.execute_command('ls -l /usr/local/bin/read_shadow')
    print(out)

    print("$ read_shadow")
    ec, out, err = system.execute_command('read_shadow')
    print(out)

    print("\n### 8. chown Command ###\n")

    # Add a test user
    system.add_user('alice', 'test123', 1001, '/home/alice')

    print("$ touch /tmp/alice_file")
    system.execute_command('touch /tmp/alice_file')

    print("$ chown alice /tmp/alice_file")
    system.execute_command('chown alice /tmp/alice_file')

    print("$ ls -l /tmp/alice_file")
    ec, out, err = system.execute_command('ls -l /tmp/alice_file')
    print(out)

    print("=" * 70)
    print(" All features demonstrated successfully!")
    print("=" * 70)


if __name__ == '__main__':
    main()
