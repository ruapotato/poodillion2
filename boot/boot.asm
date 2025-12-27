; boot.asm - BrainhairOS Kernel Entry Point
; For custom bootloader (no multiboot needed)

[BITS 32]

section .text
global _start
extern brainhair_kernel_main
extern _bss_start
extern _bss_end

_start:
    ; Explicitly set up segment registers (don't rely on bootloader)
    mov ax, 0x10            ; Data segment selector
    mov ds, ax
    mov es, ax              ; ES is used by rep stosd
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Set up stack AFTER BSS section (kernel at 1MB, BSS ends around 0x1A5000)
    ; Stack at 2MB should be safe
    mov esp, 0x200000

    ; Zero the BSS section
    cld                     ; Clear direction flag (forward)
    mov edi, _bss_start
    mov ecx, _bss_end
    sub ecx, edi            ; ECX = BSS size in bytes
    shr ecx, 2              ; ECX = number of dwords
    xor eax, eax            ; Zero value
    rep stosd               ; Zero BSS

    ; Call kernel main
    call brainhair_kernel_main

    ; Hang if kernel returns
.hang:
    cli         ; Disable interrupts
    hlt         ; Halt CPU
    jmp .hang   ; Loop forever

; ============================================================================
; Stub framebuffer info functions for non-multiboot boot
; These return 0 to indicate no framebuffer is available from bootloader
; ============================================================================
global multiboot_fb_addr
multiboot_fb_addr:
    xor eax, eax    ; Return 0
    ret

global multiboot_fb_width
multiboot_fb_width:
    xor eax, eax
    ret

global multiboot_fb_height
multiboot_fb_height:
    xor eax, eax
    ret

global multiboot_fb_bpp
multiboot_fb_bpp:
    xor eax, eax
    ret
