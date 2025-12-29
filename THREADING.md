# BrainhairOS Kernel Threading Implementation

## Overview

This document describes the kernel-level threading support added to BrainhairOS. The implementation provides basic threading capabilities allowing multiple threads of execution within a single process, sharing the same address space.

## Architecture

### Thread Model

- **Kernel-level threads**: All threads are managed by the kernel scheduler
- **Shared address space**: Threads within a process share the same page directory
- **Independent stacks**: Each thread has its own kernel stack (4KB)
- **Cooperative scheduling**: Threads can yield voluntarily using `thread_yield()`
- **Simple lifecycle**: Create, run, yield, exit

### PCB Extensions

The Process Control Block (PCB) structure has been extended with thread-specific fields:

```asm
PCB_IS_THREAD equ 100  ; int32 - 1 if thread, 0 if process
PCB_MAIN_PROC equ 104  ; int32 - Main process PID (for threads)
PCB_THREAD_ID equ 108  ; int32 - Thread ID within process
PCB_NEXT_TID  equ 112  ; int32 - Next thread ID to assign (main process only)
```

- `PCB_IS_THREAD`: Boolean flag indicating whether this is a thread or process
- `PCB_MAIN_PROC`: PID of the main process (for threads); self-referential for processes
- `PCB_THREAD_ID`: Thread ID within the process (0 for main process)
- `PCB_NEXT_TID`: Counter for allocating thread IDs (only used by main process)

## API Functions

### Kernel Functions (in kernel/process.asm)

#### `thread_create(entry, stack_ptr)`
Creates a new thread within the current process.

**Parameters:**
- `entry` (int32): Entry point address (function pointer)
- `stack_ptr` (int32): Optional stack pointer (0 = auto-allocate)

**Returns:**
- PID of the new thread (positive integer) on success
- -1 on failure (no free slots)

**Behavior:**
- Allocates a free PCB slot for the thread
- Assigns a unique thread ID
- Shares page directory with parent process
- Copies most PCB fields from main process (UID, GID, etc.)
- Creates independent kernel stack
- Sets thread state to READY
- Thread begins execution at the specified entry point

#### `thread_exit(code)`
Terminates the current thread.

**Parameters:**
- `code` (int32): Exit code (currently unused)

**Returns:** Never returns

**Behavior:**
- If called from a thread: marks PCB as UNUSED and schedules next process
- If called from a process: delegates to `exit_process()`
- Decrements ready process count
- Context switches to another ready process

#### `thread_yield()`
Voluntarily yields CPU to another ready thread/process.

**Parameters:** None

**Returns:** None (returns when scheduled again)

**Behavior:**
- Calls the scheduler to find next ready process
- Performs context switch if different from current
- Preserves all thread state and registers

#### `get_thread_id()`
Returns the thread ID of the current execution context.

**Returns:**
- Thread ID (int32): 0 for main process, 1+ for threads

#### `is_thread()`
Checks if current execution context is a thread.

**Returns:**
- 1 if current context is a thread
- 0 if current context is a process

### System Calls (userland interface)

The threading API is exposed to userland through syscalls:

- **SYS_thread_create (200)**: Create a new thread
- **SYS_thread_exit (201)**: Exit current thread
- **SYS_thread_yield (202)**: Yield CPU to other threads
- **SYS_get_thread_id (203)**: Get current thread ID
- **SYS_is_thread (204)**: Check if running in thread context

Syscall handlers are implemented in `kernel/isr.asm` (Linux syscall interface, int 0x80).

## Implementation Details

### Thread Creation Process

1. **Determine main process**: If called from a thread, find its main process
2. **Allocate thread ID**: Increment `PCB_NEXT_TID` in main process
3. **Find free PCB slot**: Search process table for PROC_UNUSED entry
4. **Copy parent PCB**: Start with a copy of main process PCB
5. **Set thread-specific fields**:
   - Mark as thread (`PCB_IS_THREAD = 1`)
   - Set main process PID
   - Assign thread ID
   - Set entry point
6. **Allocate/assign stack**:
   - Auto-allocate: Use kernel stack area (4KB per process slot)
   - Manual: Use provided stack pointer
7. **Share address space**: Copy page directory pointer from main process
8. **Initialize registers**: Clear all general-purpose registers
9. **Set state to READY**: Thread is now schedulable

### Scheduler Behavior

The existing round-robin scheduler handles threads transparently:
- Threads are scheduled like processes (they occupy PCB slots)
- Context switching preserves all CPU state (registers, flags, stack, EIP)
- Page directory is loaded from PCB (shared for threads in same process)
- No special thread-aware logic needed - the shared page directory is key

### Memory Management

**Shared:**
- Code segment (page directory)
- Data segment (page directory)
- Heap (page directory)
- Global variables (page directory)

**Per-thread:**
- Kernel stack (4KB in `kernel_stacks` area)
- CPU registers (saved in PCB during context switch)
- Stack pointer (ESP)
- Instruction pointer (EIP)

### Synchronization

**Current implementation:**
- No mutex/semaphore primitives (future work)
- No atomic operations
- Race conditions possible with shared data
- Suitable for cooperative, simple multi-threading scenarios

### Limitations

1. **No thread-local storage (TLS)**: All variables are shared or on stack
2. **No thread synchronization primitives**: No mutexes, semaphores, or condition variables
3. **No thread join/wait**: Cannot wait for a specific thread to complete
4. **Limited thread slots**: Maximum threads = MAX_PROCS (currently 16)
5. **Cooperative scheduling**: Relies on voluntary yielding (no preemption from timer)
6. **No thread priorities**: All threads scheduled round-robin equally

## Usage Example

See `userland/thread_test.bh` for a complete example. Basic usage:

```brainhair
import "lib/syscalls"

proc worker_thread() =
  var tid: int32 = get_thread_id()
  print_msg("Thread ")
  print_int(tid)
  print_msg(" running\n")

  # Do some work
  var i: int32 = 0
  while i < 10:
    # Work...
    thread_yield()  # Allow other threads to run
    i = i + 1

  thread_exit(0)

proc main(): int32 =
  # Create threads
  var t1: int32 = thread_create(cast[int32](addr(worker_thread)), 0)
  var t2: int32 = thread_create(cast[int32](addr(worker_thread)), 0)

  # Main thread continues...
  thread_yield()

  return 0
```

## Testing

Run the threading test:

```bash
# Build the kernel with threading support
make microkernel

# Run in QEMU
make run-microkernel

# In the kernel, the thread test can be executed
# (Note: Integration with shell/launcher may be needed)
```

The test program (`bin/thread_test`) demonstrates:
- Creating multiple threads
- Concurrent execution with yielding
- Shared memory access (counter variable)
- Thread identification (PID, TID)

## Files Modified

### Core Implementation
- `kernel/process.asm`: Thread management functions, PCB structure
- `kernel/kernel_main.bh`: Thread function declarations
- `kernel/isr.asm`: Syscall handlers for threading API

### Test Program
- `userland/thread_test.bh`: Comprehensive threading test

### Documentation
- `THREADING.md`: This file

## Future Enhancements

1. **Synchronization primitives**:
   - Mutexes (mutex_lock/mutex_unlock)
   - Semaphores (sem_wait/sem_post)
   - Condition variables (cond_wait/cond_signal)

2. **Thread management**:
   - thread_join(): Wait for thread to complete
   - thread_detach(): Mark thread as detached
   - thread_kill(): Forcefully terminate thread

3. **Thread-local storage (TLS)**:
   - Per-thread data segments
   - __thread storage class

4. **Advanced features**:
   - Thread priorities
   - Thread affinity (for multi-core)
   - Thread pools
   - Read-write locks

5. **Preemptive scheduling**:
   - Timer-based preemption for threads
   - Proper interrupt return frame handling

## References

- Process scheduler: `kernel/process.asm`
- Context switching: `kernel/process.asm::context_switch`
- PCB structure: See `PCB_*` constants in `kernel/process.asm`
- Syscall interface: `kernel/isr.asm::isr_linux_syscall`
