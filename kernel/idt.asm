; idt.asm - Interrupt Descriptor Table for BrainhairOS
; Sets up IDT for exceptions, hardware interrupts, and syscalls

bits 32

section .data

; IDT descriptor (loaded with lidt)
idt_descriptor:
    dw idt_end - idt_start - 1  ; Size of IDT - 1
    dd idt_start                 ; Address of IDT

section .bss

; IDT table (256 entries x 8 bytes = 2048 bytes)
idt_start:
    resb 256 * 8
idt_end:

section .text

; ============================================================================
; IDT Entry Structure (8 bytes per entry):
;   Offset 0-1:  Low 16 bits of handler address
;   Offset 2-3:  Code segment selector (0x08)
;   Offset 4:    Always 0
;   Offset 5:    Type and attributes
;                - Bit 7: Present (1 = valid)
;                - Bits 5-6: DPL (ring level that can trigger)
;                - Bit 4: Storage segment (0 for interrupts)
;                - Bits 0-3: Gate type (0xE = 32-bit interrupt gate)
;   Offset 6-7:  High 16 bits of handler address
; ============================================================================

; Attribute bytes
%define IDT_PRESENT    0x80
%define IDT_DPL0       0x00    ; Ring 0 only
%define IDT_DPL3       0x60    ; Ring 3 can trigger (for syscalls)
%define IDT_INTERRUPT  0x0E    ; 32-bit interrupt gate

; ============================================================================
; External ISR handlers (defined in isr.asm)
; ============================================================================

; CPU Exceptions (0-31)
extern isr_0   ; Divide by zero
extern isr_1   ; Debug
extern isr_2   ; NMI
extern isr_3   ; Breakpoint
extern isr_4   ; Overflow
extern isr_5   ; Bound range exceeded
extern isr_6   ; Invalid opcode
extern isr_7   ; Device not available
extern isr_8   ; Double fault
extern isr_9   ; Coprocessor segment overrun
extern isr_10  ; Invalid TSS
extern isr_11  ; Segment not present
extern isr_12  ; Stack segment fault
extern isr_13  ; General protection fault
extern isr_14  ; Page fault
extern isr_15  ; Reserved
extern isr_16  ; x87 FPU error
extern isr_17  ; Alignment check
extern isr_18  ; Machine check
extern isr_19  ; SIMD FP exception
extern isr_20  ; Virtualization exception
extern isr_21  ; Control protection exception
; 22-31 reserved

; Hardware IRQs (32-47)
extern irq_0   ; PIT timer
extern irq_1   ; Keyboard
extern irq_2   ; Cascade
extern irq_3   ; COM2
extern irq_4   ; COM1
extern irq_5   ; LPT2
extern irq_6   ; Floppy
extern irq_7   ; LPT1/spurious
extern irq_8   ; RTC
extern irq_9   ; Free
extern irq_10  ; Free
extern irq_11  ; Free
extern irq_12  ; PS/2 mouse
extern irq_13  ; FPU
extern irq_14  ; Primary ATA
extern irq_15  ; Secondary ATA

; Syscall (0x42 = 66)
extern isr_syscall
extern isr_linux_syscall

; ============================================================================
; set_idt_entry - Set an IDT entry
; Input:
;   eax = interrupt number
;   ebx = handler address
;   cl  = type/attributes
; ============================================================================
global set_idt_entry
set_idt_entry:
    push edx
    push edi

    ; Calculate IDT entry address: idt_start + (int_num * 8)
    mov edi, idt_start
    shl eax, 3              ; eax = int_num * 8
    add edi, eax

    ; Set low 16 bits of handler
    mov [edi], bx

    ; Set code segment selector (0x08)
    mov word [edi + 2], 0x08

    ; Set reserved byte to 0
    mov byte [edi + 4], 0

    ; Set type/attributes
    mov [edi + 5], cl

    ; Set high 16 bits of handler
    mov edx, ebx
    shr edx, 16
    mov [edi + 6], dx

    pop edi
    pop edx
    ret

; ============================================================================
; init_idt - Initialize the IDT with all handlers
; ============================================================================
global init_idt
init_idt:
    push eax
    push ebx
    push ecx

    ; First, clear the entire IDT
    mov edi, idt_start
    mov ecx, 256 * 8 / 4
    xor eax, eax
    rep stosd

    ; Set up CPU exception handlers (0-21)
    mov cl, IDT_PRESENT | IDT_DPL0 | IDT_INTERRUPT

    mov eax, 0
    mov ebx, isr_0
    call set_idt_entry

    mov eax, 1
    mov ebx, isr_1
    call set_idt_entry

    mov eax, 2
    mov ebx, isr_2
    call set_idt_entry

    mov eax, 3
    mov ebx, isr_3
    call set_idt_entry

    mov eax, 4
    mov ebx, isr_4
    call set_idt_entry

    mov eax, 5
    mov ebx, isr_5
    call set_idt_entry

    mov eax, 6
    mov ebx, isr_6
    call set_idt_entry

    mov eax, 7
    mov ebx, isr_7
    call set_idt_entry

    mov eax, 8
    mov ebx, isr_8
    call set_idt_entry

    mov eax, 9
    mov ebx, isr_9
    call set_idt_entry

    mov eax, 10
    mov ebx, isr_10
    call set_idt_entry

    mov eax, 11
    mov ebx, isr_11
    call set_idt_entry

    mov eax, 12
    mov ebx, isr_12
    call set_idt_entry

    mov eax, 13
    mov ebx, isr_13
    call set_idt_entry

    mov eax, 14
    mov ebx, isr_14
    call set_idt_entry

    mov eax, 15
    mov ebx, isr_15
    call set_idt_entry

    mov eax, 16
    mov ebx, isr_16
    call set_idt_entry

    mov eax, 17
    mov ebx, isr_17
    call set_idt_entry

    mov eax, 18
    mov ebx, isr_18
    call set_idt_entry

    mov eax, 19
    mov ebx, isr_19
    call set_idt_entry

    mov eax, 20
    mov ebx, isr_20
    call set_idt_entry

    mov eax, 21
    mov ebx, isr_21
    call set_idt_entry

    ; Set up hardware IRQ handlers (32-47)
    ; (after PIC remapping, IRQs 0-15 map to interrupts 32-47)

    mov eax, 32
    mov ebx, irq_0
    call set_idt_entry

    mov eax, 33
    mov ebx, irq_1
    call set_idt_entry

    mov eax, 34
    mov ebx, irq_2
    call set_idt_entry

    mov eax, 35
    mov ebx, irq_3
    call set_idt_entry

    mov eax, 36
    mov ebx, irq_4
    call set_idt_entry

    mov eax, 37
    mov ebx, irq_5
    call set_idt_entry

    mov eax, 38
    mov ebx, irq_6
    call set_idt_entry

    mov eax, 39
    mov ebx, irq_7
    call set_idt_entry

    mov eax, 40
    mov ebx, irq_8
    call set_idt_entry

    mov eax, 41
    mov ebx, irq_9
    call set_idt_entry

    mov eax, 42
    mov ebx, irq_10
    call set_idt_entry

    mov eax, 43
    mov ebx, irq_11
    call set_idt_entry

    mov eax, 44
    mov ebx, irq_12
    call set_idt_entry

    mov eax, 45
    mov ebx, irq_13
    call set_idt_entry

    mov eax, 46
    mov ebx, irq_14
    call set_idt_entry

    mov eax, 47
    mov ebx, irq_15
    call set_idt_entry

    ; Set up syscall handler (int 0x42)
    ; DPL3 so user-mode processes can trigger it
    mov cl, IDT_PRESENT | IDT_DPL3 | IDT_INTERRUPT
    mov eax, 0x42
    mov ebx, isr_syscall
    call set_idt_entry

    ; Set up Linux syscall handler (int 0x80)
    ; DPL3 so user-mode processes can trigger it
    mov cl, IDT_PRESENT | IDT_DPL3 | IDT_INTERRUPT
    mov eax, 0x80
    mov ebx, isr_linux_syscall
    call set_idt_entry

    ; Load the IDT
    lidt [idt_descriptor]

    pop ecx
    pop ebx
    pop eax
    ret

; ============================================================================
; remap_pic - Remap the PIC to use interrupts 32-47
; The default PIC mappings conflict with CPU exceptions
; ============================================================================
global remap_pic
remap_pic:
    push eax

    ; Start initialization sequence (ICW1)
    mov al, 0x11        ; Init + ICW4 needed
    out 0x20, al        ; Master PIC command
    out 0xA0, al        ; Slave PIC command

    ; ICW2: Vector offsets
    mov al, 32          ; Master: IRQs 0-7 -> interrupts 32-39
    out 0x21, al
    mov al, 40          ; Slave: IRQs 8-15 -> interrupts 40-47
    out 0xA1, al

    ; ICW3: Tell PICs about each other
    mov al, 4           ; Master: slave on IRQ2 (bit 2)
    out 0x21, al
    mov al, 2           ; Slave: cascade identity (IRQ2)
    out 0xA1, al

    ; ICW4: 8086 mode
    mov al, 0x01
    out 0x21, al
    out 0xA1, al

    ; Set interrupt masks:
    ; Master PIC (0x21): 0xFC = 11111100 = unmask IRQ0 (timer) and IRQ1 (keyboard)
    ; Slave PIC (0xA1): 0xFF = 11111111 = mask all slave IRQs
    mov al, 0xFC
    out 0x21, al
    mov al, 0xFF
    out 0xA1, al

    pop eax
    ret

; ============================================================================
; enable_interrupts - Enable hardware interrupts (sti)
; ============================================================================
global enable_interrupts
enable_interrupts:
    sti
    ret

; ============================================================================
; disable_interrupts - Disable hardware interrupts (cli)
; ============================================================================
global disable_interrupts
disable_interrupts:
    cli
    ret
