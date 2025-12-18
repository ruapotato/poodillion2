#!/bin/bash
# Create PoodillionOS initramfs
# This creates a minimal initramfs for booting

set -e

INITRAMFS_DIR="${1:-/home/david/poodillion2/distro/initramfs}"
OUTPUT="${2:-/home/david/poodillion2/distro/initramfs.cpio.gz}"
BIN_DIR="/home/david/poodillion2/bin"

echo "=== Creating PoodillionOS Initramfs ==="

# Clean and create structure
rm -rf "$INITRAMFS_DIR"
mkdir -p "$INITRAMFS_DIR"/{bin,sbin,etc,dev,proc,sys,mnt/root,tmp}

# Copy essential binaries for boot
echo "Copying essential binaries..."
ESSENTIAL_BINS="init getty login psh mount umount cat echo ls"
for bin in $ESSENTIAL_BINS; do
    if [ -f "$BIN_DIR/$bin" ]; then
        cp "$BIN_DIR/$bin" "$INITRAMFS_DIR/bin/"
        echo "  + $bin"
    else
        echo "  - $bin (not found)"
    fi
done

# Create symlinks
ln -sf /bin/init "$INITRAMFS_DIR/sbin/init"
ln -sf /bin/psh "$INITRAMFS_DIR/bin/sh"

# Create init script (the actual /init that kernel runs)
cat > "$INITRAMFS_DIR/init" << 'INITSCRIPT'
#!/bin/psh
# PoodillionOS initramfs init script

# Mount essential filesystems
/bin/mount -t proc proc /proc
/bin/mount -t sysfs sysfs /sys
/bin/mount -t devtmpfs devtmpfs /dev

# Display boot message
/bin/echo "PoodillionOS initramfs starting..."
/bin/echo ""

# Try to find and mount root filesystem
# For now, just start a shell
/bin/echo "Starting emergency shell..."
exec /bin/psh
INITSCRIPT
chmod 755 "$INITRAMFS_DIR/init"

# Also create a C-based init wrapper that will exec the script
# This is more reliable as the kernel expects an ELF binary
cp "$BIN_DIR/init" "$INITRAMFS_DIR/init"

# Create minimal /etc/passwd
cat > "$INITRAMFS_DIR/etc/passwd" << 'EOF'
root:x:0:0:root:/:/bin/psh
EOF

# Create the cpio archive
echo "Creating initramfs archive..."
cd "$INITRAMFS_DIR"
find . | cpio -o -H newc 2>/dev/null | gzip > "$OUTPUT"

SIZE=$(ls -lh "$OUTPUT" | awk '{print $5}')
echo ""
echo "=== Initramfs Created ==="
echo "Output: $OUTPUT"
echo "Size: $SIZE"
echo ""
echo "To test with QEMU:"
echo "  qemu-system-i386 -kernel /boot/vmlinuz -initrd $OUTPUT -append 'console=ttyS0' -nographic"
