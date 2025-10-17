/* linker.ld - Linker script for PoodillionOS kernel */

ENTRY(_start)

SECTIONS
{
    /* Kernel starts at 1MB */
    . = 1M;

    /* Multiboot header must be in first 8KB */
    .boot :
    {
        *(.multiboot)
    }

    /* Read-only code */
    .text ALIGN(4K) : AT(ADDR(.text))
    {
        *(.text)
    }

    /* Read-only data */
    .rodata ALIGN(4K) : AT(ADDR(.rodata))
    {
        *(.rodata)
    }

    /* Read-write data (initialized) */
    .data ALIGN(4K) : AT(ADDR(.data))
    {
        *(.data)
    }

    /* Read-write data (uninitialized) and stack */
    .bss ALIGN(4K) : AT(ADDR(.bss))
    {
        *(COMMON)
        *(.bss)
    }

    /* End of kernel */
    _kernel_end = .;
}
