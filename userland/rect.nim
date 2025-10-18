# rect - Draw a rectangle
# Usage: rect <x> <y> <width> <height> <color> [fill]

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
  # For testing: Draw filled blue rectangle at (50, 50), 100x80
  var x: int32 = 50
  var y: int32 = 50
  var width: int32 = 100
  var height: int32 = 80
  var color: int32 = 0x0000FF  # Blue
  var fill: int32 = 1  # 1 = filled, 0 = outline

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

  # Allocate line buffer (max 4KB = 1024 pixels)
  var buffer_brk: int32 = syscall1(SYS_brk, 0)
  var buffer_size: int32 = 4096
  discard syscall1(SYS_brk, buffer_brk + buffer_size)
  var buffer: ptr uint32 = cast[ptr uint32](buffer_brk)

  # Fill buffer with color
  var i: int32 = 0
  while i < buffer_size / 4:
    buffer[i] = color
    i = i + 1

  # Draw filled rectangle line by line
  if fill == 1:
    var row: int32 = 0
    while row < height:
      var py: int32 = y + row
      if py >= 0 and py < yres:
        var px: int32 = x
        if px < 0:
          px = 0
        var pwidth: int32 = width
        if px + pwidth > xres:
          pwidth = xres - px

        # Seek to line position
        var offset: int32 = (py * xres + px) * 4
        discard syscall3(SYS_lseek, fd, offset, SEEK_SET)

        # Write line
        var bytes_to_write: int32 = pwidth * 4
        discard syscall3(SYS_write, fd, cast[int32](buffer), bytes_to_write)

      row = row + 1

  discard syscall1(SYS_close, fd)
  discard syscall1(SYS_exit, 0)

main()
