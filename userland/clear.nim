# clear - Clear framebuffer to a solid color
# Usage: clear [color_hex]
# Example: clear 0xFF0000  (red screen)

const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_ioctl: int32 = 54
const SYS_mmap: int32 = 90
const SYS_munmap: int32 = 91
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

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

proc print(msg: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc main() =
  # Default color: black
  var color: uint32 = 0x000000

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
  var xres: int32 = cast[int32](vinfo[0])
  var yres: int32 = cast[int32](vinfo[1])
  var bpp: int32 = cast[int32](vinfo[6])
  var bytes_per_pixel: int32 = bpp / 8
  var screen_size: int32 = xres * yres * bytes_per_pixel

  # Memory map framebuffer
  var prot: int32 = PROT_READ | PROT_WRITE
  var fb_ptr: ptr uint32 = cast[ptr uint32](syscall6(SYS_mmap, 0, screen_size, prot, MAP_SHARED, fd, 0))

  if cast[int32](fb_ptr) < 0:
    print(cast[ptr uint8]("Error: Cannot mmap framebuffer\n"), 32)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  # Clear screen by writing color to every pixel
  var total_pixels: int32 = xres * yres
  var i: int32 = 0
  while i < total_pixels:
    fb_ptr[i] = color
    i = i + 1

  print(cast[ptr uint8]("Screen cleared!\n"), 16)

  # Cleanup
  discard syscall2(SYS_munmap, cast[int32](fb_ptr), screen_size)
  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)
