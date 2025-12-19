# find - Search for files in directory hierarchy
# Usage: find [PATH] [-name PATTERN]
# Simple glob matching: * matches anything

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_lstat64: int32 = 196
const SYS_getdents64: int32 = 220

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0
const O_DIRECTORY: int32 = 65536  # 0x10000

# File mode bits
const S_IFMT: int32 = 61440    # 0170000 - file type mask
const S_IFDIR: int32 = 16384   # 0040000 - directory

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(i: int32): ptr uint8

# String utilities
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

proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while true:
    if s1[i] != s2[i]:
      return 1
    if s1[i] == cast[uint8](0):
      return 0
    i = i + 1
  return 0

proc strcpy(dest: ptr uint8, src: ptr uint8): int32 =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)
  return i

# Simple glob matching - supports * wildcard only
proc glob_match(name: ptr uint8, pattern: ptr uint8): int32 =
  var ni: int32 = 0
  var pi: int32 = 0
  var star_pos: int32 = -1
  var name_pos: int32 = 0

  while name[ni] != cast[uint8](0):
    if pattern[pi] == cast[uint8](42):  # '*'
      star_pos = pi
      name_pos = ni
      pi = pi + 1
    else:
      if pattern[pi] == name[ni]:
        ni = ni + 1
        pi = pi + 1
      else:
        if star_pos == -1:
          return 0
        else:
          pi = star_pos + 1
          name_pos = name_pos + 1
          ni = name_pos

  # Check if remaining pattern is all stars
  while pattern[pi] == cast[uint8](42):
    pi = pi + 1

  if pattern[pi] == cast[uint8](0):
    return 1
  else:
    return 0

# Append path component
proc path_append(path: ptr uint8, name: ptr uint8) =
  var path_len: int32 = strlen(path)
  # Add slash if needed
  if path_len > 0 and path[path_len - 1] != cast[uint8](47):
    path[path_len] = cast[uint8](47)  # '/'
    path_len = path_len + 1
  # Copy name
  var i: int32 = 0
  while name[i] != cast[uint8](0):
    path[path_len + i] = name[i]
    i = i + 1
  path[path_len + i] = cast[uint8](0)

# Global variables for recursion
var global_stat_buf: ptr uint8 = cast[ptr uint8](0)
var global_dent_buf: ptr uint8 = cast[ptr uint8](0)
var global_path_buf: ptr uint8 = cast[ptr uint8](0)
var global_pattern: ptr uint8 = cast[ptr uint8](0)
var global_match_all: int32 = 1

# Search for files recursively
proc search_files(path: ptr uint8) =
  # Get file stats
  var ret: int32 = syscall2(SYS_lstat64, cast[int32](path), cast[int32](global_stat_buf))
  if ret < 0:
    return

  var mode_ptr: ptr uint32 = cast[ptr uint32](cast[int32](global_stat_buf) + 16)
  var mode: int32 = cast[int32](mode_ptr[0])

  # Check if directory
  if (mode & S_IFMT) != S_IFDIR:
    # It's a file - check if it matches
    if global_match_all == 1:
      print(path)
      discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    else:
      # Extract filename from path
      var last_slash: int32 = -1
      var i: int32 = 0
      while path[i] != cast[uint8](0):
        if path[i] == cast[uint8](47):  # '/'
          last_slash = i
        i = i + 1

      var filename: ptr uint8 = path
      if last_slash >= 0:
        filename = cast[ptr uint8](cast[int32](path) + last_slash + 1)

      if glob_match(filename, global_pattern) == 1:
        print(path)
        discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
    return

  # It's a directory - print it first if matches
  if global_match_all == 1:
    print(path)
    discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
  else:
    # Extract directory name from path
    var last_slash: int32 = -1
    var i: int32 = 0
    while path[i] != cast[uint8](0):
      if path[i] == cast[uint8](47):  # '/'
        last_slash = i
      i = i + 1

    var dirname: ptr uint8 = path
    if last_slash >= 0:
      dirname = cast[ptr uint8](cast[int32](path) + last_slash + 1)

    if glob_match(dirname, global_pattern) == 1:
      print(path)
      discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

  # Open directory
  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY | O_DIRECTORY, 0)
  if fd < 0:
    return

  # Read directory entries - process files first, then recurse into directories
  # This avoids buffer corruption from recursive getdents64 calls
  var nread: int32 = syscall3(SYS_getdents64, fd, cast[int32](global_dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](global_dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](global_dent_buf) + pos + 19)
      var d_type: ptr uint8 = cast[ptr uint8](cast[int32](global_dent_buf) + pos + 18)

      # Skip . and ..
      var skip: int32 = 0
      if d_name[0] == cast[uint8](46):  # '.'
        if d_name[1] == cast[uint8](0):
          skip = 1
        else:
          if d_name[1] == cast[uint8](46) and d_name[2] == cast[uint8](0):
            skip = 1

      if skip == 0:
        # Build full path
        var old_len: int32 = strcpy(global_path_buf, path)
        path_append(global_path_buf, d_name)

        # Check if it's a file (not a directory)
        # d_type: 4 = directory, 8 = regular file
        if d_type[0] != cast[uint8](4):
          # It's a file - check if it matches and print
          if global_match_all == 1:
            print(global_path_buf)
            discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)
          else:
            if glob_match(d_name, global_pattern) == 1:
              print(global_path_buf)
              discard syscall3(SYS_write, STDOUT, cast[int32]("\n"), 1)

        # Restore path
        global_path_buf[old_len] = cast[uint8](0)

      pos = pos + reclen

    nread = syscall3(SYS_getdents64, fd, cast[int32](global_dent_buf), 8192)

  discard syscall1(SYS_close, fd)

  # Now reopen and recurse into subdirectories
  fd = syscall3(SYS_open, cast[int32](path), O_RDONLY | O_DIRECTORY, 0)
  if fd < 0:
    return

  nread = syscall3(SYS_getdents64, fd, cast[int32](global_dent_buf), 8192)

  while nread > 0:
    var pos: int32 = 0
    while pos < nread:
      var reclen_ptr: ptr uint16 = cast[ptr uint16](cast[int32](global_dent_buf) + pos + 16)
      var reclen: int32 = cast[int32](reclen_ptr[0])
      var d_name: ptr uint8 = cast[ptr uint8](cast[int32](global_dent_buf) + pos + 19)
      var d_type: ptr uint8 = cast[ptr uint8](cast[int32](global_dent_buf) + pos + 18)

      # Skip . and ..
      var skip: int32 = 0
      if d_name[0] == cast[uint8](46):  # '.'
        if d_name[1] == cast[uint8](0):
          skip = 1
        else:
          if d_name[1] == cast[uint8](46) and d_name[2] == cast[uint8](0):
            skip = 1

      if skip == 0:
        # Check if it's a directory
        if d_type[0] == cast[uint8](4):
          # Build full path
          var old_len: int32 = strcpy(global_path_buf, path)
          path_append(global_path_buf, d_name)

          # Recurse into subdirectory
          search_files(global_path_buf)

          # Restore path
          global_path_buf[old_len] = cast[uint8](0)

      pos = pos + reclen

    nread = syscall3(SYS_getdents64, fd, cast[int32](global_dent_buf), 8192)

  discard syscall1(SYS_close, fd)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 20480
  discard syscall1(SYS_brk, new_brk)

  # Memory layout:
  # old_brk + 0: stat buffer (256 bytes)
  # old_brk + 256: getdents buffer (8KB)
  # old_brk + 8448: path buffer (4KB)
  global_stat_buf = cast[ptr uint8](old_brk)
  global_dent_buf = cast[ptr uint8](old_brk + 256)
  global_path_buf = cast[ptr uint8](old_brk + 8448)

  # Parse arguments
  var argc: int32 = get_argc()
  var target_path: ptr uint8 = cast[ptr uint8](".")
  global_pattern = cast[ptr uint8](0)
  global_match_all = 1

  var i: int32 = 1
  while i < argc:
    var arg: ptr uint8 = get_argv(i)

    # Check for -name flag
    if arg[0] == cast[uint8](45):  # '-'
      if arg[1] == cast[uint8](110):  # 'n' for -name
        # Next argument is the pattern
        i = i + 1
        if i < argc:
          global_pattern = get_argv(i)
          global_match_all = 0
    else:
      # It's a path
      target_path = arg

    i = i + 1

  # Search for files
  search_files(target_path)

  discard syscall1(SYS_exit, 0)
