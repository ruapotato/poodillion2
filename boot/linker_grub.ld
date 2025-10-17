/* Linker script for GRUB multiboot kernel */

ENTRY(_start)

SECTIONS
{
    /* Kernel starts at 1MB (standard for multiboot) */
    . = 1M;

    /* Multiboot header must be early */
    .multiboot ALIGN(4K) : {
        *(.multiboot)
    }

    /* Code section */
    .text ALIGN(4K) : {
        *(.text)
    }

    /* Read-only data */
    .rodata ALIGN(4K) : {
        *(.rodata)
    }

    /* Read-write data (initialized) */
    .data ALIGN(4K) : {
        *(.data)
    }

    /* Read-write data (uninitialized) */
    .bss ALIGN(4K) : {
        *(.bss)
        *(COMMON)
    }
}
