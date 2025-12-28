; chacha20_64.asm - ChaCha20 stream cipher implementation for BrainhairOS (64-bit)
; Implements ChaCha20 as per RFC 8439
; Uses System V AMD64 ABI calling convention

bits 64

section .data

; ChaCha20 constant: "expand 32-byte k" in little-endian
chacha_constants:
    dd 0x61707865  ; "expa"
    dd 0x3320646e  ; "nd 3"
    dd 0x79622d32  ; "2-by"
    dd 0x6b206574  ; "te k"

section .bss

; ChaCha20 state (16 x 32-bit words = 64 bytes)
chacha_state:
    resd 16

; Working copy for block generation
chacha_working:
    resd 16

; Output block (64 bytes)
chacha_block_data:
    resb 64

section .text

; ============================================================================
; chacha20_init - Initialize ChaCha20 state
; Input (System V AMD64 ABI):
;   RDI = key pointer (32 bytes)
;   RSI = nonce pointer (12 bytes)
;   EDX = counter (32-bit)
; ============================================================================
global chacha20_init
chacha20_init:
    push rbx

    ; Set constants (words 0-3)
    lea rax, [chacha_constants]
    lea rbx, [chacha_state]
    mov ecx, [rax]
    mov [rbx], ecx
    mov ecx, [rax + 4]
    mov [rbx + 4], ecx
    mov ecx, [rax + 8]
    mov [rbx + 8], ecx
    mov ecx, [rax + 12]
    mov [rbx + 12], ecx

    ; Copy key (words 4-11, 32 bytes)
    mov ecx, [rdi]
    mov [rbx + 16], ecx
    mov ecx, [rdi + 4]
    mov [rbx + 20], ecx
    mov ecx, [rdi + 8]
    mov [rbx + 24], ecx
    mov ecx, [rdi + 12]
    mov [rbx + 28], ecx
    mov ecx, [rdi + 16]
    mov [rbx + 32], ecx
    mov ecx, [rdi + 20]
    mov [rbx + 36], ecx
    mov ecx, [rdi + 24]
    mov [rbx + 40], ecx
    mov ecx, [rdi + 28]
    mov [rbx + 44], ecx

    ; Set counter (word 12)
    mov [rbx + 48], edx

    ; Copy nonce (words 13-15, 12 bytes)
    mov ecx, [rsi]
    mov [rbx + 52], ecx
    mov ecx, [rsi + 4]
    mov [rbx + 56], ecx
    mov ecx, [rsi + 8]
    mov [rbx + 60], ecx

    pop rbx
    ret

; ============================================================================
; chacha20_block - Generate 64-byte keystream block
; Modifies chacha_block_data with keystream data
; ============================================================================
global chacha20_block
chacha20_block:
    push rbx
    push r12
    push r13
    push r14
    push r15
    push rbp

    ; Copy state to working copy
    lea rsi, [chacha_state]
    lea rdi, [chacha_working]
    mov ecx, 16
.copy_state:
    mov eax, [rsi]
    mov [rdi], eax
    add rsi, 4
    add rdi, 4
    dec ecx
    jnz .copy_state

    ; Perform 20 rounds (10 double rounds)
    mov r15d, 10

.double_round:
    lea rbx, [chacha_working]

    ; QR(0,4,8,12) - Column round
    mov eax, [rbx + 0]
    mov r8d, [rbx + 16]
    mov ecx, [rbx + 32]
    mov edx, [rbx + 48]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 0], eax
    mov [rbx + 16], r8d
    mov [rbx + 32], ecx
    mov [rbx + 48], edx

    ; QR(1,5,9,13)
    mov eax, [rbx + 4]
    mov r8d, [rbx + 20]
    mov ecx, [rbx + 36]
    mov edx, [rbx + 52]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 4], eax
    mov [rbx + 20], r8d
    mov [rbx + 36], ecx
    mov [rbx + 52], edx

    ; QR(2,6,10,14)
    mov eax, [rbx + 8]
    mov r8d, [rbx + 24]
    mov ecx, [rbx + 40]
    mov edx, [rbx + 56]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 8], eax
    mov [rbx + 24], r8d
    mov [rbx + 40], ecx
    mov [rbx + 56], edx

    ; QR(3,7,11,15)
    mov eax, [rbx + 12]
    mov r8d, [rbx + 28]
    mov ecx, [rbx + 44]
    mov edx, [rbx + 60]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 12], eax
    mov [rbx + 28], r8d
    mov [rbx + 44], ecx
    mov [rbx + 60], edx

    ; Diagonal rounds: QR(0,5,10,15)
    mov eax, [rbx + 0]
    mov r8d, [rbx + 20]
    mov ecx, [rbx + 40]
    mov edx, [rbx + 60]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 0], eax
    mov [rbx + 20], r8d
    mov [rbx + 40], ecx
    mov [rbx + 60], edx

    ; QR(1,6,11,12)
    mov eax, [rbx + 4]
    mov r8d, [rbx + 24]
    mov ecx, [rbx + 44]
    mov edx, [rbx + 48]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 4], eax
    mov [rbx + 24], r8d
    mov [rbx + 44], ecx
    mov [rbx + 48], edx

    ; QR(2,7,8,13)
    mov eax, [rbx + 8]
    mov r8d, [rbx + 28]
    mov ecx, [rbx + 32]
    mov edx, [rbx + 52]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 8], eax
    mov [rbx + 28], r8d
    mov [rbx + 32], ecx
    mov [rbx + 52], edx

    ; QR(3,4,9,14)
    mov eax, [rbx + 12]
    mov r8d, [rbx + 16]
    mov ecx, [rbx + 36]
    mov edx, [rbx + 56]

    add eax, r8d
    xor edx, eax
    rol edx, 16
    add ecx, edx
    xor r8d, ecx
    rol r8d, 12
    add eax, r8d
    xor edx, eax
    rol edx, 8
    add ecx, edx
    xor r8d, ecx
    rol r8d, 7

    mov [rbx + 12], eax
    mov [rbx + 16], r8d
    mov [rbx + 36], ecx
    mov [rbx + 56], edx

    dec r15d
    jnz .double_round

    ; Add original state to working state and store as output block
    lea rsi, [chacha_state]
    lea rdi, [chacha_working]
    lea rbx, [chacha_block_data]
    mov ecx, 16
.add_state:
    mov eax, [rsi]
    add eax, [rdi]
    mov [rbx], eax
    add rsi, 4
    add rdi, 4
    add rbx, 4
    dec ecx
    jnz .add_state

    ; Increment counter in state for next block
    lea rax, [chacha_state]
    inc dword [rax + 48]

    pop rbp
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

; ============================================================================
; chacha20_encrypt - Encrypt/decrypt data using ChaCha20
; Input (System V AMD64 ABI):
;   RDI = input pointer
;   RSI = output pointer
;   EDX = length
;   RCX = key pointer (32 bytes)
;   R8  = nonce pointer (12 bytes)
;   R9D = counter
; ============================================================================
global chacha20_encrypt
chacha20_encrypt:
    push rbx
    push r12
    push r13
    push r14
    push r15
    push rbp

    ; Save parameters
    mov r12, rdi        ; input
    mov r13, rsi        ; output
    mov r14d, edx       ; length
    mov r15, rcx        ; key
    mov rbp, r8         ; nonce

    ; Initialize state: chacha20_init(key, nonce, counter)
    mov rdi, r15        ; key
    mov rsi, rbp        ; nonce
    mov edx, r9d        ; counter
    call chacha20_init

    ; Restore input/output pointers
    mov rsi, r12        ; input
    mov rdi, r13        ; output

.block_loop:
    test r14d, r14d
    jz .done

    ; Generate keystream block
    push rsi
    push rdi
    call chacha20_block
    pop rdi
    pop rsi

    ; XOR up to 64 bytes
    mov ecx, 64
    cmp r14d, ecx
    jae .xor_full
    mov ecx, r14d       ; Remaining bytes

.xor_full:
    push rcx            ; Save bytes to process
    lea rbx, [chacha_block_data]

.xor_loop:
    test ecx, ecx
    jz .xor_done
    mov al, [rsi]
    xor al, [rbx]
    mov [rdi], al
    inc rsi
    inc rdi
    inc rbx
    dec ecx
    jmp .xor_loop

.xor_done:
    pop rcx             ; Restore bytes processed
    sub r14d, ecx
    jmp .block_loop

.done:
    pop rbp
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

; ============================================================================
; chacha20_get_block - Get pointer to current keystream block
; Returns: RAX = pointer to 64-byte block
; ============================================================================
global chacha20_get_block
chacha20_get_block:
    lea rax, [chacha_block_data]
    ret
