/* linker.ld - Linker script for BrainhairOS kernel
 *
 * Memory Map for x86 (custom bootloader):
 * ----------------------------------------
 * 0x00000000 - 0x000003FF : Real Mode IVT (reserved)
 * 0x00000400 - 0x000004FF : BIOS Data Area (reserved)
 * 0x00000500 - 0x00007BFF : Free (used for bootloader stack)
 * 0x00007C00 - 0x00007DFF : Boot sector (MBR)
 * 0x00007E00 - 0x0000FFFF : Stage 2 bootloader / temp buffer
 * 0x00010000 - 0x0009FFFF : Conventional memory (640KB)
 * 0x000A0000 - 0x000BFFFF : Video memory (VGA) - RESERVED
 * 0x000C0000 - 0x000FFFFF : ROM/BIOS area - RESERVED
 * 0x00100000 - 0x00FFFFFF : Extended memory (kernel lives here)
 * 0x01000000 - ...        : High memory (available)
 *
 * Kernel Layout (starting at 1MB):
 * --------------------------------
 * 0x00100000 : _start (entry point)
 * .text      : Code section
 * .rodata    : Read-only data
 * .data      : Initialized data
 * .bss       : Uninitialized data
 * _kernel_end: End of kernel
 *
 * Stack at 2MB (0x200000), growing down
 */

ENTRY(_start)

/* Define memory regions with explicit bounds */
MEMORY
{
    /* Kernel memory: 1MB to 15MB (leaves room before 16MB paging limit) */
    KERNEL (rwx) : ORIGIN = 0x100000, LENGTH = 14M

    /* These are defined for documentation - we don't link into them */
    /* RESERVED_LOW  : ORIGIN = 0x00000, LENGTH = 0x500    */
    /* CONVENTIONAL  : ORIGIN = 0x00500, LENGTH = 0x9FB00  */
    /* VIDEO_MEMORY  : ORIGIN = 0xA0000, LENGTH = 0x20000  */
    /* ROM_BIOS      : ORIGIN = 0xC0000, LENGTH = 0x40000  */
}

SECTIONS
{
    /* Kernel starts at 1MB (above conventional memory to avoid 640KB limit) */
    . = 0x100000;

    _kernel_start = .;

    /* Read-only code - _start must be first! */
    .text : AT(ADDR(.text))
    {
        _text_start = .;
        *(.text)
        _text_end = .;
    } > KERNEL

    /* Read-only data */
    .rodata ALIGN(4K) : AT(ADDR(.rodata))
    {
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    } > KERNEL

    /* Read-write data (initialized) */
    .data ALIGN(4K) : AT(ADDR(.data))
    {
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    } > KERNEL

    /* Read-write data (uninitialized) and stack */
    .bss ALIGN(4K) : AT(ADDR(.bss))
    {
        _bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        _bss_end = .;
    } > KERNEL

    /* End of kernel */
    _kernel_end = .;
    _kernel_size = _kernel_end - _kernel_start;

    /* ====================================================================
     * BUILD-TIME ASSERTIONS
     * These will cause the link to FAIL if any condition is violated
     * ==================================================================== */

    /* Ensure kernel doesn't start in reserved low memory */
    ASSERT(_kernel_start >= 0x100000,
           "ERROR: Kernel start address is below 1MB! Must be >= 0x100000")

    /* Ensure kernel doesn't overlap with video memory (shouldn't happen at 1MB+) */
    ASSERT(_kernel_start >= 0xC0000 || _kernel_end <= 0xA0000,
           "ERROR: Kernel overlaps with video memory region (0xA0000-0xBFFFF)!")

    /* Ensure BSS section doesn't grow into high reserved areas */
    /* With kernel at 1MB, check it stays below 15MB (leaving room for framebuffer mapping) */
    ASSERT(_bss_end < 0xF00000,
           "ERROR: BSS section exceeds 15MB limit! Kernel is too large.")

    /* Ensure kernel stays within the defined KERNEL memory region */
    ASSERT(_kernel_end <= 0xF00000,
           "ERROR: Kernel exceeds memory region bounds (max 15MB)")

    /* Sanity check: BSS must come after data */
    ASSERT(_bss_start >= _data_end,
           "ERROR: BSS section overlaps with data section!")

    /* Sanity check: kernel must have some code */
    ASSERT(_text_end > _text_start,
           "ERROR: Text section is empty!")

    /* Discard unnecessary sections */
    /DISCARD/ :
    {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
