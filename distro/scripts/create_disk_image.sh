#!/bin/bash
# Create a bootable disk image for QEMU
# This creates a raw disk image with extlinux bootloader

set -e

OUTPUT="/home/david/poodillion2/distro/poodillion.img"
SIZE_MB=64
BIN_DIR="/home/david/poodillion2/bin"
ROOTFS_DIR="/home/david/poodillion2/distro/rootfs"

echo "=== Creating PoodillionOS Disk Image ==="
echo "Output: $OUTPUT"
echo "Size: ${SIZE_MB}MB"

# Create empty disk image
dd if=/dev/zero of="$OUTPUT" bs=1M count=$SIZE_MB 2>/dev/null

# Create partition table and filesystem
# This requires root for losetup
if [ "$(id -u)" != "0" ]; then
    echo ""
    echo "Note: Full disk image creation requires root."
    echo "Creating minimal initramfs-only test image instead..."
    echo ""

    # Create a minimal test that can run with -kernel and -initrd
    INITRD_DIR="/tmp/poodillion_initrd_$$"
    mkdir -p "$INITRD_DIR"/{bin,sbin,etc,dev,proc,sys,tmp,root}

    # Copy all binaries
    cp "$BIN_DIR"/* "$INITRD_DIR/bin/"
    ln -sf /bin/init "$INITRD_DIR/sbin/init"
    ln -sf /bin/psh "$INITRD_DIR/bin/sh"

    # Create minimal config
    echo "root:x:0:0:root:/root:/bin/psh" > "$INITRD_DIR/etc/passwd"
    echo "root:x:0:" > "$INITRD_DIR/etc/group"
    echo "poodillion" > "$INITRD_DIR/etc/hostname"

    # Create the initramfs
    cd "$INITRD_DIR"
    find . | cpio -o -H newc 2>/dev/null | gzip > "/home/david/poodillion2/distro/poodillion-full.cpio.gz"
    rm -rf "$INITRD_DIR"

    SIZE=$(ls -lh /home/david/poodillion2/distro/poodillion-full.cpio.gz | awk '{print $5}')
    echo "Created: /home/david/poodillion2/distro/poodillion-full.cpio.gz ($SIZE)"
    echo ""
    echo "To test with QEMU (using host kernel):"
    echo ""
    echo "  qemu-system-x86_64 -m 256M \\"
    echo "    -kernel /boot/vmlinuz-\$(uname -r) \\"
    echo "    -initrd /home/david/poodillion2/distro/poodillion-full.cpio.gz \\"
    echo "    -append 'console=ttyS0 init=/bin/init' \\"
    echo "    -nographic"
    echo ""
    echo "Or for graphical:"
    echo ""
    echo "  qemu-system-x86_64 -m 256M \\"
    echo "    -kernel /boot/vmlinuz-\$(uname -r) \\"
    echo "    -initrd /home/david/poodillion2/distro/poodillion-full.cpio.gz \\"
    echo "    -append 'console=tty0 init=/bin/init'"
    exit 0
fi

# If running as root, create full disk image
echo "Creating partition..."
parted -s "$OUTPUT" mklabel msdos
parted -s "$OUTPUT" mkpart primary ext2 1MiB 100%
parted -s "$OUTPUT" set 1 boot on

# Setup loop device
LOOP=$(losetup -f --show -P "$OUTPUT")
echo "Loop device: $LOOP"

# Format partition
mkfs.ext2 -L POODILLION "${LOOP}p1"

# Mount and populate
MOUNT_DIR="/tmp/poodillion_mount_$$"
mkdir -p "$MOUNT_DIR"
mount "${LOOP}p1" "$MOUNT_DIR"

# Copy rootfs
cp -a "$ROOTFS_DIR"/* "$MOUNT_DIR/"

# Install bootloader (extlinux/syslinux)
if command -v extlinux &> /dev/null; then
    mkdir -p "$MOUNT_DIR/boot"
    cp /boot/vmlinuz-$(uname -r) "$MOUNT_DIR/boot/vmlinuz"

    # Create extlinux config
    cat > "$MOUNT_DIR/boot/extlinux.conf" << EOF
DEFAULT poodillion
LABEL poodillion
    LINUX /boot/vmlinuz
    APPEND init=/bin/init root=/dev/sda1 console=tty0
EOF

    extlinux --install "$MOUNT_DIR/boot"
    dd if=/usr/lib/syslinux/mbr/mbr.bin of="$LOOP" bs=440 count=1 conv=notrunc 2>/dev/null
fi

# Cleanup
umount "$MOUNT_DIR"
losetup -d "$LOOP"
rmdir "$MOUNT_DIR"

echo ""
echo "=== Disk Image Created ==="
echo "Output: $OUTPUT"
echo ""
echo "To test with QEMU:"
echo "  qemu-system-x86_64 -hda $OUTPUT -m 256M"
