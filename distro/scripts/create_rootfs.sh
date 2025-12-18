#!/bin/bash
# Create PoodillionOS root filesystem
# Run with sudo

set -e

ROOTFS_DIR="${1:-/home/david/poodillion2/distro/rootfs}"
BIN_DIR="/home/david/poodillion2/bin"

echo "=== Creating PoodillionOS Root Filesystem ==="
echo "Target: $ROOTFS_DIR"

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$ROOTFS_DIR"/{bin,sbin,etc,dev,proc,sys,tmp,var,home,root,lib,usr/bin,usr/lib}
chmod 1777 "$ROOTFS_DIR/tmp"
chmod 700 "$ROOTFS_DIR/root"

# Copy all binaries
echo "Copying binaries..."
cp "$BIN_DIR"/* "$ROOTFS_DIR/bin/"

# Create essential symlinks
ln -sf /bin/init "$ROOTFS_DIR/sbin/init" 2>/dev/null || true
ln -sf /bin/psh "$ROOTFS_DIR/bin/sh" 2>/dev/null || true

# Create /etc/passwd
echo "Creating /etc/passwd..."
cat > "$ROOTFS_DIR/etc/passwd" << 'EOF'
root:x:0:0:root:/root:/bin/psh
nobody:x:65534:65534:nobody:/:/bin/false
EOF

# Create /etc/group
echo "Creating /etc/group..."
cat > "$ROOTFS_DIR/etc/group" << 'EOF'
root:x:0:
users:x:100:
nobody:x:65534:
EOF

# Create /etc/shadow (no passwords)
cat > "$ROOTFS_DIR/etc/shadow" << 'EOF'
root::0:0:99999:7:::
nobody:*:0:0:99999:7:::
EOF
chmod 600 "$ROOTFS_DIR/etc/shadow"

# Create /etc/hostname
echo "poodillion" > "$ROOTFS_DIR/etc/hostname"

# Create /etc/hosts
cat > "$ROOTFS_DIR/etc/hosts" << 'EOF'
127.0.0.1   localhost
127.0.1.1   poodillion
EOF

# Create /etc/fstab
cat > "$ROOTFS_DIR/etc/fstab" << 'EOF'
# <file system>  <mount point>  <type>  <options>       <dump>  <pass>
proc             /proc          proc    defaults        0       0
sysfs            /sys           sysfs   defaults        0       0
devtmpfs         /dev           devtmpfs defaults       0       0
EOF

# Create /etc/inittab (for our init)
cat > "$ROOTFS_DIR/etc/inittab" << 'EOF'
# PoodillionOS inittab
# Format: id:runlevels:action:process

# System initialization
::sysinit:/bin/mount -t proc proc /proc
::sysinit:/bin/mount -t sysfs sysfs /sys
::sysinit:/bin/mount -t devtmpfs devtmpfs /dev
::sysinit:/bin/hostname -F /etc/hostname

# Start getty on tty1
tty1::respawn:/bin/getty /dev/tty1

# Shutdown actions
::shutdown:/bin/sync
::shutdown:/bin/umount -a
EOF

# Create /etc/profile
cat > "$ROOTFS_DIR/etc/profile" << 'EOF'
# PoodillionOS system profile
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root
export PS1='poodillion# '
export TERM=linux

echo "Welcome to PoodillionOS!"
echo "Type 'help' for available commands."
EOF

# Create /etc/motd
cat > "$ROOTFS_DIR/etc/motd" << 'EOF'

  ____                 _ _ _ _ _             ___  ____
 |  _ \ ___   ___   __| (_) | (_) ___  _ __ / _ \/ ___|
 | |_) / _ \ / _ \ / _` | | | | |/ _ \| '_ \ | | \___ \
 |  __/ (_) | (_) | (_| | | | | | (_) | | | | |_| |___) |
 |_|   \___/ \___/ \__,_|_|_|_|_|\___/|_| |_|\___/|____/

  A Data-Oriented Operating System with Typed Pipelines
  Built entirely in Mini-Nim with direct Linux syscalls

EOF

# Create device nodes (needs root)
if [ "$(id -u)" = "0" ]; then
    echo "Creating device nodes..."
    mknod -m 666 "$ROOTFS_DIR/dev/null" c 1 3 2>/dev/null || true
    mknod -m 666 "$ROOTFS_DIR/dev/zero" c 1 5 2>/dev/null || true
    mknod -m 666 "$ROOTFS_DIR/dev/random" c 1 8 2>/dev/null || true
    mknod -m 666 "$ROOTFS_DIR/dev/urandom" c 1 9 2>/dev/null || true
    mknod -m 600 "$ROOTFS_DIR/dev/console" c 5 1 2>/dev/null || true
    mknod -m 666 "$ROOTFS_DIR/dev/tty" c 5 0 2>/dev/null || true
    mknod -m 620 "$ROOTFS_DIR/dev/tty1" c 4 1 2>/dev/null || true
    mknod -m 620 "$ROOTFS_DIR/dev/tty2" c 4 2 2>/dev/null || true
    ln -sf /proc/self/fd "$ROOTFS_DIR/dev/fd" 2>/dev/null || true
    ln -sf /proc/self/fd/0 "$ROOTFS_DIR/dev/stdin" 2>/dev/null || true
    ln -sf /proc/self/fd/1 "$ROOTFS_DIR/dev/stdout" 2>/dev/null || true
    ln -sf /proc/self/fd/2 "$ROOTFS_DIR/dev/stderr" 2>/dev/null || true
else
    echo "Warning: Not running as root, skipping device node creation"
fi

# Calculate size
TOTAL_SIZE=$(du -sh "$ROOTFS_DIR" | cut -f1)
FILE_COUNT=$(find "$ROOTFS_DIR" -type f | wc -l)

echo ""
echo "=== Root Filesystem Created ==="
echo "Location: $ROOTFS_DIR"
echo "Size: $TOTAL_SIZE"
echo "Files: $FILE_COUNT"
echo ""
echo "To test with chroot (as root):"
echo "  sudo chroot $ROOTFS_DIR /bin/psh"
