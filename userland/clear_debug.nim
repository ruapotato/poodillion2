# clear_debug - Clear screen by writing directly to framebuffer

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
  print(cast[ptr uint8]("Clearing screen...\n"), 19)

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

  # Allocate buffer for one line (4096 bytes = 1024 pixels)
  var buffer_brk: int32 = syscall1(SYS_brk, 0)
  var buffer_size: int32 = 4096
  discard syscall1(SYS_brk, buffer_brk + buffer_size)
  var buffer: ptr uint32 = cast[ptr uint32](buffer_brk)

  # Fill buffer with black (0x00000000)
  var i: int32 = 0
  while i < buffer_size / 4:
    buffer[i] = 0x00000000
    i = i + 1

  # Seek to start of framebuffer
  discard syscall3(SYS_lseek, fd, 0, SEEK_SET)

  # Write buffer repeatedly to clear entire screen
  var written: int32 = 0
  while written < screen_size:
    var to_write: int32 = buffer_size
    if written + to_write > screen_size:
      to_write = screen_size - written

    var bytes_written: int32 = syscall3(SYS_write, fd, cast[int32](buffer), to_write)
    if bytes_written <= 0:
      print(cast[ptr uint8]("Error: Write failed\n"), 20)
      discard syscall1(SYS_close, fd)
      discard syscall1(SYS_exit, 1)

    written = written + bytes_written

  print(cast[ptr uint8]("Screen cleared!\n"), 16)

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)

main()
