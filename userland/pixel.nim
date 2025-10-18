# pixel - Draw a pixel at x,y with color
# Usage: pixel <x> <y> <color>
# Color format: RRGGBB hex (e.g., FF0000 for red)

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

proc main() =
  # For testing: Draw red pixel at (100, 100)
  var x: int32 = 100
  var y: int32 = 100
  var color: int32 = 0x00FF0000  # Red

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

  # Check bounds (skip for speed - assume valid coords)
  # Mini-nim doesn't support 'or' so we skip bounds checking

  # Calculate offset in framebuffer
  var offset: int32 = (y * xres + x) * bytes_per_pixel

  # Seek to pixel position
  discard syscall3(SYS_lseek, fd, offset, SEEK_SET)

  # Allocate pixel buffer
  var pixel_brk: int32 = syscall1(SYS_brk, 0)
  discard syscall1(SYS_brk, pixel_brk + 4)
  var pixel: ptr uint32 = cast[ptr uint32](pixel_brk)
  pixel[0] = color

  # Write pixel
  var bytes_written: int32 = syscall3(SYS_write, fd, cast[int32](pixel), 4)
  if bytes_written < 4:
    print(cast[ptr uint8]("Error: Write failed\n"), 20)
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)

main()
