#!/bin/bash
# Create bootable PoodillionOS ISO
# Requires: grub-mkrescue, xorriso

set -e

ISO_DIR="/home/david/poodillion2/distro/iso"
OUTPUT="/home/david/poodillion2/distro/poodillion.iso"
ROOTFS_DIR="/home/david/poodillion2/distro/rootfs"
KERNEL="${KERNEL:-/boot/vmlinuz-$(uname -r)}"

echo "=== Creating PoodillionOS ISO ==="

# Check for required tools
if ! command -v grub-mkrescue &> /dev/null; then
    echo "Error: grub-mkrescue not found. Install grub-pc-bin or grub2-tools"
    exit 1
fi

# Clean and setup ISO structure
rm -rf "$ISO_DIR"
mkdir -p "$ISO_DIR"/{boot/grub,poodillion}

# Copy kernel
if [ -f "$KERNEL" ]; then
    echo "Copying kernel: $KERNEL"
    cp "$KERNEL" "$ISO_DIR/boot/vmlinuz"
else
    echo "Warning: Kernel not found at $KERNEL"
    echo "You may need to provide a 32-bit kernel"
    # Try to find any kernel
    if [ -f /boot/vmlinuz ]; then
        cp /boot/vmlinuz "$ISO_DIR/boot/vmlinuz"
    fi
fi

# Create initramfs with full system
echo "Creating initramfs..."
INITRD_DIR="$ISO_DIR/initrd_tmp"
mkdir -p "$INITRD_DIR"/{bin,sbin,etc,dev,proc,sys,tmp,root,home,var,mnt}

# Copy all binaries
cp /home/david/poodillion2/bin/* "$INITRD_DIR/bin/"
ln -sf /bin/init "$INITRD_DIR/sbin/init"
ln -sf /bin/psh "$INITRD_DIR/bin/sh"

# Copy etc files
if [ -d "$ROOTFS_DIR/etc" ]; then
    cp -r "$ROOTFS_DIR/etc/"* "$INITRD_DIR/etc/" 2>/dev/null || true
else
    # Create minimal etc
    echo "root:x:0:0:root:/root:/bin/psh" > "$INITRD_DIR/etc/passwd"
    echo "root:x:0:" > "$INITRD_DIR/etc/group"
    echo "poodillion" > "$INITRD_DIR/etc/hostname"
fi

# Create initramfs
cd "$INITRD_DIR"
find . | cpio -o -H newc 2>/dev/null | gzip > "$ISO_DIR/boot/initrd.img"
rm -rf "$INITRD_DIR"

# Create GRUB config
cat > "$ISO_DIR/boot/grub/grub.cfg" << 'EOF'
set timeout=5
set default=0

menuentry "PoodillionOS" {
    linux /boot/vmlinuz init=/bin/init console=tty0
    initrd /boot/initrd.img
}

menuentry "PoodillionOS (Serial Console)" {
    linux /boot/vmlinuz init=/bin/init console=ttyS0,115200
    initrd /boot/initrd.img
}

menuentry "PoodillionOS (Debug)" {
    linux /boot/vmlinuz init=/bin/init console=tty0 debug
    initrd /boot/initrd.img
}
EOF

# Create the ISO
echo "Building ISO..."
grub-mkrescue -o "$OUTPUT" "$ISO_DIR" 2>/dev/null

if [ -f "$OUTPUT" ]; then
    SIZE=$(ls -lh "$OUTPUT" | awk '{print $5}')
    echo ""
    echo "=== ISO Created Successfully ==="
    echo "Output: $OUTPUT"
    echo "Size: $SIZE"
    echo ""
    echo "To test with QEMU:"
    echo "  qemu-system-i386 -cdrom $OUTPUT -m 256M"
    echo ""
    echo "To write to USB (DANGEROUS - double check device!):"
    echo "  sudo dd if=$OUTPUT of=/dev/sdX bs=4M status=progress"
else
    echo "Error: ISO creation failed"
    exit 1
fi
