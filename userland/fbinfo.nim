# fbinfo - Display framebuffer information
# Shows resolution, color depth, and other FB parameters

const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_ioctl: int32 = 54
const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDOUT: int32 = 1
const O_RDWR: int32 = 2

const FBIOGET_VSCREENINFO: int32 = 0x4600

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32

proc print(msg: ptr uint8, len: int32) =
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_num(n: int32) =
  # Print a number (simplified - works for numbers < 10000)
  if n >= 1000:
    var thousands: uint8 = cast[uint8](48 + n / 1000)
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(thousands)), 1)
  if n >= 100:
    var hundreds: uint8 = cast[uint8](48 + n / 100 % 10)
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(hundreds)), 1)
  if n >= 10:
    var tens: uint8 = cast[uint8](48 + n / 10 % 10)
    discard syscall3(SYS_write, STDOUT, cast[int32](addr(tens)), 1)
  var ones: uint8 = cast[uint8](48 + n % 10)
  discard syscall3(SYS_write, STDOUT, cast[int32](addr(ones)), 1)

proc newline() =
  print(cast[ptr uint8]("\n"), 1)

proc main() =
  print(cast[ptr uint8]("PoodillionOS Framebuffer Info"), 30)
  newline()
  print(cast[ptr uint8]("============================="), 29)
  newline()

  # Open framebuffer
  var fd: int32 = syscall2(SYS_open, cast[int32]("/dev/fb0"), O_RDWR)
  if fd < 0:
    print(cast[ptr uint8]("Error: Cannot open /dev/fb0"), 28)
    newline()
    print(cast[ptr uint8]("Try: sudo chown $USER /dev/fb0"), 31)
    newline()
    discard syscall1(SYS_exit, 1)

  # Allocate buffer for ioctl (160 bytes for VScreenInfo struct)
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 160
  discard syscall1(SYS_brk, new_brk)
  var vinfo: ptr uint32 = cast[ptr uint32](old_brk)

  # Get screen info
  var result: int32 = syscall3(SYS_ioctl, fd, FBIOGET_VSCREENINFO, cast[int32](vinfo))
  if result < 0:
    print(cast[ptr uint8]("Error: Cannot get screen info"), 30)
    newline()
    discard syscall1(SYS_close, fd)
    discard syscall1(SYS_exit, 1)

  # Extract fields from vinfo struct
  # Fields are: xres(u32), yres(u32), xres_virtual(u32), yres_virtual(u32),
  #             xoffset(u32), yoffset(u32), bits_per_pixel(u32)...
  var xres: int32 = cast[int32](vinfo[0])
  var yres: int32 = cast[int32](vinfo[1])
  var xres_virt: int32 = cast[int32](vinfo[2])
  var yres_virt: int32 = cast[int32](vinfo[3])
  var bpp: int32 = cast[int32](vinfo[6])

  # Display info
  print(cast[ptr uint8]("Resolution: "), 12)
  print_num(xres)
  print(cast[ptr uint8](" x "), 3)
  print_num(yres)
  newline()

  print(cast[ptr uint8]("Bits per pixel: "), 16)
  print_num(bpp)
  newline()

  print(cast[ptr uint8]("Virtual resolution: "), 20)
  print_num(xres_virt)
  print(cast[ptr uint8](" x "), 3)
  print_num(yres_virt)
  newline()

  var total_pixels: int32 = xres * yres
  print(cast[ptr uint8]("Total pixels: "), 14)
  print_num(total_pixels)
  newline()

  var bytes_per_pixel: int32 = bpp / 8
  var fb_size: int32 = total_pixels * bytes_per_pixel
  print(cast[ptr uint8]("Framebuffer size: "), 18)
  print_num(fb_size / 1024)
  print(cast[ptr uint8](" KB"), 3)
  newline()

  # Close and exit
  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)
