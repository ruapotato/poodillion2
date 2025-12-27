/* linker_grub.ld - Linker script for GRUB multiboot kernel
 *
 * Memory Map for x86 (GRUB multiboot):
 * ------------------------------------
 * 0x00000000 - 0x000003FF : Real Mode IVT (reserved)
 * 0x00000400 - 0x000004FF : BIOS Data Area (reserved)
 * 0x00000500 - 0x0009FFFF : Conventional memory
 * 0x000A0000 - 0x000BFFFF : Video memory (VGA) - RESERVED
 * 0x000C0000 - 0x000FFFFF : ROM/BIOS area - RESERVED
 * 0x00100000 - 0x00FFFFFF : Extended memory (kernel lives here)
 * 0x01000000 - ...        : High memory (available)
 *
 * GRUB loads multiboot kernels at 1MB by convention.
 */

ENTRY(_start)

/* Define memory regions with explicit bounds */
MEMORY
{
    /* Kernel memory: 1MB to 15MB */
    KERNEL (rwx) : ORIGIN = 0x100000, LENGTH = 14M
}

SECTIONS
{
    /* Kernel starts at 1MB (standard for multiboot) */
    . = 1M;

    _kernel_start = .;

    /* Multiboot header must be early (within first 8KB) */
    .multiboot ALIGN(4K) :
    {
        *(.multiboot)
    } > KERNEL

    /* Code section */
    .text ALIGN(4K) :
    {
        _text_start = .;
        *(.text)
        *(.text.*)
        _text_end = .;
    } > KERNEL

    /* Read-only data */
    .rodata ALIGN(4K) :
    {
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    } > KERNEL

    /* Read-write data (initialized) */
    .data ALIGN(4K) :
    {
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    } > KERNEL

    /* Read-write data (uninitialized) */
    .bss ALIGN(4K) :
    {
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(COMMON)
        _bss_end = .;
    } > KERNEL

    _kernel_end = .;
    _kernel_size = _kernel_end - _kernel_start;

    /* ====================================================================
     * BUILD-TIME ASSERTIONS
     * ==================================================================== */

    ASSERT(_kernel_start >= 0x100000,
           "ERROR: Kernel start address is below 1MB!")

    ASSERT(_bss_end < 0xF00000,
           "ERROR: Kernel exceeds 15MB limit!")

    ASSERT(_text_end > _text_start,
           "ERROR: Text section is empty!")

    /DISCARD/ :
    {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
