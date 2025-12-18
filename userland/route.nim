# route - Display IP routing table
# Reads from /proc/net/route

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

proc hexchar_to_int(c: uint8): int32 =
  if c >= cast[uint8](48):
    if c <= cast[uint8](57):
      return cast[int32](c) - 48
  if c >= cast[uint8](65):
    if c <= cast[uint8](70):
      return cast[int32](c) - 65 + 10
  if c >= cast[uint8](97):
    if c <= cast[uint8](102):
      return cast[int32](c) - 97 + 10
  return 0

proc int_to_char(val: int32): uint8 =
  if val < 10:
    return cast[uint8](val + 48)
  return cast[uint8](0)

proc hex_to_ip(hex_str: ptr uint8, out: ptr uint8) =
  # Convert hex IP (little endian) to dotted decimal
  # Example: 00000000 -> 0.0.0.0
  var i: int32 = 0
  var j: int32 = 0
  var octet: int32 = 0

  while i < 8:
    var byte_val: int32 = hexchar_to_int(hex_str[i]) * 16 + hexchar_to_int(hex_str[i + 1])

    # Convert to decimal string
    var d1: int32 = byte_val / 100
    var d2: int32 = (byte_val % 100) / 10
    var d3: int32 = byte_val % 10

    if d1 > 0:
      out[j] = int_to_char(d1)
      j = j + 1
      out[j] = int_to_char(d2)
      j = j + 1
      out[j] = int_to_char(d3)
      j = j + 1
    if d1 == 0:
      if d2 > 0:
        out[j] = int_to_char(d2)
        j = j + 1
        out[j] = int_to_char(d3)
        j = j + 1
      if d2 == 0:
        out[j] = int_to_char(d3)
        j = j + 1

    octet = octet + 1
    if octet < 4:
      out[j] = cast[uint8](46)  # .
      j = j + 1

    i = i + 2

  out[j] = cast[uint8](0)

proc pad_string(s: ptr uint8, width: int32) =
  var len: int32 = strlen(s)
  while len < width:
    print(cast[ptr uint8](" "))
    len = len + 1

proc parse_route_line(line: ptr uint8, iface: ptr uint8, dest: ptr uint8, gateway: ptr uint8, mask: ptr uint8) =
  # Parse /proc/net/route format:
  # Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT
  # eth0  00000000    0102A8C0 0003  0      0   0      00000000 0   0   0

  var i: int32 = 0
  var j: int32 = 0

  # Parse interface name (first field)
  while line[i] != cast[uint8](9):  # tab
    if line[i] == cast[uint8](0):
      return
    iface[j] = line[i]
    i = i + 1
    j = j + 1
  iface[j] = cast[uint8](0)

  # Skip tab
  i = i + 1

  # Parse destination (second field)
  j = 0
  while line[i] != cast[uint8](9):
    if line[i] == cast[uint8](0):
      return
    dest[j] = line[i]
    i = i + 1
    j = j + 1
  dest[j] = cast[uint8](0)

  # Skip tab
  i = i + 1

  # Parse gateway (third field)
  j = 0
  while line[i] != cast[uint8](9):
    if line[i] == cast[uint8](0):
      return
    gateway[j] = line[i]
    i = i + 1
    j = j + 1
  gateway[j] = cast[uint8](0)

  # Skip to mask field (fields 4-7)
  var field: int32 = 3
  while field < 7:
    while line[i] != cast[uint8](9):
      if line[i] == cast[uint8](0):
        return
      i = i + 1
    i = i + 1
    field = field + 1

  # Parse mask (8th field)
  j = 0
  while line[i] != cast[uint8](9):
    if line[i] == cast[uint8](0):
      if line[i] == cast[uint8](10):
        if i >= 0:
          i = i
      if line[i] != cast[uint8](0):
        if line[i] != cast[uint8](10):
          mask[j] = line[i]
          j = j + 1
          i = i + 1
    if line[i] == cast[uint8](9):
      if i >= 0:
        i = i
    if line[i] != cast[uint8](9):
      if line[i] == cast[uint8](0):
        if i >= 0:
          i = i
      if line[i] == cast[uint8](10):
        if i >= 0:
          i = i
      if line[i] != cast[uint8](0):
        if line[i] != cast[uint8](10):
          mask[j] = line[i]
          j = j + 1
          i = i + 1
  mask[j] = cast[uint8](0)

proc main() =
  # Allocate memory
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  var path: ptr uint8 = cast[ptr uint8](old_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk + 256)
  var line_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192)
  var iface_buf: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512)
  var dest_hex: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 64)
  var gw_hex: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 128)
  var mask_hex: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 192)
  var dest_ip: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 256)
  var gw_ip: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 320)
  var mask_ip: ptr uint8 = cast[ptr uint8](old_brk + 8192 + 512 + 384)

  # Build /proc/net/route path
  path[0] = cast[uint8](47)   # /
  path[1] = cast[uint8](112)  # p
  path[2] = cast[uint8](114)  # r
  path[3] = cast[uint8](111)  # o
  path[4] = cast[uint8](99)   # c
  path[5] = cast[uint8](47)   # /
  path[6] = cast[uint8](110)  # n
  path[7] = cast[uint8](101)  # e
  path[8] = cast[uint8](116)  # t
  path[9] = cast[uint8](47)   # /
  path[10] = cast[uint8](114) # r
  path[11] = cast[uint8](111) # o
  path[12] = cast[uint8](117) # u
  path[13] = cast[uint8](116) # t
  path[14] = cast[uint8](101) # e
  path[15] = cast[uint8](0)

  var fd: int32 = syscall3(SYS_open, cast[int32](path), O_RDONLY, 0)
  if fd < 0:
    print(cast[ptr uint8]("route: cannot open /proc/net/route\n"))
    discard syscall1(SYS_exit, 1)

  var nread: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 8192)
  discard syscall1(SYS_close, fd)

  if nread <= 0:
    print(cast[ptr uint8]("route: cannot read routing table\n"))
    discard syscall1(SYS_exit, 1)

  # Print header
  print(cast[ptr uint8]("Kernel IP routing table\n"))
  print(cast[ptr uint8]("Destination     Gateway         Genmask         Iface\n"))

  # Parse line by line
  var line_start: int32 = 0
  var i: int32 = 0
  var first_line: int32 = 1

  while i < nread:
    if buffer[i] == cast[uint8](10):  # newline
      # Skip header line
      if first_line == 1:
        first_line = 0
        line_start = i + 1
        i = i + 1
        if i >= nread:
          return
      if first_line == 0:
        # Copy line to line_buf
        var j: int32 = 0
        var k: int32 = line_start
        while k < i:
          line_buf[j] = buffer[k]
          j = j + 1
          k = k + 1
        line_buf[j] = cast[uint8](0)

        # Parse the line
        parse_route_line(line_buf, iface_buf, dest_hex, gw_hex, mask_hex)

        # Convert hex to IP
        hex_to_ip(dest_hex, dest_ip)
        hex_to_ip(gw_hex, gw_ip)
        hex_to_ip(mask_hex, mask_ip)

        # Print route entry
        print(dest_ip)
        pad_string(dest_ip, 16)

        print(gw_ip)
        pad_string(gw_ip, 16)

        print(mask_ip)
        pad_string(mask_ip, 16)

        print(iface_buf)
        print(cast[ptr uint8]("\n"))

        line_start = i + 1

    i = i + 1

  discard syscall1(SYS_exit, 0)
