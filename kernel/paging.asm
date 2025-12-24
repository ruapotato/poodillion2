; paging.asm - x86 Paging Setup for BrainhairOS
; Sets up identity mapping for kernel space

bits 32

; Page table entry flags
PTE_PRESENT    equ 0x001   ; Page is present
PTE_WRITABLE   equ 0x002   ; Page is writable
PTE_USER       equ 0x004   ; Page is accessible from user mode
PTE_ACCESSED   equ 0x020   ; Page has been accessed
PTE_DIRTY      equ 0x040   ; Page has been written to

; Combined flags
PTE_KERNEL     equ PTE_PRESENT | PTE_WRITABLE           ; Kernel page
PTE_USER_RW    equ PTE_PRESENT | PTE_WRITABLE | PTE_USER ; User page

section .bss
align 4096

; Page Directory (4KB, 1024 entries)
global page_directory
page_directory:
    resb 4096

; Page Tables for identity mapping first 16MB (4 tables)
; Each table maps 4MB (1024 * 4KB pages)
global page_tables
page_tables:
    resb 4096 * 4   ; 4 page tables = 16MB identity mapped

; Kernel heap page tables (for dynamic allocation)
; Maps 0x00400000 - 0x00800000 (4MB kernel heap)
kernel_heap_pt:
    resb 4096

section .data

; Track next free page frame (physical address)
global next_free_frame
next_free_frame:
    dd 0x00100000   ; Start allocating at 1MB (after kernel)

; End of usable memory (detected at boot or hardcoded)
global memory_end
memory_end:
    dd 0x01000000   ; Assume 16MB for now (conservative)

; Number of free frames
global free_frame_count
free_frame_count:
    dd 0

section .text

; ============================================================================
; init_paging - Initialize paging with identity mapping
; Identity maps first 16MB of physical memory
; ============================================================================
global init_paging
init_paging:
    push eax
    push ebx
    push ecx
    push edx
    push edi

    ; Clear page directory
    mov edi, page_directory
    mov ecx, 1024
    xor eax, eax
    rep stosd

    ; Clear page tables
    mov edi, page_tables
    mov ecx, 1024 * 4       ; 4 tables
    rep stosd

    ; Set up identity mapping for first 16MB
    ; This maps physical 0x00000000-0x00FFFFFF to virtual 0x00000000-0x00FFFFFF

    ; Fill page tables with identity mapping
    mov edi, page_tables    ; Start of page tables
    mov eax, PTE_KERNEL     ; First page at 0x00000000 with kernel flags
    mov ecx, 1024 * 4       ; 4096 pages (16MB)

.fill_tables:
    mov [edi], eax          ; Store page table entry
    add eax, 0x1000         ; Next physical page (4KB)
    add edi, 4              ; Next entry
    loop .fill_tables

    ; Set up page directory entries pointing to page tables
    mov edi, page_directory
    mov eax, page_tables
    or eax, PTE_KERNEL      ; Page table at page_tables, kernel flags

    ; Entry 0: maps 0x00000000 - 0x003FFFFF (first 4MB)
    mov [edi], eax
    add eax, 0x1000         ; Next page table

    ; Entry 1: maps 0x00400000 - 0x007FFFFF (4-8MB)
    mov [edi + 4], eax
    add eax, 0x1000

    ; Entry 2: maps 0x00800000 - 0x00BFFFFF (8-12MB)
    mov [edi + 8], eax
    add eax, 0x1000

    ; Entry 3: maps 0x00C00000 - 0x00FFFFFF (12-16MB)
    mov [edi + 12], eax

    ; Calculate free frame count
    ; Usable memory starts at 1MB, assume 16MB total
    ; Free frames = (16MB - 1MB) / 4KB = 3840 frames
    mov eax, [memory_end]
    sub eax, 0x00100000     ; Subtract 1MB (kernel space)
    shr eax, 12             ; Divide by 4096
    mov [free_frame_count], eax

    ; Load page directory address into CR3
    mov eax, page_directory
    mov cr3, eax

    ; Enable paging by setting bit 31 of CR0
    mov eax, cr0
    or eax, 0x80000000      ; Set PG bit
    mov cr0, eax

    pop edi
    pop edx
    pop ecx
    pop ebx
    pop eax
    ret

; ============================================================================
; disable_paging - Disable paging (for debugging)
; ============================================================================
global disable_paging
disable_paging:
    mov eax, cr0
    and eax, 0x7FFFFFFF     ; Clear PG bit
    mov cr0, eax
    ret

; ============================================================================
; get_cr3 - Get current page directory address
; Returns: EAX = CR3 value
; ============================================================================
global get_cr3
get_cr3:
    mov eax, cr3
    ret

; ============================================================================
; set_cr3 - Set page directory address (switch address space)
; Input: [esp+4] = new page directory physical address
; ============================================================================
global set_cr3
set_cr3:
    mov eax, [esp + 4]
    mov cr3, eax
    ret

; ============================================================================
; flush_tlb - Flush the TLB (Translation Lookaside Buffer)
; Call after modifying page tables
; ============================================================================
global flush_tlb
flush_tlb:
    mov eax, cr3
    mov cr3, eax            ; Reloading CR3 flushes TLB
    ret

; ============================================================================
; flush_tlb_page - Flush a single page from TLB
; Input: [esp+4] = virtual address of page to flush
; ============================================================================
global flush_tlb_page
flush_tlb_page:
    mov eax, [esp + 4]
    invlpg [eax]
    ret

; ============================================================================
; alloc_frame - Allocate a physical page frame
; Returns: EAX = physical address of frame, or 0 if out of memory
; ============================================================================
global alloc_frame
alloc_frame:
    push ebx

    ; Check if we have free frames
    mov eax, [free_frame_count]
    test eax, eax
    jz .out_of_memory

    ; Get next free frame
    mov eax, [next_free_frame]
    mov ebx, eax

    ; Update next free frame pointer
    add ebx, 0x1000         ; Next 4KB frame
    mov [next_free_frame], ebx

    ; Decrement free frame count
    dec dword [free_frame_count]

    pop ebx
    ret

.out_of_memory:
    xor eax, eax            ; Return 0
    pop ebx
    ret

; ============================================================================
; free_frame - Free a physical page frame
; Input: [esp+4] = physical address of frame to free
; Note: Simple implementation - doesn't actually reuse frames yet
; ============================================================================
global free_frame
free_frame:
    ; For now, just increment the free count
    ; A real implementation would maintain a free list
    inc dword [free_frame_count]
    ret

; ============================================================================
; map_page - Map a virtual address to a physical address
; Input:
;   [esp+4]  = virtual address (page-aligned)
;   [esp+8]  = physical address (page-aligned)
;   [esp+12] = flags (PTE_KERNEL or PTE_USER_RW)
; Returns: EAX = 0 on success, -1 on failure
; ============================================================================
global map_page
map_page:
    push ebx
    push ecx
    push edx
    push edi

    mov eax, [esp + 20]     ; Virtual address
    mov ebx, [esp + 24]     ; Physical address
    mov ecx, [esp + 28]     ; Flags

    ; Calculate page directory index (top 10 bits of virtual address)
    mov edx, eax
    shr edx, 22             ; PDI = vaddr >> 22

    ; Check if page table exists
    mov edi, page_directory
    mov eax, [edi + edx * 4]
    test eax, PTE_PRESENT
    jnz .table_exists

    ; TODO: Allocate new page table if needed
    ; For now, fail if page table doesn't exist
    mov eax, -1
    jmp .done

.table_exists:
    ; Get page table address (clear flags)
    and eax, 0xFFFFF000

    ; Calculate page table index (middle 10 bits)
    mov edx, [esp + 20]     ; Virtual address again
    shr edx, 12
    and edx, 0x3FF          ; PTI = (vaddr >> 12) & 0x3FF

    ; Set page table entry
    or ebx, ecx             ; Combine physical address with flags
    mov [eax + edx * 4], ebx

    ; Flush TLB for this page
    mov eax, [esp + 20]
    invlpg [eax]

    xor eax, eax            ; Return 0 (success)

.done:
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

; ============================================================================
; get_physical_address - Get physical address for a virtual address
; Input: [esp+4] = virtual address
; Returns: EAX = physical address, or 0 if not mapped
; ============================================================================
global get_physical_address
get_physical_address:
    push ebx
    push edx

    mov eax, [esp + 12]     ; Virtual address

    ; Get page directory index
    mov edx, eax
    shr edx, 22

    ; Check page directory entry
    mov ebx, page_directory
    mov ebx, [ebx + edx * 4]
    test ebx, PTE_PRESENT
    jz .not_mapped

    ; Get page table address
    and ebx, 0xFFFFF000

    ; Get page table index
    mov edx, eax
    shr edx, 12
    and edx, 0x3FF

    ; Get page table entry
    mov eax, [ebx + edx * 4]
    test eax, PTE_PRESENT
    jz .not_mapped

    ; Get physical page address and add offset
    and eax, 0xFFFFF000
    mov edx, [esp + 12]     ; Original virtual address
    and edx, 0xFFF          ; Page offset
    or eax, edx             ; Physical address + offset

    jmp .done

.not_mapped:
    xor eax, eax

.done:
    pop edx
    pop ebx
    ret
