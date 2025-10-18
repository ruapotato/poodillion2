# demo - Graphics demonstration
# Draws colorful shapes to show off framebuffer capabilities

const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_ioctl: int32 = 54
const SYS_mmap: int32 = 90
const SYS_munmap: int32 = 91
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_nanosleep: int32 = 162

const STDOUT: int32 = 1
const O_RDWR: int32 = 2
const PROT_READ: int32 = 1
const PROT_WRITE: int32 = 2
const MAP_SHARED: int32 = 1
const FBIOGET_VSCREENINFO: int32 = 0x4600

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc syscall6(num: int32, arg1: int32, arg2: int32, arg3: int32, arg4: int32, arg5: int32, arg6: int32): int32

# Global framebuffer state
var fb_ptr: ptr uint32
var screen_width: int32
var screen_height: int32

proc print(msg: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

# Plot a single pixel (with bounds checking)
proc pixel(x: int32, y: int32, color: uint32) =
  if x < 0:
    return
  if x >= screen_width:
    return
  if y < 0:
    return
  if y >= screen_height:
    return
  var offset: int32 = y * screen_width + x
  fb_ptr[offset] = color

# Draw filled rectangle
proc rect(x: int32, y: int32, w: int32, h: int32, color: uint32) =
  var row: int32 = 0
  while row < h:
    var col: int32 = 0
    while col < w:
      pixel(x + col, y + row, color)
      col = col + 1
    row = row + 1

# Draw horizontal line
proc hline(x1: int32, x2: int32, y: int32, color: uint32) =
  var x: int32 = x1
  while x <= x2:
    pixel(x, y, color)
    x = x + 1

# Draw vertical line
proc vline(x: int32, y1: int32, y2: int32, color: uint32) =
  var y: int32 = y1
  while y <= y2:
    pixel(x, y, color)
    y = y + 1

# Draw simple line (not perfect but works)
proc line(x0: int32, y0: int32, x1: int32, y1: int32, color: uint32) =
  var dx: int32 = x1 - x0
  var dy: int32 = y1 - y0

  if dx < 0:
    dx = 0 - dx
  if dy < 0:
    dy = 0 - dy

  if dy == 0:
    if x0 < x1:
      hline(x0, x1, y0, color)
    if x0 >= x1:
      hline(x1, x0, y0, color)
    return

  if dx == 0:
    if y0 < y1:
      vline(x0, y0, y1, color)
    if y0 >= y1:
      vline(x0, y1, y0, color)
    return

  var steps: int32 = dx
  if dy > dx:
    steps = dy

  var i: int32 = 0
  while i <= steps:
    var x: int32 = x0 + i * (x1 - x0) / steps
    var y: int32 = y0 + i * (y1 - y0) / steps
    pixel(x, y, color)
    i = i + 1

# Draw circle (midpoint algorithm simplified)
proc circle(cx: int32, cy: int32, radius: int32, color: uint32) =
  var x: int32 = 0 - radius
  while x <= radius:
    var y: int32 = 0 - radius
    while y <= radius:
      if x * x + y * y <= radius * radius:
        pixel(cx + x, cy + y, color)
      y = y + 1
    x = x + 1

proc main() =
  print(cast[ptr uint8]("PoodillionOS Graphics Demo\n"), 27)
  print(cast[ptr uint8]("=========================\n"), 26)

  # Open framebuffer
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

  # Extract screen parameters
  screen_width = cast[int32](vinfo[0])
  screen_height = cast[int32](vinfo[1])
  var bpp: int32 = cast[int32](vinfo[6])
  var bytes_per_pixel: int32 = bpp / 8
  var screen_size: int32 = screen_width * screen_height * bytes_per_pixel

  # Memory map framebuffer
  var prot: int32 = PROT_READ | PROT_WRITE
  fb_ptr = cast[ptr uint32](syscall6(SYS_mmap, 0, screen_size, prot, MAP_SHARED, fd, 0))

  if cast[int32](fb_ptr) < 0:
    print(cast[ptr uint8]("Error: Cannot mmap framebuffer\n"), 32)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  print(cast[ptr uint8]("Drawing graphics...\n"), 20)

  # Clear to black
  var i: int32 = 0
  var total_pixels: int32 = screen_width * screen_height
  while i < total_pixels:
    fb_ptr[i] = 0x000000
    i = i + 1

  # Draw some colorful rectangles
  rect(50, 50, 200, 150, 0xFF0000)      # Red rectangle
  rect(300, 50, 200, 150, 0x00FF00)     # Green rectangle
  rect(550, 50, 200, 150, 0x0000FF)     # Blue rectangle

  # Draw some lines
  line(50, 250, 750, 250, 0xFFFFFF)     # White horizontal line
  line(400, 50, 400, 500, 0xFFFF00)     # Yellow vertical line
  line(50, 300, 750, 500, 0xFF00FF)     # Magenta diagonal line

  # Draw circles
  circle(150, 400, 50, 0xFF8800)        # Orange circle
  circle(400, 400, 75, 0x00FFFF)        # Cyan circle
  circle(650, 400, 60, 0xFF0088)        # Pink circle

  # Draw border around screen
  hline(0, screen_width - 1, 0, 0xFFFFFF)
  hline(0, screen_width - 1, screen_height - 1, 0xFFFFFF)
  vline(0, 0, screen_height - 1, 0xFFFFFF)
  vline(screen_width - 1, 0, screen_height - 1, 0xFFFFFF)

  print(cast[ptr uint8]("Graphics drawn!\n"), 16)
  print(cast[ptr uint8]("Shapes: rectangles, lines, circles\n"), 36)

  # Cleanup
  discard syscall2(SYS_munmap, cast[int32](fb_ptr), screen_size)
  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)
