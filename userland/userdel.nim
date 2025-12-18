# userdel - Delete a user from the system
# Usage: userdel [-r] USERNAME
# -r: Remove home directory

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_unlink: int32 = 10
const SYS_rmdir: int32 = 40

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0
const O_WRONLY: int32 = 1
const O_CREAT: int32 = 64
const O_TRUNC: int32 = 512

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
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

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768
  discard syscall1(SYS_brk, new_brk)

  var username: ptr uint8 = cast[ptr uint8](old_brk)
  var passwd_path: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var passwd_new: ptr uint8 = cast[ptr uint8](old_brk + 512)
  var passwd_buf: ptr uint8 = cast[ptr uint8](old_brk + 16896)
  var home_path: ptr uint8 = cast[ptr uint8](old_brk + 32256)

  # For simplified version, username is hardcoded
  print(cast[ptr uint8]("userdel: simplified version\n"))
  print(cast[ptr uint8]("Usage: userdel USERNAME\n"))
  print(cast[ptr uint8]("Example username: testuser\n"))

  # Hardcoded username for demo
  username[0] = cast[uint8](116)  # t
  username[1] = cast[uint8](101)  # e
  username[2] = cast[uint8](115)  # s
  username[3] = cast[uint8](116)  # t
  username[4] = cast[uint8](117)  # u
  username[5] = cast[uint8](115)  # s
  username[6] = cast[uint8](101)  # e
  username[7] = cast[uint8](114)  # r
  username[8] = cast[uint8](0)

  var username_len: int32 = strlen(username)

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

  # Read /etc/passwd
  var fd: int32 = syscall3(SYS_open, cast[int32](passwd_path), O_RDONLY, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("userdel: cannot open /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](passwd_buf), 16000)
  discard syscall1(SYS_close, fd)

  if nread < 0:
    print_err(cast[ptr uint8]("userdel: cannot read /etc/passwd\n"))
    discard syscall1(SYS_exit, 1)

  # Parse /etc/passwd and rebuild without the target user
  var i: int32 = 0
  var new_pos: int32 = 0
  var found: int32 = 0

  while i < nread:
    var line_start: int32 = i

    # Parse username field
    var entry_username_start: int32 = i
    while i < nread:
      if passwd_buf[i] == cast[uint8](58):  # colon
        break
      i = i + 1
    var entry_username_end: int32 = i

    # Find end of line
    var line_end: int32 = i
    while line_end < nread:
      if passwd_buf[line_end] == cast[uint8](10):  # newline
        line_end = line_end + 1
        break
      line_end = line_end + 1

    # Check if this is the user to delete
    var match: int32 = 0
    if entry_username_end - entry_username_start == username_len:
      var j: int32 = 0
      match = 1
      while j < username_len:
        if passwd_buf[entry_username_start + j] != username[j]:
          match = 0
          break
        j = j + 1

    if match == 1:
      # Skip this line (don't copy to new buffer)
      found = 1

      # Extract home directory for removal
      var field: int32 = 0
      var k: int32 = line_start
      while k < line_end:
        if passwd_buf[k] == cast[uint8](58):  # colon
          field = field + 1
          if field == 5:
            # This is the home directory field
            k = k + 1
            var home_idx: int32 = 0
            while k < line_end:
              if passwd_buf[k] == cast[uint8](58):  # colon
                break
              home_path[home_idx] = passwd_buf[k]
              home_idx = home_idx + 1
              k = k + 1
            home_path[home_idx] = cast[uint8](0)
            break
        k = k + 1
    else:
      # Copy line to new buffer
      var j: int32 = line_start
      while j < line_end:
        passwd_new[new_pos] = passwd_buf[j]
        new_pos = new_pos + 1
        j = j + 1

    i = line_end

  if found == 0:
    print_err(cast[ptr uint8]("userdel: user '"))
    print_err(username)
    print_err(cast[ptr uint8]("' not found\n"))
    discard syscall1(SYS_exit, 1)

  # Write new /etc/passwd
  fd = syscall3(SYS_open, cast[int32](passwd_path), O_WRONLY + O_TRUNC, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("userdel: cannot open /etc/passwd for writing\n"))
    print_err(cast[ptr uint8]("         (may need root privileges)\n"))
    discard syscall1(SYS_exit, 1)

  var nwritten: int32 = syscall3(SYS_write, fd, cast[int32](passwd_new), new_pos)
  discard syscall1(SYS_close, fd)

  if nwritten != new_pos:
    print_err(cast[ptr uint8]("userdel: failed to write new passwd file\n"))
    discard syscall1(SYS_exit, 1)

  print(cast[ptr uint8]("userdel: user '"))
  print(username)
  print(cast[ptr uint8]("' deleted successfully\n"))

  # Attempt to remove home directory
  if strlen(home_path) > 0:
    var rmdir_result: int32 = syscall1(SYS_rmdir, cast[int32](home_path))
    if rmdir_result < 0:
      print(cast[ptr uint8]("userdel: warning: could not remove home directory "))
      print(home_path)
      print(cast[ptr uint8]("\n         (may not be empty or may not exist)\n"))
    else:
      print(cast[ptr uint8]("userdel: removed home directory "))
      print(home_path)
      print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
