# login - User login program
# Displays login prompt, reads username, and spawns a shell
#
# Usage: login
#
# Simple implementation (no password checking):
# - Print "login: " prompt
# - Read username
# - Set environment (future: setuid/setgid)
# - Exec shell
#
# For a bootable system, this is simplified - no actual authentication

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_execve: int32 = 11
const SYS_brk: int32 = 45
const SYS_setuid: int32 = 23
const SYS_setgid: int32 = 46
const SYS_chdir: int32 = 12

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

# Read a line from stdin into buffer
# Returns length read (without newline)
proc readline(buf: ptr uint8, max_len: int32): int32 =
  var i: int32 = 0
  while i < max_len - 1:
    var ch: uint8 = 0
    var n: int32 = syscall3(SYS_read, STDIN, cast[int32](addr(ch)), 1)

    if n <= 0:
      # EOF or error
      break

    # Echo the character
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(ch)), 1)

    if ch == cast[uint8](10):  # newline
      break

    if ch == cast[uint8](13):  # carriage return
      break

    buf[i] = ch
    i = i + 1

  buf[i] = cast[uint8](0)
  return i

proc main() =
  # Allocate working memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 4096
  discard syscall1(SYS_brk, new_brk)

  var username: ptr uint8 = cast[ptr uint8](old_brk)
  var argv: ptr int32 = cast[ptr int32](old_brk + 256)
  var shell_path: ptr uint8 = cast[ptr uint8](old_brk + 512)
  var home_dir: ptr uint8 = cast[ptr uint8](old_brk + 768)

  # Display login prompt
  print(cast[ptr uint8]("login: "))

  # Read username
  var name_len: int32 = readline(username, 128)

  if name_len <= 0:
    print_err(cast[ptr uint8]("\nlogin: no username entered\n"))
    discard syscall1(SYS_exit, 1)

  print(cast[ptr uint8]("\n"))

  # In a real system, we'd check /etc/passwd here
  # For now, just accept any username and proceed

  # Welcome message
  print(cast[ptr uint8]("Welcome to PoodillionOS, "))
  print(username)
  print(cast[ptr uint8]("!\n"))

  # Set home directory
  # For simplicity, use /home/username or just /
  strcpy(home_dir, cast[ptr uint8]("/"))

  # Try to change to home directory
  var chdir_result: int32 = syscall2(SYS_chdir, cast[int32](home_dir), 0)
  if chdir_result < 0:
    print_err(cast[ptr uint8]("login: warning: could not chdir to home\n"))

  # For a minimal system, we skip setuid/setgid
  # In production, you'd parse /etc/passwd and:
  # - syscall1(SYS_setgid, gid)
  # - syscall1(SYS_setuid, uid)

  # Check if root login
  var is_root: int32 = 0
  if strcmp(username, cast[ptr uint8]("root")) == 0:
    is_root = 1
    print(cast[ptr uint8]("# Root access granted #\n"))

  # Prepare to exec shell
  # Try /bin/psh first, then ./bin/psh
  strcpy(shell_path, cast[ptr uint8]("/bin/psh"))
  argv[0] = cast[int32](shell_path)
  argv[1] = 0

  # Try to exec the shell
  discard syscall3(SYS_execve, cast[int32](shell_path), cast[int32](argv), 0)

  # If that fails, try ./bin/psh
  strcpy(shell_path, cast[ptr uint8]("./bin/psh"))
  argv[0] = cast[int32](shell_path)
  discard syscall3(SYS_execve, cast[int32](shell_path), cast[int32](argv), 0)

  # Try /bin/sh
  strcpy(shell_path, cast[ptr uint8]("/bin/sh"))
  argv[0] = cast[int32](shell_path)
  discard syscall3(SYS_execve, cast[int32](shell_path), cast[int32](argv), 0)

  # Try /bin/bash
  strcpy(shell_path, cast[ptr uint8]("/bin/bash"))
  argv[0] = cast[int32](shell_path)
  discard syscall3(SYS_execve, cast[int32](shell_path), cast[int32](argv), 0)

  # If all shells fail
  print_err(cast[ptr uint8]("login: failed to exec shell\n"))
  discard syscall1(SYS_exit, 1)
