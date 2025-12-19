# groupadd - Add a new group to the system
# Usage: groupadd [-g GID] GROUPNAME
# Appends to /etc/group

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2
const O_RDONLY: int32 = 0
const O_WRONLY: int32 = 1
const O_APPEND: int32 = 1024

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

# Find next available GID from /etc/group
proc find_next_gid(group_buf: ptr uint8, nread: int32): int32 =
  var max_gid: int32 = 99  # Start from 100 for regular groups
  var i: int32 = 0

  while i < nread:
    # Skip groupname field
    while i < nread:
      if group_buf[i] == cast[uint8](58):  # colon
        break
      i = i + 1

    # Skip password field
    i = i + 1
    while i < nread:
      if group_buf[i] == cast[uint8](58):  # colon
        break
      i = i + 1

    # Parse GID field
    i = i + 1
    var gid_start: int32 = i
    while i < nread:
      if group_buf[i] == cast[uint8](58):  # colon
        break
      if group_buf[i] == cast[uint8](10):  # newline
        break
      i = i + 1
    var gid_end: int32 = i

    # Calculate GID
    var gid: int32 = 0
    var j: int32 = gid_start
    while j < gid_end:
      if group_buf[j] >= cast[uint8](48):
        if group_buf[j] <= cast[uint8](57):
          gid = gid * 10 + cast[int32](group_buf[j]) - 48
      j = j + 1

    if gid > max_gid:
      max_gid = gid

    # Skip to next line
    while i < nread:
      if group_buf[i] == cast[uint8](10):  # newline
        i = i + 1
        break
      i = i + 1

  return max_gid + 1

# Convert integer to string
proc int_to_str(n: int32, buf: ptr uint8): int32 =
  if n == 0:
    buf[0] = cast[uint8](48)
    buf[1] = cast[uint8](0)
    return 1

  # Count digits
  var temp: int32 = n
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  # Build string
  var pos: int32 = digits - 1
  temp = n
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  buf[digits] = cast[uint8](0)
  return digits

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32768
  discard syscall1(SYS_brk, new_brk)

  var groupname: ptr uint8 = cast[ptr uint8](old_brk)
  var group_path: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var group_buf: ptr uint8 = cast[ptr uint8](old_brk + 512)
  var entry_buf: ptr uint8 = cast[ptr uint8](old_brk + 17024)
  var gid_str: ptr uint8 = cast[ptr uint8](old_brk + 17536)

  # Default values
  var gid: int32 = 0  # Will be auto-assigned

  # For simplified version, groupname is hardcoded
  print(cast[ptr uint8]("groupadd: simplified version\n"))
  print(cast[ptr uint8]("Usage: groupadd GROUPNAME\n"))
  print(cast[ptr uint8]("Example groupname: testgroup\n"))

  # Hardcoded groupname for demo
  groupname[0] = cast[uint8](116)  # t
  groupname[1] = cast[uint8](101)  # e
  groupname[2] = cast[uint8](115)  # s
  groupname[3] = cast[uint8](116)  # t
  groupname[4] = cast[uint8](103)  # g
  groupname[5] = cast[uint8](114)  # r
  groupname[6] = cast[uint8](111)  # o
  groupname[7] = cast[uint8](117)  # u
  groupname[8] = cast[uint8](112)  # p
  groupname[9] = cast[uint8](0)

  # Build path: /etc/group
  group_path[0] = cast[uint8](47)   # /
  group_path[1] = cast[uint8](101)  # e
  group_path[2] = cast[uint8](116)  # t
  group_path[3] = cast[uint8](99)   # c
  group_path[4] = cast[uint8](47)   # /
  group_path[5] = cast[uint8](103)  # g
  group_path[6] = cast[uint8](114)  # r
  group_path[7] = cast[uint8](111)  # o
  group_path[8] = cast[uint8](117)  # u
  group_path[9] = cast[uint8](112)  # p
  group_path[10] = cast[uint8](0)

  # Read /etc/group to find next GID
  var fd: int32 = syscall3(SYS_open, cast[int32](group_path), O_RDONLY, 0)
  if fd < 0:
    # File might not exist, create it
    print(cast[ptr uint8]("groupadd: /etc/group does not exist, will create\n"))
    gid = 100
  else:
    var nread: int32 = syscall3(SYS_read, fd, cast[int32](group_buf), 16000)
    discard syscall1(SYS_close, fd)

    if nread < 0:
      print_err(cast[ptr uint8]("groupadd: cannot read /etc/group\n"))
      discard syscall1(SYS_exit, 1)

    # Find next available GID
    if gid == 0:
      gid = find_next_gid(group_buf, nread)

  # Convert GID to string
  discard int_to_str(gid, gid_str)

  # Build /etc/group entry: groupname:x:gid:
  var pos: int32 = 0

  # Groupname
  var i: int32 = 0
  while groupname[i] != cast[uint8](0):
    entry_buf[pos] = groupname[i]
    pos = pos + 1
    i = i + 1

  # :x:
  entry_buf[pos] = cast[uint8](58)  # :
  pos = pos + 1
  entry_buf[pos] = cast[uint8](120) # x
  pos = pos + 1
  entry_buf[pos] = cast[uint8](58)  # :
  pos = pos + 1

  # GID
  i = 0
  while gid_str[i] != cast[uint8](0):
    entry_buf[pos] = gid_str[i]
    pos = pos + 1
    i = i + 1

  # :
  entry_buf[pos] = cast[uint8](58)  # :
  pos = pos + 1

  # Newline
  entry_buf[pos] = cast[uint8](10)   # \n
  pos = pos + 1

  # Open /etc/group for appending
  fd = syscall3(SYS_open, cast[int32](group_path), O_WRONLY + O_APPEND, 0)
  if fd < 0:
    print_err(cast[ptr uint8]("groupadd: cannot open /etc/group for writing\n"))
    print_err(cast[ptr uint8]("          (may need root privileges)\n"))
    discard syscall1(SYS_exit, 1)

  # Write entry
  var nwritten: int32 = syscall3(SYS_write, fd, cast[int32](entry_buf), pos)
  discard syscall1(SYS_close, fd)

  if nwritten != pos:
    print_err(cast[ptr uint8]("groupadd: failed to write entry\n"))
    discard syscall1(SYS_exit, 1)

  print(cast[ptr uint8]("groupadd: group '"))
  print(groupname)
  print(cast[ptr uint8]("' created successfully\n"))
  print(cast[ptr uint8]("  GID: "))
  print(gid_str)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
