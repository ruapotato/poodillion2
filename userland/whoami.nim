# whoami - Print the current username
# Uses getuid() and parses /etc/passwd to find username

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_getuid: int32 = 24

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
  # Get current user ID
  var uid: int32 = syscall1(SYS_getuid, 0)

  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)

  # Build path: /etc/passwd
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](101)  # e
  path[2] = cast[uint8](116)  # t
  path[3] = cast[uint8](99)   # c
  path[4] = cast[uint8](47)   # /
  path[5] = cast[uint8](112)  # p
  path[6] = cast[uint8](97)   # a
  path[7] = cast[uint8](115)  # s
  path[8] = cast[uint8](115)  # s
  path[9] = cast[uint8](119)  # w
  path[10] = cast[uint8](100) # d
  path[11] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("whoami: cannot open /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 16000)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("whoami: cannot read /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  buffer[nread] = cast[uint8](0)

  # Parse /etc/passwd
  # Format: username:password:uid:gid:comment:home:shell
  var i: int32 = 0
  var found: int32 = 0

  while i < nread:
    var line_start: int32 = i

    # Find username (first field before first colon)
    var username_start: int32 = i
    while i < nread:
      if buffer[i] == cast[uint8](58):  # colon
        break
      i = i + 1
    var username_end: int32 = i

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

    var entry_uid: int32 = parse_int(buffer, uid_start, uid_end)

    # Check if this is our user
    if entry_uid == uid:
      # Print username
      var j: int32 = username_start
      while j < username_end:
        discard syscall3(SYS_write, STDOUT, cast[int32](cast[ptr uint8](cast[int32](buffer) + j)), 1)
        j = j + 1
      print(cast[ptr uint8]("\n"))
      found = 1
      break

    # Skip to next line
    while i < nread:
      if buffer[i] == cast[uint8](10):  # newline
        i = i + 1
        break
      i = i + 1

  if found == 0:
    print(cast[ptr uint8]("whoami: unknown user\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
