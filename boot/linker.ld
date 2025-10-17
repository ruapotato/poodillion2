/* linker.ld - Linker script for PoodillionOS kernel */

ENTRY(_start)

SECTIONS
{
    /* Kernel starts at 64KB (where stage2 loads it) */
    . = 0x10000;

    /* Read-only code - _start must be first! */
    .text :
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
