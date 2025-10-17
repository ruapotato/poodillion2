"""
Script Installer - Install PooScript commands into VFS
Reads scripts from scripts/ directory and installs them into the virtual filesystem
"""

import os


def install_scripts(vfs, verbose=False):
    """
    Install all PooScript files from scripts/ into the VFS

    Args:
        vfs: VFS instance to install scripts into
        verbose: If True, print installation messages
    """
    # Get the base directory (parent of core/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(base_dir, 'scripts')

    # Mapping of script directories to VFS paths
    mappings = {
        'bin': '/bin',
        'usr_bin': '/usr/bin',
        'sbin': '/sbin',
        'www': '/www',
        'secrets': '/secrets',
        'etc': '/etc',
        'tmp': '/tmp',
        'var/log': '/var/log',
    }

    installed_count = 0

    for script_subdir, vfs_path in mappings.items():
        # Handle nested directories like 'var/log'
        script_path = os.path.join(scripts_dir, script_subdir.replace('/', os.sep))

        # Skip if directory doesn't exist
        if not os.path.isdir(script_path):
            continue

        # Ensure VFS directory exists (create parent directories if needed)
        path_parts = vfs_path.strip('/').split('/')
        current_path = ''
        for part in path_parts:
            current_path += '/' + part
            if not vfs.stat(current_path, 1):
                vfs.mkdir(current_path, 0o755, 0, 0, 1)

        # Install each script file
        for filename in os.listdir(script_path):
            file_path = os.path.join(script_path, filename)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Read script content
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()

                # Determine permissions (executable for /bin, readable for others)
                mode = 0o755 if vfs_path in ['/bin', '/usr/bin', '/sbin'] else 0o644

                # Install into VFS
                vfs_file_path = f'{vfs_path}/{filename}'
                result = vfs.create_file(vfs_file_path, mode, 0, 0, content, 1)

                if result:
                    installed_count += 1
                    if verbose:
                        print(f"  Installed: {vfs_file_path}")

            except Exception as e:
                if verbose:
                    print(f"  Warning: Failed to install {filename}: {e}")

    # Create /bin/sh symlink to pooshell
    if vfs.stat('/bin/pooshell', 1):
        vfs.symlink('/bin/pooshell', '/bin/sh', 0, 0, 1)
        if verbose:
            print(f"  Created symlink: /bin/sh -> /bin/pooshell")

    if verbose:
        print(f"  Total PooScript commands installed: {installed_count}")
    return installed_count
