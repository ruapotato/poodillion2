; net.asm - Networking support for BrainhairOS
; Includes PCI access and E1000 driver support

[BITS 32]

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
port_outb:
    push ebp
    mov ebp, esp
    mov dx, [ebp+8]     ; port
    mov al, [ebp+12]    ; value
    out dx, al
    pop ebp
    ret

; void port_outw(uint16 port, uint16 value)
port_outw:
    push ebp
    mov ebp, esp
    mov dx, [ebp+8]     ; port
    mov ax, [ebp+12]    ; value
    out dx, ax
    pop ebp
    ret

; void port_outl(uint16 port, uint32 value)
port_outl:
    push ebp
    mov ebp, esp
    mov dx, [ebp+8]     ; port
    mov eax, [ebp+12]   ; value
    out dx, eax
    pop ebp
    ret

; uint8 port_inb(uint16 port)
port_inb:
    push ebp
    mov ebp, esp
    xor eax, eax
    mov dx, [ebp+8]     ; port
    in al, dx
    pop ebp
    ret

; uint16 port_inw(uint16 port)
port_inw:
    push ebp
    mov ebp, esp
    xor eax, eax
    mov dx, [ebp+8]     ; port
    in ax, dx
    pop ebp
    ret

; uint32 port_inl(uint16 port)
port_inl:
    push ebp
    mov ebp, esp
    mov dx, [ebp+8]     ; port
    in eax, dx
    pop ebp
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
; Address format: 0x80000000 | (bus << 16) | (slot << 11) | (func << 8) | (offset & 0xFC)
pci_config_read32:
    push ebp
    mov ebp, esp
    push ebx

    ; Build config address
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, byte [ebp+8] ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, byte [ebp+12] ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, byte [ebp+16] ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, byte [ebp+20] ; offset (aligned to 4 bytes)
    and ebx, 0xFC
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data
    mov dx, 0xCFC
    in eax, dx

    pop ebx
    pop ebp
    ret

; void pci_config_write32(uint8 bus, uint8 slot, uint8 func, uint8 offset, uint32 value)
pci_config_write32:
    push ebp
    mov ebp, esp
    push ebx

    ; Build config address
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, byte [ebp+8] ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, byte [ebp+12] ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, byte [ebp+16] ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, byte [ebp+20] ; offset (aligned to 4 bytes)
    and ebx, 0xFC
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Write config data
    mov dx, 0xCFC
    mov eax, [ebp+24]       ; value
    out dx, eax

    pop ebx
    pop ebp
    ret

; uint16 pci_config_read16(uint8 bus, uint8 slot, uint8 func, uint8 offset)
pci_config_read16:
    push ebp
    mov ebp, esp
    push ebx

    ; Build config address
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, byte [ebp+8] ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, byte [ebp+12] ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, byte [ebp+16] ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, byte [ebp+20] ; offset (aligned to 2 bytes)
    and ebx, 0xFE
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data (16-bit from appropriate offset)
    mov dx, 0xCFC
    movzx ebx, byte [ebp+20]
    and ebx, 2
    add dx, bx
    in ax, dx
    movzx eax, ax

    pop ebx
    pop ebp
    ret

; uint8 pci_config_read8(uint8 bus, uint8 slot, uint8 func, uint8 offset)
pci_config_read8:
    push ebp
    mov ebp, esp
    push ebx

    ; Build config address
    mov eax, 0x80000000     ; Enable bit

    movzx ebx, byte [ebp+8] ; bus
    shl ebx, 16
    or eax, ebx

    movzx ebx, byte [ebp+12] ; slot
    shl ebx, 11
    or eax, ebx

    movzx ebx, byte [ebp+16] ; func
    shl ebx, 8
    or eax, ebx

    movzx ebx, byte [ebp+20] ; offset
    and ebx, 0xFC
    or eax, ebx

    ; Write config address
    mov dx, 0xCF8
    out dx, eax

    ; Read config data (8-bit from appropriate offset)
    mov dx, 0xCFC
    movzx ebx, byte [ebp+20]
    and ebx, 3
    add dx, bx
    in al, dx
    movzx eax, al

    pop ebx
    pop ebp
    ret

; ============================================================================
; Memory-Mapped I/O
; ============================================================================

global mmio_read32
global mmio_write32

; uint32 mmio_read32(uint32 addr)
mmio_read32:
    push ebp
    mov ebp, esp
    mov eax, [ebp+8]        ; addr
    mov eax, [eax]          ; read from address
    pop ebp
    ret

; void mmio_write32(uint32 addr, uint32 value)
mmio_write32:
    push ebp
    mov ebp, esp
    mov eax, [ebp+8]        ; addr
    mov edx, [ebp+12]       ; value
    mov [eax], edx          ; write to address
    pop ebp
    ret

; ============================================================================
; Memory copy/set for network buffers
; ============================================================================

global net_memcpy
global net_memset

; void net_memcpy(void* dest, void* src, uint32 len)
net_memcpy:
    push ebp
    mov ebp, esp
    push edi
    push esi
    push ecx

    mov edi, [ebp+8]        ; dest
    mov esi, [ebp+12]       ; src
    mov ecx, [ebp+16]       ; len

    rep movsb

    pop ecx
    pop esi
    pop edi
    pop ebp
    ret

; void net_memset(void* dest, uint8 value, uint32 len)
net_memset:
    push ebp
    mov ebp, esp
    push edi
    push ecx

    mov edi, [ebp+8]        ; dest
    movzx eax, byte [ebp+12] ; value
    mov ecx, [ebp+16]       ; len

    rep stosb

    pop ecx
    pop edi
    pop ebp
    ret
