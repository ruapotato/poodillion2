; sha256_64.asm - SHA-256 Hash Algorithm for BrainhairOS (64-bit)
; Implements FIPS 180-4 specification
; Uses System V AMD64 ABI calling convention

[BITS 64]

section .data

; SHA-256 Constants (first 32 bits of fractional parts of cube roots of first 64 primes)
align 16
sha256_k:
    dd 0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5
    dd 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5
    dd 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3
    dd 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174
    dd 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc
    dd 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da
    dd 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7
    dd 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967
    dd 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13
    dd 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85
    dd 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3
    dd 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070
    dd 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5
    dd 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3
    dd 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208
    dd 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2

; Initial hash values (first 32 bits of fractional parts of square roots of first 8 primes)
sha256_initial_h:
    dd 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a
    dd 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19

section .text

; Context offsets
SHA256_H_OFFSET        equ 0
SHA256_DATA_OFFSET     equ 32
SHA256_DATALEN_OFFSET  equ 96
SHA256_BITLEN_LO_OFFSET equ 100
SHA256_BITLEN_HI_OFFSET equ 104

; ============================================================================
; sha256_init - Initialize SHA-256 context
; RDI = pointer to SHA-256 context (108 bytes)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global sha256_init
sha256_init:
    test rdi, rdi
    jz .error

    push rbx
    push r12
    mov r12, rdi            ; Save context pointer

    ; Copy initial hash values
    lea rsi, [rel sha256_initial_h]
    mov ecx, 8
.copy_h:
    mov eax, [rsi]
    mov [rdi], eax
    add rsi, 4
    add rdi, 4
    dec ecx
    jnz .copy_h

    ; Clear datalen and bitlen
    xor eax, eax
    mov [r12 + SHA256_DATALEN_OFFSET], eax
    mov [r12 + SHA256_BITLEN_LO_OFFSET], eax
    mov [r12 + SHA256_BITLEN_HI_OFFSET], eax

    xor eax, eax            ; Return 0 (success)
    pop r12
    pop rbx
    ret

.error:
    mov eax, -1
    ret

; ============================================================================
; sha256_transform - Process one 512-bit block (internal)
; RDI = pointer to SHA-256 context
; RSI = pointer to 64-byte data block
; ============================================================================
sha256_transform:
    push rbp
    mov rbp, rsp
    sub rsp, 320            ; w[64]=256 + working_vars[8]=32 + padding
    push rbx
    push r12
    push r13
    push r14
    push r15

    mov r12, rdi            ; Save context pointer

    ; Working variables on stack at [rbp-288] to [rbp-257]
    ; w array at [rbp-256] to [rbp-1]
    %define W_BASE rbp-256
    %define VAR_A dword [rbp-288]
    %define VAR_B dword [rbp-284]
    %define VAR_C dword [rbp-280]
    %define VAR_D dword [rbp-276]
    %define VAR_E dword [rbp-272]
    %define VAR_F dword [rbp-268]
    %define VAR_G dword [rbp-264]
    %define VAR_H dword [rbp-260]

    ; Prepare message schedule (w[0..15] from input, big-endian)
    lea rdi, [W_BASE]
    mov ecx, 16
.prepare_w:
    mov eax, [rsi]
    bswap eax
    mov [rdi], eax
    add rsi, 4
    add rdi, 4
    dec ecx
    jnz .prepare_w

    ; Extend w[16..63]
    lea rdi, [W_BASE]
    mov ecx, 16
.extend_w:
    ; s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3)
    mov eax, [rdi + rcx*4 - 60]     ; w[i-15]
    mov edx, eax
    ror edx, 7
    mov r8d, eax
    ror r8d, 18
    xor edx, r8d
    shr eax, 3
    xor edx, eax
    mov r9d, edx                    ; r9d = s0

    ; s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10)
    mov eax, [rdi + rcx*4 - 8]      ; w[i-2]
    mov edx, eax
    ror edx, 17
    mov r8d, eax
    ror r8d, 19
    xor edx, r8d
    shr eax, 10
    xor edx, eax                    ; edx = s1

    ; w[i] = w[i-16] + s0 + w[i-7] + s1
    mov eax, [rdi + rcx*4 - 64]     ; w[i-16]
    add eax, r9d                    ; + s0
    add eax, [rdi + rcx*4 - 28]     ; + w[i-7]
    add eax, edx                    ; + s1
    mov [rdi + rcx*4], eax

    inc ecx
    cmp ecx, 64
    jl .extend_w

    ; Initialize working variables from hash state
    mov eax, [r12 + 0]
    mov VAR_A, eax
    mov eax, [r12 + 4]
    mov VAR_B, eax
    mov eax, [r12 + 8]
    mov VAR_C, eax
    mov eax, [r12 + 12]
    mov VAR_D, eax
    mov eax, [r12 + 16]
    mov VAR_E, eax
    mov eax, [r12 + 20]
    mov VAR_F, eax
    mov eax, [r12 + 24]
    mov VAR_G, eax
    mov eax, [r12 + 28]
    mov VAR_H, eax

    ; Main compression loop
    lea r13, [rel sha256_k]
    lea r14, [W_BASE]
    xor ecx, ecx
.compress_loop:
    ; S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
    mov eax, VAR_E
    mov edx, eax
    ror edx, 6
    mov r8d, eax
    ror r8d, 11
    xor edx, r8d
    mov r8d, eax
    ror r8d, 25
    xor edx, r8d
    mov r9d, edx              ; r9d = S1

    ; ch = (e & f) ^ (~e & g)
    mov eax, VAR_E
    mov ebx, VAR_F
    and ebx, eax              ; e & f
    not eax
    and eax, VAR_G            ; ~e & g
    xor eax, ebx              ; ch
    mov r10d, eax             ; r10d = ch

    ; temp1 = h + S1 + ch + k[i] + w[i]
    mov eax, VAR_H
    add eax, r9d              ; + S1
    add eax, r10d             ; + ch
    add eax, [r13 + rcx*4]    ; + k[i]
    add eax, [r14 + rcx*4]    ; + w[i]
    mov r15d, eax             ; r15d = temp1

    ; S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
    mov eax, VAR_A
    mov edx, eax
    ror edx, 2
    mov r8d, eax
    ror r8d, 13
    xor edx, r8d
    mov r8d, eax
    ror r8d, 22
    xor edx, r8d
    mov r9d, edx              ; r9d = S0

    ; maj = (a & b) ^ (a & c) ^ (b & c)
    mov eax, VAR_A
    mov ebx, VAR_B
    mov edx, eax
    and edx, ebx              ; a & b
    mov r8d, eax
    and r8d, VAR_C            ; a & c
    xor edx, r8d
    mov r8d, ebx
    and r8d, VAR_C            ; b & c
    xor edx, r8d              ; maj
    mov r10d, edx             ; r10d = maj

    ; temp2 = S0 + maj
    mov eax, r9d
    add eax, r10d
    mov r11d, eax             ; r11d = temp2

    ; Update working variables
    ; h = g
    mov eax, VAR_G
    mov VAR_H, eax
    ; g = f
    mov eax, VAR_F
    mov VAR_G, eax
    ; f = e
    mov eax, VAR_E
    mov VAR_F, eax
    ; e = d + temp1
    mov eax, VAR_D
    add eax, r15d
    mov VAR_E, eax
    ; d = c
    mov eax, VAR_C
    mov VAR_D, eax
    ; c = b
    mov eax, VAR_B
    mov VAR_C, eax
    ; b = a
    mov eax, VAR_A
    mov VAR_B, eax
    ; a = temp1 + temp2
    mov eax, r15d
    add eax, r11d
    mov VAR_A, eax

    inc ecx
    cmp ecx, 64
    jl .compress_loop

    ; Add compressed chunk to current hash
    mov eax, VAR_A
    add [r12 + 0], eax
    mov eax, VAR_B
    add [r12 + 4], eax
    mov eax, VAR_C
    add [r12 + 8], eax
    mov eax, VAR_D
    add [r12 + 12], eax
    mov eax, VAR_E
    add [r12 + 16], eax
    mov eax, VAR_F
    add [r12 + 20], eax
    mov eax, VAR_G
    add [r12 + 24], eax
    mov eax, VAR_H
    add [r12 + 28], eax

    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

; ============================================================================
; sha256_update - Add data to hash computation
; RDI = pointer to SHA-256 context
; RSI = pointer to data
; RDX = length of data
; Returns: EAX = 0 on success
; ============================================================================
global sha256_update
sha256_update:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    push r15

    mov r12, rdi            ; context
    mov r13, rsi            ; data
    mov r14, rdx            ; length

    test r14, r14
    jz .update_done

.update_loop:
    ; Get current datalen
    mov eax, [r12 + SHA256_DATALEN_OFFSET]

    ; Copy byte to buffer
    mov cl, [r13]
    lea rbx, [r12 + SHA256_DATA_OFFSET]
    mov [rbx + rax], cl

    inc eax
    mov [r12 + SHA256_DATALEN_OFFSET], eax

    ; If buffer is full (64 bytes), transform
    cmp eax, 64
    jne .next_byte

    ; Transform
    mov rdi, r12
    lea rsi, [r12 + SHA256_DATA_OFFSET]
    call sha256_transform

    ; Update bit length
    mov eax, [r12 + SHA256_BITLEN_LO_OFFSET]
    add eax, 512            ; 64 bytes * 8 bits
    mov [r12 + SHA256_BITLEN_LO_OFFSET], eax
    jnc .no_carry
    inc dword [r12 + SHA256_BITLEN_HI_OFFSET]
.no_carry:

    ; Reset datalen
    mov dword [r12 + SHA256_DATALEN_OFFSET], 0

.next_byte:
    inc r13
    dec r14
    jnz .update_loop

.update_done:
    xor eax, eax

    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ============================================================================
; sha256_final - Finalize and output hash
; RDI = pointer to SHA-256 context
; RSI = pointer to 32-byte output buffer
; Returns: EAX = 0 on success
; ============================================================================
global sha256_final
sha256_final:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13

    mov r12, rdi            ; context
    mov r13, rsi            ; output

    ; Pad message
    mov eax, [r12 + SHA256_DATALEN_OFFSET]
    mov ebx, eax            ; Save datalen

    ; Add 0x80 byte
    lea rdi, [r12 + SHA256_DATA_OFFSET]
    mov byte [rdi + rax], 0x80
    inc eax

    ; If datalen > 55, need two blocks
    cmp eax, 56
    jbe .pad_to_56

    ; Pad rest with zeros and transform
    lea rdi, [r12 + SHA256_DATA_OFFSET + rax]
    mov ecx, 64
    sub ecx, eax
.zero_pad1:
    test ecx, ecx
    jz .transform1
    mov byte [rdi], 0
    inc rdi
    dec ecx
    jmp .zero_pad1

.transform1:
    mov rdi, r12
    lea rsi, [r12 + SHA256_DATA_OFFSET]
    call sha256_transform

    ; Zero the buffer for next block
    lea rdi, [r12 + SHA256_DATA_OFFSET]
    mov ecx, 56
.zero_buf:
    mov byte [rdi], 0
    inc rdi
    dec ecx
    jnz .zero_buf
    jmp .add_length

.pad_to_56:
    ; Pad with zeros until 56 bytes
    lea rdi, [r12 + SHA256_DATA_OFFSET + rax]
    mov ecx, 56
    sub ecx, eax
.zero_pad2:
    test ecx, ecx
    jz .add_length
    mov byte [rdi], 0
    inc rdi
    dec ecx
    jmp .zero_pad2

.add_length:
    ; Calculate total bit length
    ; bitlen += datalen * 8
    mov eax, [r12 + SHA256_BITLEN_LO_OFFSET]
    mov edx, ebx            ; original datalen
    shl edx, 3              ; * 8
    add eax, edx

    ; Store length in big-endian at bytes 56-63
    lea rdi, [r12 + SHA256_DATA_OFFSET + 56]
    mov dword [rdi], 0      ; High 32 bits (simplified - assume < 2^32 bits)
    mov dword [rdi + 4], 0
    bswap eax
    mov [rdi + 4], eax      ; Low 32 bits in big-endian

    ; Final transform
    mov rdi, r12
    lea rsi, [r12 + SHA256_DATA_OFFSET]
    call sha256_transform

    ; Copy hash to output in big-endian
    mov rdi, r13
    mov rsi, r12
    mov ecx, 8
.copy_hash:
    mov eax, [rsi]
    bswap eax
    mov [rdi], eax
    add rsi, 4
    add rdi, 4
    dec ecx
    jnz .copy_hash

    xor eax, eax

    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ============================================================================
; sha256_hash - One-shot hash function
; RDI = pointer to data
; ESI = length of data
; RDX = pointer to 32-byte output buffer
; Returns: EAX = 0 on success
; ============================================================================
global sha256_hash
sha256_hash:
    push rbp
    mov rbp, rsp
    sub rsp, 128            ; Context on stack (108 bytes + padding)
    push rbx
    push r12
    push r13

    mov r12, rdi            ; data
    mov r13d, esi           ; length
    mov rbx, rdx            ; output

    ; Initialize context
    lea rdi, [rbp - 128]
    call sha256_init

    ; Update with data
    lea rdi, [rbp - 128]
    mov rsi, r12
    mov edx, r13d            ; Zero-extends to RDX
    call sha256_update

    ; Finalize
    lea rdi, [rbp - 128]
    mov rsi, rbx
    call sha256_final

    pop r13
    pop r12
    pop rbx
    mov rsp, rbp
    pop rbp
    ret
