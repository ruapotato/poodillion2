# dnsdomainname - Show DNS domain name
# Reads from /etc/resolv.conf or extracts from hostname

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

proc starts_with(line: ptr uint8, prefix: ptr uint8): int32 =
  var i: int32 = 0
  while prefix[i] != cast[uint8](0):
    if line[i] != prefix[i]:
      return 0
    i = i + 1
  return 1

proc extract_domain(line: ptr uint8, domain: ptr uint8) =
  # Extract domain from "domain example.com" or "search example.com"
  var i: int32 = 0

  # Skip "domain" or "search"
  while line[i] != cast[uint8](32):
    if line[i] == cast[uint8](0):
      return
    i = i + 1

  # Skip spaces
  while line[i] == cast[uint8](32):
    i = i + 1

  # Copy domain name
  var j: int32 = 0
  while line[i] != cast[uint8](32):
    if line[i] == cast[uint8](10):
      if i >= 0:
        i = i
    if line[i] == cast[uint8](0):
      if i >= 0:
        i = i
    if line[i] != cast[uint8](32):
      if line[i] != cast[uint8](10):
        if line[i] != cast[uint8](0):
          domain[j] = line[i]
          j = j + 1
          i = i + 1

  domain[j] = cast[uint8](0)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var line_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var domain_buf: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 512)
  var domain_prefix: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 512 + 256)
  var search_prefix: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 512 + 256 + 64)

  # Build /etc/resolv.conf path
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](101)  # e
  path[2] = cast[uint8](116)  # t
  path[3] = cast[uint8](99)   # c
  path[4] = cast[uint8](47)   # /
  path[5] = cast[uint8](114)  # r
  path[6] = cast[uint8](101)  # e
  path[7] = cast[uint8](115)  # s
  path[8] = cast[uint8](111)  # o
  path[9] = cast[uint8](108)  # l
  path[10] = cast[uint8](118) # v
  path[11] = cast[uint8](46)  # .
  path[12] = cast[uint8](99)  # c
  path[13] = cast[uint8](111) # o
  path[14] = cast[uint8](110) # n
  path[15] = cast[uint8](102) # f
  path[16] = cast[uint8](0)

  # Build "domain" prefix
  domain_prefix[0] = cast[uint8](100) # d
  domain_prefix[1] = cast[uint8](111) # o
  domain_prefix[2] = cast[uint8](109) # m
  domain_prefix[3] = cast[uint8](97)  # a
  domain_prefix[4] = cast[uint8](105) # i
  domain_prefix[5] = cast[uint8](110) # n
  domain_prefix[6] = cast[uint8](0)

  # Build "search" prefix
  search_prefix[0] = cast[uint8](115) # s
  search_prefix[1] = cast[uint8](101) # e
  search_prefix[2] = cast[uint8](97)  # a
  search_prefix[3] = cast[uint8](114) # r
  search_prefix[4] = cast[uint8](99)  # c
  search_prefix[5] = cast[uint8](104) # h
  search_prefix[6] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    # If /etc/resolv.conf doesn't exist, try to get from hostname
    var hostname_path: ptr uint8 = cast[ptr uint8](old_brk + 2048)
    hostname_path[0] = cast[uint8](47)   # /
    hostname_path[1] = cast[uint8](112)  # p
    hostname_path[2] = cast[uint8](114)  # r
    hostname_path[3] = cast[uint8](111)  # o
    hostname_path[4] = cast[uint8](99)   # c
    hostname_path[5] = cast[uint8](47)   # /
    hostname_path[6] = cast[uint8](115)  # s
    hostname_path[7] = cast[uint8](121)  # y
    hostname_path[8] = cast[uint8](115)  # s
    hostname_path[9] = cast[uint8](47)   # /
    hostname_path[10] = cast[uint8](107) # k
    hostname_path[11] = cast[uint8](101) # e
    hostname_path[12] = cast[uint8](114) # r
    hostname_path[13] = cast[uint8](110) # n
    hostname_path[14] = cast[uint8](101) # e
    hostname_path[15] = cast[uint8](108) # l
    hostname_path[16] = cast[uint8](47)  # /
    hostname_path[17] = cast[uint8](104) # h
    hostname_path[18] = cast[uint8](111) # o
    hostname_path[19] = cast[uint8](115) # s
    hostname_path[20] = cast[uint8](116) # t
    hostname_path[21] = cast[uint8](110) # n
    hostname_path[22] = cast[uint8](97)  # a
    hostname_path[23] = cast[uint8](109) # m
    hostname_path[24] = cast[uint8](101) # e
    hostname_path[25] = cast[uint8](0)

    fd = syscall3(SYS_open, cast[int32](hostname_path), O_RDONLY, 0)
    if fd < 0:
      discard syscall1(SYS_exit, 1)

    var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 256)
    discard syscall1(SYS_close, fd)

    if nread <= 0:
      discard syscall1(SYS_exit, 1)

    # Remove newline
    if buffer[nread - 1] == cast[uint8](10):
      nread = nread - 1
    buffer[nread] = cast[uint8](0)

    # Extract domain from hostname (after first dot)
    var i: int32 = 0
    var found_dot: int32 = 0
    while i < nread:
      if buffer[i] == cast[uint8](46):  # .
        found_dot = 1
        i = i + 1
        if i < nread:
          if i >= 0:
            i = i
      if found_dot == 1:
        print(cast[ptr uint8](cast[int32](buffer) + i))
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_exit, 0)
      i = i + 1

    discard syscall1(SYS_exit, 1)

  # Read /etc/resolv.conf
  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    discard syscall1(SYS_exit, 1)

  # Parse line by line
  var line_start: int32 = 0
  var i: int32 = 0

  while i < nread:
    if buffer[i] == cast[uint8](10):  # newline
      # Copy line to line_buf
      var j: int32 = 0
      var k: int32 = line_start
      while k < i:
        line_buf[j] = buffer[k]
        j = j + 1
        k = k + 1
      line_buf[j] = cast[uint8](0)

      # Check if line starts with "domain" or "search"
      if starts_with(line_buf, domain_prefix) == 1:
        extract_domain(line_buf, domain_buf)
        print(domain_buf)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_exit, 0)

      if starts_with(line_buf, search_prefix) == 1:
        extract_domain(line_buf, domain_buf)
        print(domain_buf)
        print(cast[ptr uint8]("\n"))
        discard syscall1(SYS_exit, 0)

      line_start = i + 1

    i = i + 1

  discard syscall1(SYS_exit, 1)
