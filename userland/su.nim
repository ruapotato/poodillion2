# su - Switch user
# Switches to another user account (default: root)
# Usage: su [USER]

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_setuid: int32 = 23
const SYS_setgid: int32 = 46
const SYS_getuid: int32 = 24
const SYS_execve: int32 = 11

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

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

# String comparison
proc strcmp(s1: ptr uint8, s2: ptr uint8, len: int32): int32 =
  var i: int32 = 0
  while i < len:
    if s1[i] != s2[i]:
      return 1
    if s1[i] == cast[uint8](0):
      return 0
    i = i + 1
  return 0

# Copy string
proc strcpy(dest: ptr uint8, src: ptr uint8, max_len: int32) =
  var i: int32 = 0
  while i < max_len:
    dest[i] = src[i]
    if src[i] == cast[uint8](0):
      break
    i = i + 1

# Parse integer from string
proc parse_int(s: ptr uint8, start: int32, end: int32): int32 =
  var result: int32 = 0
  var i: int32 = start
  while i < end:
    if s[i] >= cast[uint8](48):
      if s[i] <= cast[uint8](57):
        result = result * 10 + cast[int32](s[i]) - 48
    i = i + 1
  return result

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768
  discard syscall1(SYS_brk, new_brk)

  var username: ptr uint8 = cast[ptr uint8](old_brk)
  var passwd_path: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 512)
  var shell_path: ptr uint8 = cast[ptr uint8](old_brk + 16896)
  var shell_argv: ptr ptr uint8 = cast[ptr ptr uint8](old_brk + 17152)
  var shell_envp: ptr ptr uint8 = cast[ptr ptr uint8](old_brk + 17408)

  # Default to root
  # TODO: Parse command line arguments
  # For now, we default to root
  username[0] = cast[uint8](114) # r
  username[1] = cast[uint8](111) # o
  username[2] = cast[uint8](111) # o
  username[3] = cast[uint8](116) # t
  username[4] = cast[uint8](0)

  # Build path: /etc/passwd
  passwd_path[0] = cast[uint8](47)   # /
  passwd_path[1] = cast[uint8](101)  # e
  passwd_path[2] = cast[uint8](116)  # t
  passwd_path[3] = cast[uint8](99)   # c
  passwd_path[4] = cast[uint8](47)   # /
  passwd_path[5] = cast[uint8](112)  # p
  passwd_path[6] = cast[uint8](97)   # a
  passwd_path[7] = cast[uint8](115)  # s
  passwd_path[8] = cast[uint8](115)  # s
  passwd_path[9] = cast[uint8](119)  # w
  passwd_path[10] = cast[uint8](100) # d
  passwd_path[11] = cast[uint8](0)

  # Open /etc/passwd
  var fd: int32 = syscall3(SYS_open, cast[int32](passwd_path), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("su: cannot open /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 16000)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print_err(cast[ptr uint8]("su: cannot read /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  buffer[nread] = cast[uint8](0)

  # Parse /etc/passwd to find user
  # Format: username:password:uid:gid:comment:home:shell
  var i: int32 = 0
  var found: int32 = 0
  var target_uid: int32 = 0
  var target_gid: int32 = 0
  var username_len: int32 = strlen(username)

  while i < nread:
    # Parse username field
    var entry_username_start: int32 = i
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1
    var entry_username_end: int32 = i

    # Check if this matches our target username
    var match: int32 = 0
    if entry_username_end - entry_username_start == username_len:
      var j: int32 = 0
      match = 1
      while j < username_len:
        if buffer[entry_username_start + j] != username[j]:
          match = 0
          break
        j = j + 1

    # Skip password field
    i = i + 1
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1

    # Parse UID field
    i = i + 1
    var uid_start: int32 = i
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1
    var uid_end: int32 = i

    # Parse GID field
    i = i + 1
    var gid_start: int32 = i
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1
    var gid_end: int32 = i

    # Skip comment field
    i = i + 1
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1

    # Skip home field
    i = i + 1
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1

    # Parse shell field
    i = i + 1
    var shell_start: int32 = i
    while i < nread:
      if buffer[i] == cast[uint8](10):  # newline
        break
      if buffer[i] == cast[uint8](0):
        break
      i = i + 1
    var shell_end: int32 = i

    if match == 1:
      # Found the user
      target_uid = parse_int(buffer, uid_start, uid_end)
      target_gid = parse_int(buffer, gid_start, gid_end)

      # Copy shell path
      var k: int32 = 0
      var j: int32 = shell_start
      while j < shell_end:
        shell_path[k] = buffer[j]
        k = k + 1
        j = j + 1
      shell_path[k] = cast[uint8](0)

      found = 1
      break

    # Move to next line
    while i < nread:
      if buffer[i] == cast[uint8](10):  # newline
        i = i + 1
        break
      i = i + 1

  if found == 0:
    print_err(cast[ptr uint8]("su: user not found\n"))
    discard syscall1(SYS_exit, 1)

  # Check if we're already root or have permission
  var current_uid: int32 = syscall1(SYS_getuid, 0)
  if current_uid != 0:
    print_err(cast[ptr uint8]("su: must be root to use su\n"))
    discard syscall1(SYS_exit, 1)

  # Set GID first (must be done before setuid)
  var result: int32 = syscall1(SYS_setgid, target_gid)
  if result < 0:
    print_err(cast[ptr uint8]("su: setgid failed\n"))
    discard syscall1(SYS_exit, 1)

  # Set UID
  result = syscall1(SYS_setuid, target_uid)
  if result < 0:
    print_err(cast[ptr uint8]("su: setuid failed\n"))
    discard syscall1(SYS_exit, 1)

  # Prepare to exec shell
  # argv[0] = shell name, argv[1] = NULL
  shell_argv[0] = shell_path
  shell_argv[1] = cast[ptr uint8](0)

  # Empty environment
  shell_envp[0] = cast[ptr uint8](0)

  # Execute shell
  result = syscall3(SYS_execve, cast[int32](shell_path), cast[int32](shell_argv), cast[int32](shell_envp))

  # If we get here, exec failed
  print_err(cast[ptr uint8]("su: cannot execute shell\n"))
  discard syscall1(SYS_exit, 1)
