# line - Draw a line from (x1,y1) to (x2,y2)
# Usage: line <x1> <y1> <x2> <y2> <color>
# Uses Bresenham's line algorithm

const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_ioctl: int32 = 54
const SYS_write: int32 = 4
const SYS_lseek: int32 = 19
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const O_RDWR: int32 = 2
const FBIOGET_VSCREENINFO: int32 = 0x4600
const SEEK_SET: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(msg: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc my_abs(x: int32): int32 =
  if x < 0:
    return -x
  else:
    return x

proc plot_pixel(fd: int32, x: int32, y: int32, xres: int32, yres: int32, color: int32, pixel_buf: ptr uint32) =
  if x < 0 or x >= xres or y < 0 or y >= yres:
    return

  var offset: int32 = (y * xres + x) * 4
  discard syscall3(SYS_lseek, fd, offset, SEEK_SET)
  pixel_buf[0] = color
  discard syscall3(SYS_write, fd, cast[int32](pixel_buf), 4)

proc main() =
  # For testing: Draw diagonal line (0,0) to (200,200)
  var x1: int32 = 0
  var y1: int32 = 0
  var x2: int32 = 200
  var y2: int32 = 200
  var color: int32 = 0x00FF00  # Green

  var fd: int32 = syscall2(SYS_open, cast[int32]("/dev/fb0"), O_RDWR)
  if fd < 0:
    print(cast[ptr uint8]("Error: Cannot open /dev/fb0\n"), 29)
    discard syscall1(SYS_exit, 1)

  # Get screen info
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 160
  discard syscall1(SYS_brk, new_brk)
  var vinfo: ptr uint32 = cast[ptr uint32](old_brk)

  var result: int32 = syscall3(SYS_ioctl, fd, FBIOGET_VSCREENINFO, cast[int32](vinfo))
  if result < 0:
    print(cast[ptr uint8]("Error: Cannot get screen info\n"), 31)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  var xres: int32 = cast[int32](vinfo[0])
  var yres: int32 = cast[int32](vinfo[1])

  # Allocate pixel buffer
  var pixel_brk: int32 = syscall1(SYS_brk, 0)
  discard syscall1(SYS_brk, pixel_brk + 4)
  var pixel: ptr uint32 = cast[ptr uint32](pixel_brk)

  # Bresenham's line algorithm
  var dx: int32 = my_abs(x2 - x1)
  var dy: int32 = my_abs(y2 - y1)
  var sx: int32 = if x1 < x2: 1 else: -1
  var sy: int32 = if y1 < y2: 1 else: -1
  var err: int32 = dx - dy
  var x: int32 = x1
  var y: int32 = y1

  while true:
    plot_pixel(fd, x, y, xres, yres, color, pixel)

    if x == x2 and y == y2:
      break

    var e2: int32 = 2 * err
    if e2 > -dy:
      err = err - dy
      x = x + sx
    if e2 < dx:
      err = err + dx
      y = y + sy

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)

main()
