; poly1305_64.asm - Poly1305 Message Authentication Code for BrainhairOS (64-bit)
; Implements Poly1305 as per RFC 8439
; Uses System V AMD64 ABI calling convention
;
; Poly1305 is a fast, secure MAC designed by Daniel J. Bernstein
; Uses 256-bit key (r||s) and produces 128-bit tag
; Computation: tag = ((sum of message blocks * r^i) mod (2^130 - 5) + s) mod 2^128

[BITS 64]

section .data

; Poly1305 state structure
align 16
poly1305_r:
    dq 0, 0, 0, 0, 0        ; r[0..4] - 5 x 26-bit limbs (stored in 64-bit)

poly1305_s:
    dq 0, 0                 ; s[0..1] - 128-bit nonce as 2 x 64-bit

poly1305_acc:
    dq 0, 0, 0, 0, 0        ; accumulator[0..4] - 5 x 26-bit limbs (stored in 64-bit)

poly1305_buffer:
    times 16 db 0           ; Input buffer for partial blocks

poly1305_buflen:
    dq 0                    ; Current buffer length

section .text

; Limb masks
LIMB_MASK equ 0x3FFFFFFFFFF  ; 44 bits = 0xFFFFFFFFFFF actually... let me recalculate
; Actually for efficiency, let's use 5 x 26-bit limbs like the 32-bit version
; This is simpler and proven to work

; Using 5 x 26-bit limbs stored in 64-bit words
LIMB26_MASK equ 0x03FFFFFF   ; 26 bits

; ============================================================================
; poly1305_init - Initialize Poly1305 state with key
; RDI = pointer to 32-byte key (r||s)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global poly1305_init
poly1305_init:
    test rdi, rdi
    jz .error

    push rbx
    push r12
    push r13
    push r14

    mov r12, rdi            ; Save key pointer

    ; Load r (first 16 bytes) as 4 little-endian 32-bit words
    mov eax, [r12 + 0]      ; r[0-3]
    mov ebx, [r12 + 4]      ; r[4-7]
    mov ecx, [r12 + 8]      ; r[8-11]
    mov edx, [r12 + 12]     ; r[12-15]

    ; Clamp r according to RFC 8439:
    ; Clear top 4 bits of bytes 3,7,11,15
    ; Clear bottom 2 bits of bytes 4,8,12
    and eax, 0x0FFFFFFF     ; Clear top 4 bits of byte 3
    and ebx, 0x0FFFFFFC     ; Clear bottom 2 bits of byte 4
    and ebx, 0x0FFFFFFF     ; Clear top 4 bits of byte 7
    and ecx, 0x0FFFFFFC     ; Clear bottom 2 bits of byte 8
    and ecx, 0x0FFFFFFF     ; Clear top 4 bits of byte 11
    and edx, 0x0FFFFFFC     ; Clear bottom 2 bits of byte 12
    and edx, 0x0FFFFFFF     ; Clear top 4 bits of byte 15

    ; Convert to 5 x 26-bit limbs
    ; r0 = r[0:26]
    mov r8d, eax
    and r8d, LIMB26_MASK
    mov [rel poly1305_r + 0], r8

    ; r1 = r[26:52]
    mov r8d, eax
    shr r8d, 26
    mov r9d, ebx
    shl r9d, 6
    or r8d, r9d
    and r8d, LIMB26_MASK
    mov [rel poly1305_r + 8], r8

    ; r2 = r[52:78]
    mov r8d, ebx
    shr r8d, 20
    mov r9d, ecx
    shl r9d, 12
    or r8d, r9d
    and r8d, LIMB26_MASK
    mov [rel poly1305_r + 16], r8

    ; r3 = r[78:104]
    mov r8d, ecx
    shr r8d, 14
    mov r9d, edx
    shl r9d, 18
    or r8d, r9d
    and r8d, LIMB26_MASK
    mov [rel poly1305_r + 24], r8

    ; r4 = r[104:130]
    mov r8d, edx
    shr r8d, 8
    and r8d, LIMB26_MASK
    mov [rel poly1305_r + 32], r8

    ; Load s (last 16 bytes) as 2 x 64-bit little-endian
    mov rax, [r12 + 16]
    mov [rel poly1305_s + 0], rax
    mov rax, [r12 + 24]
    mov [rel poly1305_s + 8], rax

    ; Initialize accumulator to 0
    xor eax, eax
    mov [rel poly1305_acc + 0], rax
    mov [rel poly1305_acc + 8], rax
    mov [rel poly1305_acc + 16], rax
    mov [rel poly1305_acc + 24], rax
    mov [rel poly1305_acc + 32], rax

    ; Initialize buffer state
    mov [rel poly1305_buflen], rax

    xor eax, eax            ; Success
    jmp .done

.error:
    mov eax, -1

.done:
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

; ============================================================================
; poly1305_block - Process one 16-byte block
; RDI = pointer to 16-byte block
; ESI = final flag (1 if final block, 0 otherwise)
; Internal use only
; ============================================================================
poly1305_block:
    push rbp
    mov rbp, rsp
    sub rsp, 128            ; Local space
    push rbx
    push r12
    push r13
    push r14
    push r15

    mov r12, rdi            ; Block pointer
    mov r13d, esi           ; Final flag

    ; Load block as 4 x 32-bit
    mov eax, [r12 + 0]
    mov ebx, [r12 + 4]
    mov ecx, [r12 + 8]
    mov edx, [r12 + 12]

    ; Convert to 5 x 26-bit limbs and add to accumulator
    ; h0
    mov r8d, eax
    and r8d, LIMB26_MASK
    add r8, [rel poly1305_acc + 0]
    mov [rbp - 8], r8       ; h0

    ; h1
    mov r8d, eax
    shr r8d, 26
    mov r9d, ebx
    shl r9d, 6
    or r8d, r9d
    and r8d, LIMB26_MASK
    add r8, [rel poly1305_acc + 8]
    mov [rbp - 16], r8      ; h1

    ; h2
    mov r8d, ebx
    shr r8d, 20
    mov r9d, ecx
    shl r9d, 12
    or r8d, r9d
    and r8d, LIMB26_MASK
    add r8, [rel poly1305_acc + 16]
    mov [rbp - 24], r8      ; h2

    ; h3
    mov r8d, ecx
    shr r8d, 14
    mov r9d, edx
    shl r9d, 18
    or r8d, r9d
    and r8d, LIMB26_MASK
    add r8, [rel poly1305_acc + 24]
    mov [rbp - 32], r8      ; h3

    ; h4 with high bit (if not final)
    mov r8d, edx
    shr r8d, 8
    and r8d, 0x00FFFFFF     ; 24 bits from block
    test r13d, r13d
    jnz .skip_high_bit
    or r8d, 0x01000000      ; Set bit 128
.skip_high_bit:
    add r8, [rel poly1305_acc + 32]
    mov [rbp - 40], r8      ; h4

    ; Precompute r*5 for modular reduction
    mov rax, [rel poly1305_r + 8]
    lea r9, [rax + rax*4]   ; r1 * 5
    mov [rbp - 48], r9

    mov rax, [rel poly1305_r + 16]
    lea r9, [rax + rax*4]   ; r2 * 5
    mov [rbp - 56], r9

    mov rax, [rel poly1305_r + 24]
    lea r9, [rax + rax*4]   ; r3 * 5
    mov [rbp - 64], r9

    mov rax, [rel poly1305_r + 32]
    lea r9, [rax + rax*4]   ; r4 * 5
    mov [rbp - 72], r9

    ; Multiply: d = h * r mod (2^130 - 5)
    ; Using 64-bit multiplications for efficiency

    ; d0 = h0*r0 + h1*r4*5 + h2*r3*5 + h3*r2*5 + h4*r1*5
    mov rax, [rbp - 8]      ; h0
    imul rax, [rel poly1305_r + 0]  ; h0 * r0
    mov r8, rax             ; d0

    mov rax, [rbp - 16]     ; h1
    imul rax, [rbp - 72]    ; h1 * r4*5
    add r8, rax

    mov rax, [rbp - 24]     ; h2
    imul rax, [rbp - 64]    ; h2 * r3*5
    add r8, rax

    mov rax, [rbp - 32]     ; h3
    imul rax, [rbp - 56]    ; h3 * r2*5
    add r8, rax

    mov rax, [rbp - 40]     ; h4
    imul rax, [rbp - 48]    ; h4 * r1*5
    add r8, rax
    mov [rbp - 80], r8      ; d0

    ; d1 = h0*r1 + h1*r0 + h2*r4*5 + h3*r3*5 + h4*r2*5
    mov rax, [rbp - 8]
    imul rax, [rel poly1305_r + 8]
    mov r9, rax

    mov rax, [rbp - 16]
    imul rax, [rel poly1305_r + 0]
    add r9, rax

    mov rax, [rbp - 24]
    imul rax, [rbp - 72]
    add r9, rax

    mov rax, [rbp - 32]
    imul rax, [rbp - 64]
    add r9, rax

    mov rax, [rbp - 40]
    imul rax, [rbp - 56]
    add r9, rax
    mov [rbp - 88], r9      ; d1

    ; d2 = h0*r2 + h1*r1 + h2*r0 + h3*r4*5 + h4*r3*5
    mov rax, [rbp - 8]
    imul rax, [rel poly1305_r + 16]
    mov r10, rax

    mov rax, [rbp - 16]
    imul rax, [rel poly1305_r + 8]
    add r10, rax

    mov rax, [rbp - 24]
    imul rax, [rel poly1305_r + 0]
    add r10, rax

    mov rax, [rbp - 32]
    imul rax, [rbp - 72]
    add r10, rax

    mov rax, [rbp - 40]
    imul rax, [rbp - 64]
    add r10, rax
    mov [rbp - 96], r10     ; d2

    ; d3 = h0*r3 + h1*r2 + h2*r1 + h3*r0 + h4*r4*5
    mov rax, [rbp - 8]
    imul rax, [rel poly1305_r + 24]
    mov r11, rax

    mov rax, [rbp - 16]
    imul rax, [rel poly1305_r + 16]
    add r11, rax

    mov rax, [rbp - 24]
    imul rax, [rel poly1305_r + 8]
    add r11, rax

    mov rax, [rbp - 32]
    imul rax, [rel poly1305_r + 0]
    add r11, rax

    mov rax, [rbp - 40]
    imul rax, [rbp - 72]
    add r11, rax
    mov [rbp - 104], r11    ; d3

    ; d4 = h0*r4 + h1*r3 + h2*r2 + h3*r1 + h4*r0
    mov rax, [rbp - 8]
    imul rax, [rel poly1305_r + 32]
    mov r14, rax

    mov rax, [rbp - 16]
    imul rax, [rel poly1305_r + 24]
    add r14, rax

    mov rax, [rbp - 24]
    imul rax, [rel poly1305_r + 16]
    add r14, rax

    mov rax, [rbp - 32]
    imul rax, [rel poly1305_r + 8]
    add r14, rax

    mov rax, [rbp - 40]
    imul rax, [rel poly1305_r + 0]
    add r14, rax
    ; d4 in r14

    ; Reduce: propagate carries through 26-bit limbs
    mov r8, [rbp - 80]      ; d0
    mov rax, r8
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 0], rax

    shr r8, 26              ; carry
    add r8, [rbp - 88]      ; d1 + carry
    mov rax, r8
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 8], rax

    shr r8, 26
    add r8, [rbp - 96]      ; d2 + carry
    mov rax, r8
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 16], rax

    shr r8, 26
    add r8, [rbp - 104]     ; d3 + carry
    mov rax, r8
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 24], rax

    shr r8, 26
    add r8, r14             ; d4 + carry
    mov rax, r8
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 32], rax

    ; Final carry and modular reduction (multiply by 5)
    shr r8, 26
    lea rax, [r8 + r8*4]    ; carry * 5
    add [rel poly1305_acc + 0], rax

    ; Propagate final carry
    mov rax, [rel poly1305_acc + 0]
    mov r8, rax
    and eax, LIMB26_MASK
    mov [rel poly1305_acc + 0], rax
    shr r8, 26
    add [rel poly1305_acc + 8], r8

    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

; ============================================================================
; poly1305_update - Process message data
; RDI = pointer to message data
; RSI = length of data
; ============================================================================
global poly1305_update
poly1305_update:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14

    mov r12, rdi            ; Data pointer
    mov r13, rsi            ; Length

    test r12, r12
    jz .done
    test r13, r13
    jz .done

    ; Check if we have buffered data
    mov rbx, [rel poly1305_buflen]
    test rbx, rbx
    jz .process_blocks

    ; Fill buffer first
.fill_buffer:
    cmp rbx, 16
    jae .buffer_full
    test r13, r13
    jz .done

    mov al, [r12]
    lea r14, [rel poly1305_buffer]
    mov [r14 + rbx], al
    inc r12
    inc rbx
    dec r13
    jmp .fill_buffer

.buffer_full:
    ; Process buffered block
    lea rdi, [rel poly1305_buffer]
    xor esi, esi            ; Not final
    call poly1305_block
    xor rbx, rbx            ; Clear buffer

.process_blocks:
    ; Process complete 16-byte blocks
    cmp r13, 16
    jb .buffer_remainder

    mov rdi, r12
    xor esi, esi            ; Not final
    call poly1305_block

    add r12, 16
    sub r13, 16
    jmp .process_blocks

.buffer_remainder:
    ; Buffer remaining bytes
    test r13, r13
    jz .save_buflen

    mov al, [r12]
    lea r14, [rel poly1305_buffer]
    mov [r14 + rbx], al
    inc r12
    inc rbx
    dec r13
    jmp .buffer_remainder

.save_buflen:
    mov [rel poly1305_buflen], rbx

.done:
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ============================================================================
; poly1305_final - Finalize and output 16-byte tag
; RDI = pointer to 16-byte output tag buffer
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global poly1305_final
poly1305_final:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13

    mov r12, rdi            ; Output pointer
    test r12, r12
    jz .error

    ; Process any remaining buffered data
    mov rbx, [rel poly1305_buflen]
    test rbx, rbx
    jz .finalize

    ; Per RFC 8439: Append 0x01 byte at position buflen, then pad with zeros
    lea r13, [rel poly1305_buffer]
    mov byte [r13 + rbx], 1     ; Add 0x01 marker at end of data
    inc rbx                      ; Now buflen+1 bytes are valid

    ; Pad rest with zeros
.pad_buffer:
    cmp rbx, 16
    jae .process_final_block
    mov byte [r13 + rbx], 0
    inc rbx
    jmp .pad_buffer

.process_final_block:
    lea rdi, [rel poly1305_buffer]
    mov esi, 1              ; Final block flag (skip automatic bit-128)
    call poly1305_block

.finalize:
    ; Convert accumulator to bytes and add s
    ; Convert 5 x 26-bit limbs to 4 x 32-bit words (128 bits)
    mov rax, [rel poly1305_acc + 0]     ; h0
    mov rbx, [rel poly1305_acc + 8]     ; h1
    mov rcx, [rel poly1305_acc + 16]    ; h2
    mov rdx, [rel poly1305_acc + 24]    ; h3
    mov r8, [rel poly1305_acc + 32]     ; h4

    ; word0 = h0 + (h1 << 26)
    mov r9, rbx
    shl r9, 26
    or rax, r9
    mov r9d, eax            ; word0

    ; word1 = (h1 >> 6) + (h2 << 20)
    shr rbx, 6
    mov r10, rcx
    shl r10, 20
    or rbx, r10
    mov r10d, ebx           ; word1

    ; word2 = (h2 >> 12) + (h3 << 14)
    shr rcx, 12
    mov r11, rdx
    shl r11, 14
    or rcx, r11
    mov r11d, ecx           ; word2

    ; word3 = (h3 >> 18) + (h4 << 8)
    shr rdx, 18
    shl r8, 8
    or rdx, r8
    ; rdx has word3

    ; Add s to the result (mod 2^128)
    ; Load s as two 64-bit values
    mov rax, [rel poly1305_s + 0]   ; s_lo
    mov rbx, [rel poly1305_s + 8]   ; s_hi

    ; Combine words into 64-bit values
    mov rcx, r10
    shl rcx, 32
    or rcx, r9              ; h_lo = word0 | (word1 << 32)

    mov r8, rdx
    shl r8, 32
    or r8, r11              ; h_hi = word2 | (word3 << 32)

    ; Add s
    add rcx, rax
    adc r8, rbx

    ; Write tag as little-endian
    mov [r12 + 0], rcx
    mov [r12 + 8], r8

    xor eax, eax            ; Success
    jmp .done

.error:
    mov eax, -1

.done:
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; ============================================================================
; poly1305_auth - One-shot MAC computation
; RDI = pointer to output tag (16 bytes)
; RSI = pointer to message
; RDX = message length
; RCX = pointer to key (32 bytes)
; Returns: EAX = 0 on success, -1 on error
; ============================================================================
global poly1305_auth
poly1305_auth:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14

    mov r12, rdi            ; tag output
    mov r13, rsi            ; message
    mov r14, rdx            ; length
    mov rbx, rcx            ; key

    ; Initialize with key
    mov rdi, rbx
    call poly1305_init
    test eax, eax
    jnz .error

    ; Update with message
    mov rdi, r13
    mov rsi, r14
    call poly1305_update

    ; Finalize and output tag
    mov rdi, r12
    call poly1305_final
    test eax, eax
    jnz .error

    xor eax, eax
    jmp .done

.error:
    mov eax, -1

.done:
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
