; net_64.asm - Networking support for BrainhairOS (64-bit)
; Includes PCI access, MMIO, and E1000 driver support
; Uses System V AMD64 ABI calling convention

[BITS 64]

section .text

; ============================================================================
; Port I/O Functions
; ============================================================================

global port_outb
global port_outw
global port_outl
global port_inb
global port_inw
global port_inl

; void port_outb(uint16 port, uint8 value)
; RDI = port, RSI = value
port_outb:
    mov dx, di          ; port (lower 16 bits of RDI)
    mov al, sil         ; value (lower 8 bits of RSI)
    out dx, al
    ret

; void port_outw(uint16 port, uint16 value)
; RDI = port, RSI = value
port_outw:
    mov dx, di          ; port
    mov ax, si          ; value
    out dx, ax
    ret

; void port_outl(uint16 port, uint32 value)
; RDI = port, RSI = value
port_outl:
    mov dx, di          ; port
    mov eax, esi        ; value
    out dx, eax
    ret

; uint8 port_inb(uint16 port)
; RDI = port, returns in EAX
port_inb:
    xor eax, eax
    mov dx, di          ; port
    in al, dx
    ret

; uint16 port_inw(uint16 port)
; RDI = port, returns in EAX
port_inw:
    xor eax, eax
    mov dx, di          ; port
    in ax, dx
    ret

; uint32 port_inl(uint16 port)
; RDI = port, returns in EAX
port_inl:
    mov dx, di          ; port
    in eax, dx
    ret

; ============================================================================
; PCI Configuration Space Access
; ============================================================================

; PCI config address port: 0xCF8
; PCI config data port: 0xCFC

global pci_config_read32
global pci_config_write32
global pci_config_read16
global pci_config_read8

; uint32 pci_config_read32(uint8 bus, uint8 slot, uint8 func, uint8 offset)
; RDI = bus, RSI = slot, RDX = func, RCX = offset
; Address format: 0x80000000 | (bus << 16) | (slot << 11) | (func << 8) | (offset & 0xFC)
pci_config_read32:
    push rbx

    ; Build config address in EAX
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, dil          ; bus (lower 8 bits of RDI)
    shl ebx, 16
    or eax, ebx

    movzx ebx, sil          ; slot (lower 8 bits of RSI)
    shl ebx, 11
    or eax, ebx

    movzx ebx, dl           ; func (lower 8 bits of RDX)
    shl ebx, 8
    or eax, ebx

    movzx ebx, cl           ; offset (lower 8 bits of RCX)
    and ebx, 0xFC           ; align to 4 bytes
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data
    mov dx, 0xCFC
    in eax, dx

    pop rbx
    ret

; void pci_config_write32(uint8 bus, uint8 slot, uint8 func, uint8 offset, uint32 value)
; RDI = bus, RSI = slot, RDX = func, RCX = offset, R8D = value
pci_config_write32:
    push rbx
    push r8

    ; Build config address in EAX
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, dil          ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, sil          ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, dl           ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, cl           ; offset
    and ebx, 0xFC
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Write config data
    mov dx, 0xCFC
    pop r8
    mov eax, r8d            ; value
    out dx, eax

    pop rbx
    ret

; uint16 pci_config_read16(uint8 bus, uint8 slot, uint8 func, uint8 offset)
; RDI = bus, RSI = slot, RDX = func, RCX = offset
pci_config_read16:
    push rbx
    push rcx                ; save offset for later

    ; Build config address in EAX
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, dil          ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, sil          ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, dl           ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, cl           ; offset
    and ebx, 0xFE           ; align to 2 bytes
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data (16-bit from appropriate offset)
    mov dx, 0xCFC
    pop rcx                 ; restore offset
    movzx ebx, cl
    and ebx, 2
    add dx, bx
    in ax, dx
    movzx eax, ax

    pop rbx
    ret

; uint8 pci_config_read8(uint8 bus, uint8 slot, uint8 func, uint8 offset)
; RDI = bus, RSI = slot, RDX = func, RCX = offset
pci_config_read8:
    push rbx
    push rcx                ; save offset for later

    ; Build config address in EAX
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, dil          ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, sil          ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, dl           ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, cl           ; offset
    and ebx, 0xFC
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data (8-bit from appropriate offset)
    mov dx, 0xCFC
    pop rcx                 ; restore offset
    movzx ebx, cl
    and ebx, 3
    add dx, bx
    in al, dx
    movzx eax, al

    pop rbx
    ret

; ============================================================================
; Memory-Mapped I/O
; ============================================================================

global mmio_read32
global mmio_write32

; uint32 mmio_read32(uint64 addr)
; RDI = addr, returns in EAX
mmio_read32:
    mov eax, [rdi]          ; read 32-bit value from address
    ret

; void mmio_write32(uint64 addr, uint32 value)
; RDI = addr, ESI = value
mmio_write32:
    mov [rdi], esi          ; write 32-bit value to address
    ret

; ============================================================================
; Wait for next interrupt (allows timer to fire)
; ============================================================================
global wait_tick
wait_tick:
    sti             ; Enable interrupts
    hlt             ; Wait for interrupt
    ret

; ============================================================================
; Memory copy/set for network buffers
; ============================================================================

global net_memcpy

; void net_memcpy(void* dest, void* src, uint64 len)
; RDI = dest, RSI = src, RDX = len
net_memcpy:
    push rcx
    mov rcx, rdx            ; len
    rep movsb
    pop rcx
    ret
