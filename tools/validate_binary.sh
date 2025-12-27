#!/bin/bash
# validate_binary.sh - Post-link validation for BrainhairOS binaries
#
# Validates that compiled binaries don't have sections overlapping
# with reserved x86 memory regions.
#
# Usage: ./validate_binary.sh <elf_file>
#
# Exit codes:
#   0 = Valid
#   1 = Invalid (sections overlap reserved memory)
#   2 = Usage error

set -e

# Reserved memory regions (x86 real mode / PC architecture)
readonly RESERVED_LOW_END=0x500       # Real mode IVT + BDA
readonly VIDEO_START=0xA0000          # VGA memory start
readonly VIDEO_END=0xBFFFF            # VGA memory end
readonly ROM_START=0xC0000            # ROM/BIOS start
readonly ROM_END=0xFFFFF              # ROM/BIOS end
readonly KERNEL_MIN=0x100000          # Minimum kernel address (1MB)
readonly KERNEL_MAX=0xF00000          # Maximum kernel address (15MB)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print error and exit
error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
    exit 1
}

# Print warning
warn() {
    echo -e "${YELLOW}WARNING:${NC} $1" >&2
}

# Print success
success() {
    echo -e "${GREEN}OK:${NC} $1"
}

# Check if a range overlaps with reserved regions
check_range() {
    local name="$1"
    local start="$2"
    local end="$3"
    local size=$((end - start))

    # Skip empty sections
    if [ "$size" -le 0 ]; then
        return 0
    fi

    # Check for overlap with low memory (IVT/BDA)
    if [ "$start" -lt "$RESERVED_LOW_END" ]; then
        error "$name section (0x$(printf '%X' $start)-0x$(printf '%X' $end)) overlaps with reserved low memory (0x0-0x$(printf '%X' $RESERVED_LOW_END))!"
    fi

    # Check for overlap with video memory
    if [ "$start" -lt "$VIDEO_END" ] && [ "$end" -gt "$VIDEO_START" ]; then
        error "$name section (0x$(printf '%X' $start)-0x$(printf '%X' $end)) overlaps with video memory (0x$(printf '%X' $VIDEO_START)-0x$(printf '%X' $VIDEO_END))!"
    fi

    # Check for overlap with ROM/BIOS
    if [ "$start" -lt "$ROM_END" ] && [ "$end" -gt "$ROM_START" ]; then
        error "$name section (0x$(printf '%X' $start)-0x$(printf '%X' $end)) overlaps with ROM/BIOS area (0x$(printf '%X' $ROM_START)-0x$(printf '%X' $ROM_END))!"
    fi

    # Check kernel is above 1MB
    if [ "$start" -lt "$KERNEL_MIN" ] && [ "$start" -gt "$RESERVED_LOW_END" ]; then
        warn "$name section starts in conventional memory (0x$(printf '%X' $start)). Kernel should be at 1MB+."
    fi

    # Check kernel doesn't exceed 15MB
    if [ "$end" -gt "$KERNEL_MAX" ]; then
        error "$name section (0x$(printf '%X' $start)-0x$(printf '%X' $end)) exceeds 15MB limit (0x$(printf '%X' $KERNEL_MAX))!"
    fi

    return 0
}

# Main validation function
validate_elf() {
    local elf_file="$1"

    if [ ! -f "$elf_file" ]; then
        error "File not found: $elf_file"
    fi

    # Check if objdump is available
    if ! command -v objdump &> /dev/null; then
        error "objdump not found. Install binutils."
    fi

    echo "Validating: $elf_file"
    echo "============================================"

    # Get section headers
    local sections
    sections=$(objdump -h "$elf_file" 2>/dev/null)

    if [ -z "$sections" ]; then
        error "Could not read section headers from $elf_file"
    fi

    # Parse and check each section
    local errors=0
    local text_start=0 text_size=0
    local data_start=0 data_size=0
    local bss_start=0 bss_size=0
    local rodata_start=0 rodata_size=0

    while IFS= read -r line; do
        # Parse lines like: "  0 .text         0003e77c  00100000  00100000  00001000  2**4"
        if [[ "$line" =~ ^[[:space:]]*[0-9]+[[:space:]]+\.([a-z]+)[[:space:]]+([0-9a-f]+)[[:space:]]+([0-9a-f]+) ]]; then
            local section_name="${BASH_REMATCH[1]}"
            local section_size="0x${BASH_REMATCH[2]}"
            local section_vma="0x${BASH_REMATCH[3]}"

            local size_dec=$((section_size))
            local start_dec=$((section_vma))
            local end_dec=$((start_dec + size_dec))

            case "$section_name" in
                text)
                    text_start=$start_dec
                    text_size=$size_dec
                    ;;
                data)
                    data_start=$start_dec
                    data_size=$size_dec
                    ;;
                bss)
                    bss_start=$start_dec
                    bss_size=$size_dec
                    ;;
                rodata)
                    rodata_start=$start_dec
                    rodata_size=$size_dec
                    ;;
            esac

            # Only check loadable sections
            if [ "$size_dec" -gt 0 ]; then
                printf "  %-10s: 0x%08X - 0x%08X (%d bytes)\n" \
                    ".$section_name" "$start_dec" "$end_dec" "$size_dec"

                if ! check_range ".$section_name" "$start_dec" "$end_dec"; then
                    ((errors++))
                fi
            fi
        fi
    done <<< "$sections"

    echo "--------------------------------------------"

    # Calculate total kernel size
    local kernel_start=$text_start
    local kernel_end=0

    if [ "$bss_size" -gt 0 ]; then
        kernel_end=$((bss_start + bss_size))
    elif [ "$data_size" -gt 0 ]; then
        kernel_end=$((data_start + data_size))
    elif [ "$rodata_size" -gt 0 ]; then
        kernel_end=$((rodata_start + rodata_size))
    else
        kernel_end=$((text_start + text_size))
    fi

    local kernel_size=$((kernel_end - kernel_start))

    printf "Kernel range: 0x%08X - 0x%08X\n" "$kernel_start" "$kernel_end"
    printf "Kernel size:  %d bytes (%.2f MB)\n" "$kernel_size" "$(echo "scale=2; $kernel_size / 1048576" | bc)"

    echo "--------------------------------------------"

    if [ "$errors" -gt 0 ]; then
        echo -e "${RED}VALIDATION FAILED: $errors error(s) found${NC}"
        exit 1
    fi

    success "All sections are within valid memory regions"
    echo ""
    return 0
}

# Check usage
if [ $# -ne 1 ]; then
    echo "Usage: $0 <elf_file>" >&2
    echo "" >&2
    echo "Validates that an ELF binary doesn't have sections" >&2
    echo "overlapping with reserved x86 memory regions." >&2
    exit 2
fi

validate_elf "$1"
