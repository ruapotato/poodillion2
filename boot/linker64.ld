/* linker64.ld - Linker script for BrainhairOS 64-bit kernel
 *
 * Memory Map for x86_64:
 * ----------------------
 * 0x00000000_00000000 - 0x00000000_000FFFFF : Low memory (identity mapped)
 * 0x00000000_00100000 - 0x00000000_00FFFFFF : Extended memory (kernel)
 * 0x00000000_01000000 - ...                 : High memory
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

OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

/* Define memory regions */
MEMORY
{
    /* Kernel memory: 1MB to 15MB */
    KERNEL (rwx) : ORIGIN = 0x100000, LENGTH = 14M
}

SECTIONS
{
    /* Kernel starts at 1MB */
    . = 0x100000;

    _kernel_start = .;

    /* Read-only code - _start must be first! */
    .text : AT(ADDR(.text))
    {
        _text_start = .;
        *(.text)
        *(.text.*)
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

    /* Read-write data (uninitialized) */
    .bss ALIGN(4K) : AT(ADDR(.bss))
    {
        __bss_start = .;
        _bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        __bss_end = .;
        _bss_end = .;
    } > KERNEL

    /* End of kernel */
    _kernel_end = .;
    _kernel_size = _kernel_end - _kernel_start;

    /* Build-time assertions */
    ASSERT(_kernel_start >= 0x100000,
           "ERROR: Kernel start address is below 1MB!")

    ASSERT(_bss_end < 0xF00000,
           "ERROR: BSS section exceeds 15MB limit!")

    ASSERT(_kernel_end <= 0xF00000,
           "ERROR: Kernel exceeds memory region bounds (max 15MB)")

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
