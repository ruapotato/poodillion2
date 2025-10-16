"""
Script Installer - Install PooScript commands into VFS
Reads scripts from scripts/ directory and installs them into the virtual filesystem
"""

import os


def install_scripts(vfs):
    """
    Install all PooScript files from scripts/ into the VFS

    Args:
        vfs: VFS instance to install scripts into
    """
    # Get the base directory (parent of core/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(base_dir, 'scripts')

    # Mapping of script directories to VFS paths
    mappings = {
        'bin': '/bin',
        'usr_bin': '/usr/bin',
        'sbin': '/sbin',
    }

    installed_count = 0

    for script_subdir, vfs_path in mappings.items():
        script_path = os.path.join(scripts_dir, script_subdir)

        # Skip if directory doesn't exist
        if not os.path.isdir(script_path):
            continue

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

                # Install into VFS
                vfs_file_path = f'{vfs_path}/{filename}'
                result = vfs.create_file(vfs_file_path, 0o755, 0, 0, content, 1)

                if result:
                    installed_count += 1
                    print(f"  Installed: {vfs_file_path}")

            except Exception as e:
                print(f"  Warning: Failed to install {filename}: {e}")

    # Create /bin/sh symlink to pooshell
    if vfs.stat('/bin/pooshell', 1):
        vfs.symlink('/bin/pooshell', '/bin/sh', 0, 0, 1)
        print(f"  Created symlink: /bin/sh -> /bin/pooshell")

    print(f"  Total VirtualScript commands installed: {installed_count}")
    return installed_count
