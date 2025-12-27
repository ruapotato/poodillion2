; elf.asm - ELF32 loader for BrainhairOS
; Parses and loads ELF32 executable files

bits 32

; ELF Magic bytes
ELF_MAGIC       equ 0x464C457F  ; "\x7FELF" little-endian

; ELF Header offsets
ELF_MAGIC_OFF   equ 0
ELF_CLASS_OFF   equ 4       ; 1 = 32-bit
ELF_DATA_OFF    equ 5       ; 1 = little-endian
ELF_TYPE_OFF    equ 16      ; 2 = ET_EXEC
ELF_MACHINE_OFF equ 18      ; 3 = EM_386
ELF_ENTRY_OFF   equ 24      ; Entry point
ELF_PHOFF_OFF   equ 28      ; Program header offset
ELF_PHENTSIZE_OFF equ 42    ; Program header entry size
ELF_PHNUM_OFF   equ 44      ; Number of program headers

; Program header offsets
PH_TYPE_OFF     equ 0       ; 1 = PT_LOAD
PH_OFFSET_OFF   equ 4       ; File offset
PH_VADDR_OFF    equ 8       ; Virtual address
PH_FILESZ_OFF   equ 16      ; Size in file
PH_MEMSZ_OFF    equ 20      ; Size in memory
PH_FLAGS_OFF    equ 24      ; Flags (R/W/X)

PT_LOAD         equ 1

section .data

elf_error_magic:    db "ELF: Invalid magic", 0
elf_error_class:    db "ELF: Not 32-bit", 0
elf_error_machine:  db "ELF: Not x86", 0

section .text

; ============================================================================
; elf_validate - Validate ELF header
; Input: ESI = pointer to ELF file in memory
; Returns: EAX = 1 if valid, 0 if invalid
; ============================================================================
global elf_validate
elf_validate:
    push ebx
    push ebp
    mov ebp, esp
    mov esi, [ebp + 12]     ; Get elf_ptr from stack (cdecl)

    ; Check magic
    mov eax, [esi + ELF_MAGIC_OFF]
    cmp eax, ELF_MAGIC
    jne .invalid

    ; Check class (32-bit)
    movzx eax, byte [esi + ELF_CLASS_OFF]
    cmp al, 1
    jne .invalid

    ; Check endianness (little-endian)
    movzx eax, byte [esi + ELF_DATA_OFF]
    cmp al, 1
    jne .invalid

    ; Check machine (x86)
    movzx eax, word [esi + ELF_MACHINE_OFF]
    cmp ax, 3
    jne .invalid

    mov eax, 1
    pop ebp
    pop ebx
    ret

.invalid:
    xor eax, eax
    pop ebp
    pop ebx
    ret

; ============================================================================
; elf_get_entry - Get entry point from ELF
; Input: ESI = pointer to ELF file
; Returns: EAX = entry point address
; ============================================================================
global elf_get_entry
elf_get_entry:
    push ebp
    mov ebp, esp
    mov esi, [ebp + 8]      ; Get elf_ptr from stack (cdecl)
    mov eax, [esi + ELF_ENTRY_OFF]
    pop ebp
    ret

; ============================================================================
; elf_load - Load ELF segments into memory
; Input:
;   ESI = pointer to ELF file in memory
;   EDI = destination base address (or 0 to use virtual addresses)
; Returns: EAX = entry point, or 0 on error
; ============================================================================
global elf_load
elf_load:
    push ebx
    push ecx
    push edx
    push edi
    push ebp
    mov ebp, esp
    mov esi, [ebp + 24]     ; Get elf_ptr from stack (cdecl) - 6 pushes * 4 = 24
    mov edi, [ebp + 28]     ; Get dest_base from stack

    ; Validate ELF - push esi for cdecl call
    push esi
    call elf_validate
    add esp, 4
    test eax, eax
    jz .load_error

    ; Get program header info
    mov eax, [esi + ELF_PHOFF_OFF]      ; Program header offset
    add eax, esi                         ; Absolute address
    mov ebp, eax                         ; EBP = program header pointer

    movzx ecx, word [esi + ELF_PHNUM_OFF]   ; Number of program headers
    movzx edx, word [esi + ELF_PHENTSIZE_OFF]  ; Entry size

.load_segment:
    test ecx, ecx
    jz .load_done

    ; Check if PT_LOAD
    mov eax, [ebp + PH_TYPE_OFF]
    cmp eax, PT_LOAD
    jne .next_segment

    ; Get segment info
    mov eax, [ebp + PH_VADDR_OFF]       ; Virtual address
    mov ebx, [ebp + PH_OFFSET_OFF]      ; File offset
    add ebx, esi                         ; Absolute source address

    push ecx
    push edx

    ; Copy segment to memory
    mov edi, eax                         ; Destination = virtual address
    mov ecx, [ebp + PH_FILESZ_OFF]       ; Bytes to copy

    ; Copy file data
    push esi
    mov esi, ebx                         ; Source
    rep movsb
    pop esi

    ; Zero remaining bytes (BSS)
    mov ecx, [ebp + PH_MEMSZ_OFF]
    sub ecx, [ebp + PH_FILESZ_OFF]
    jle .no_bss

    xor al, al
    rep stosb

.no_bss:
    pop edx
    pop ecx

.next_segment:
    add ebp, edx                         ; Next program header
    dec ecx
    jmp .load_segment

.load_done:
    ; Return entry point
    mov eax, [esi + ELF_ENTRY_OFF]

    pop ebp
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

.load_error:
    xor eax, eax
    pop ebp
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; elf_info - Print ELF info (for debugging)
; Input: ESI = pointer to ELF file
; ============================================================================
global elf_info
elf_info:
    push eax
    push ebx

    ; Get entry point
    mov eax, [esi + ELF_ENTRY_OFF]
    ; Would print here, but we don't have printing in this file

    ; Get number of program headers
    movzx eax, word [esi + ELF_PHNUM_OFF]

    pop ebx
    pop eax
    ret

; ============================================================================
; Stub implementations removed - use userland_bins.asm for these functions:
;   - get_webapp_bin
;   - get_webapp_bin_size
;   - call_entry
;   - call_entry_with_stack
; ============================================================================
