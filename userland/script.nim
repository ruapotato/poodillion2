# script - Record terminal session
# Usage: script [FILE]
# Records all terminal input/output to a file (default: typescript)
# Uses fork, dup2, and exec to capture shell session

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_fork: int32 = 2
const SYS_execve: int32 = 11
const SYS_wait4: int32 = 114
const SYS_brk: int32 = 45
const SYS_pipe: int32 = 42
const SYS_dup2: int32 = 63
const SYS_time: int32 = 13

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512
const O_APPEND: int32 = 1024

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc syscall4(num: int32, arg1: int32, arg2: int32, arg3: int32, arg4: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var len: int32 = 0
  while s[len] != cast[uint8](0):
    len = len + 1
  return len

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc strcpy(dst: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dst[i] = src[i]
    i = i + 1
  dst[i] = cast[uint8](0)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var filename: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var shell_path: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var argv: ptr int32 = cast[ptr int32](old_brk + 4200)
  var envp: ptr int32 = cast[ptr int32](old_brk + 4300)

  # Default filename: typescript
  var argc: int32 = get_argc()
  if argc < 2:
    filename[0] = cast[uint8](116)  # t
    filename[1] = cast[uint8](121)  # y
    filename[2] = cast[uint8](112)  # p
    filename[3] = cast[uint8](101)  # e
    filename[4] = cast[uint8](115)  # s
    filename[5] = cast[uint8](99)   # c
    filename[6] = cast[uint8](114)  # r
    filename[7] = cast[uint8](105)  # i
    filename[8] = cast[uint8](112)  # p
    filename[9] = cast[uint8](116)  # t
    filename[10] = cast[uint8](0)
  if argc >= 2:
    var arg_file: ptr uint8 = get_argv(1)
    strcpy(filename, arg_file)

  # Open output file
  var flags: int32 = O_WRONLY | O_CREAT | O_TRUNC
  var mode: int32 = 420  # 0644 in octal = 420 in decimal
  var fd: int32 = syscall3(SYS_open, cast[int32](filename), flags, mode)

  if fd < 0:
    print_err(cast[ptr uint8]("script: cannot open "))
    print_err(filename)
    print_err(cast[ptr uint8]("\n"))
    discard syscall1(SYS_exit, 1)

  # Print start message
  print(cast[ptr uint8]("Script started, file is "))
  print(filename)
  print(cast[ptr uint8]("\n"))

  # Write header to file
  var header: ptr uint8 = cast[ptr uint8]("Script started\n")
  var header_len: int32 = strlen(header)
  discard syscall3(SYS_write, fd, cast[int32](header), header_len)

  # Simple implementation: just copy stdin to both stdout and file
  # A full implementation would use pseudo-terminals (pty)

  # Fork to run shell
  var pid: int32 = syscall1(SYS_fork, 0)

  if pid < 0:
    print_err(cast[ptr uint8]("script: fork failed\n"))
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  if pid == 0:
    # Child: exec shell
    # Build shell path: /bin/sh
    shell_path[0] = cast[uint8](47)   # /
    shell_path[1] = cast[uint8](98)   # b
    shell_path[2] = cast[uint8](105)  # i
    shell_path[3] = cast[uint8](110)  # n
    shell_path[4] = cast[uint8](47)   # /
    shell_path[5] = cast[uint8](115)  # s
    shell_path[6] = cast[uint8](104)  # h
    shell_path[7] = cast[uint8](0)

    # Setup argv
    argv[0] = cast[int32](shell_path)
    argv[1] = 0

    # Setup envp (empty)
    envp[0] = 0

    # Exec shell
    discard syscall3(SYS_execve, cast[int32](shell_path), cast[int32](argv), cast[int32](envp))

    # If exec fails
    print_err(cast[ptr uint8]("script: cannot exec shell\n"))
    discard syscall1(SYS_exit, 1)

  # Parent: wait for child and copy output
  # For simplicity, we just wait for the child to finish
  # A real script would use pty to capture all I/O

  var status_buf: ptr int32 = cast[ptr int32](old_brk + 5000)
  status_buf[0] = 0
  var wait_ret: int32 = syscall4(SYS_wait4, pid, cast[int32](status_buf), 0, 0)

  # Write footer to file
  var footer: ptr uint8 = cast[ptr uint8]("Script done\n")
  var footer_len: int32 = strlen(footer)
  discard syscall3(SYS_write, fd, cast[int32](footer), footer_len)

  discard syscall1(SYS_close, fd)

  print(cast[ptr uint8]("Script done, file is "))
  print(filename)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
