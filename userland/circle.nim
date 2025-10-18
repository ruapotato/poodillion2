# circle - Draw a circle
# Usage: circle <cx> <cy> <radius> <color> [fill]
# Uses midpoint circle algorithm

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

proc plot_pixel(fd: int32, x: int32, y: int32, xres: int32, yres: int32, color: int32, pixel_buf: ptr uint32) =
  if x < 0 or x >= xres or y < 0 or y >= yres:
    return

  var offset: int32 = (y * xres + x) * 4
  discard syscall3(SYS_lseek, fd, offset, SEEK_SET)
  pixel_buf[0] = color
  discard syscall3(SYS_write, fd, cast[int32](pixel_buf), 4)

proc draw_circle_points(fd: int32, cx: int32, cy: int32, x: int32, y: int32, xres: int32, yres: int32, color: int32, pixel: ptr uint32) =
  plot_pixel(fd, cx + x, cy + y, xres, yres, color, pixel)
  plot_pixel(fd, cx - x, cy + y, xres, yres, color, pixel)
  plot_pixel(fd, cx + x, cy - y, xres, yres, color, pixel)
  plot_pixel(fd, cx - x, cy - y, xres, yres, color, pixel)
  plot_pixel(fd, cx + y, cy + x, xres, yres, color, pixel)
  plot_pixel(fd, cx - y, cy + x, xres, yres, color, pixel)
  plot_pixel(fd, cx + y, cy - x, xres, yres, color, pixel)
  plot_pixel(fd, cx - y, cy - x, xres, yres, color, pixel)

proc main() =
  # For testing: Draw yellow circle at (400, 300), radius 50
  var cx: int32 = 400
  var cy: int32 = 300
  var radius: int32 = 50
  var color: int32 = 0xFFFF00  # Yellow

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

  # Midpoint circle algorithm
  var x: int32 = 0
  var y: int32 = radius
  var d: int32 = 1 - radius

  while x <= y:
    draw_circle_points(fd, cx, cy, x, y, xres, yres, color, pixel)

    x = x + 1
    if d < 0:
      d = d + 2 * x + 1
    else:
      y = y - 1
      d = d + 2 * (x - y) + 1

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)

main()
