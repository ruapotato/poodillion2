# date - Display or set date and time
# Uses SYS_time (13) to get Unix epoch seconds

const SYS_write: int32 = 4
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45
const SYS_time: int32 = 13

const STDOUT: int32 = 1
const STDERR: int32 = 2

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

# Print integer with leading zero padding to 2 digits
proc print_int_pad2(n: int32) =
  if n < 10:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)

  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n
  var temp: int32 = num
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var pos: int32 = digits
  buf[pos] = cast[uint8](0)
  pos = pos - 1

  temp = num
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  print(buf)

# Print integer without padding
proc print_int(n: int32) =
  if n == 0:
    discard syscall3(SYS_write, STDOUT, cast[int32]("0"), 1)
    return

  var num: int32 = n
  var temp: int32 = num
  var digits: int32 = 0
  while temp > 0:
    digits = digits + 1
    temp = temp / 10

  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 32
  discard syscall1(SYS_brk, new_brk)
  var buf: ptr uint8 = cast[ptr uint8](old_brk)

  var pos: int32 = digits
  buf[pos] = cast[uint8](0)
  pos = pos - 1

  temp = num
  while temp > 0:
    var digit: int32 = temp % 10
    buf[pos] = cast[uint8](48 + digit)
    pos = pos - 1
    temp = temp / 10

  print(buf)

# Check if year is leap year
proc is_leap_year(year: int32): int32 =
  if (year % 4) != 0:
    return 0
  if (year % 100) != 0:
    return 1
  if (year % 400) != 0:
    return 0
  return 1

# Get days in month
proc days_in_month(month: int32, year: int32): int32 =
  if month == 1:
    return 31
  if month == 2:
    var leap: int32 = is_leap_year(year)
    if leap == 1:
      return 29
    else:
      return 28
  if month == 3:
    return 31
  if month == 4:
    return 30
  if month == 5:
    return 31
  if month == 6:
    return 30
  if month == 7:
    return 31
  if month == 8:
    return 31
  if month == 9:
    return 30
  if month == 10:
    return 31
  if month == 11:
    return 30
  if month == 12:
    return 31
  return 30

# Get month name (3 letter abbreviation)
proc get_month_name(month: int32): ptr uint8 =
  if month == 1:
    return cast[ptr uint8]("Jan")
  if month == 2:
    return cast[ptr uint8]("Feb")
  if month == 3:
    return cast[ptr uint8]("Mar")
  if month == 4:
    return cast[ptr uint8]("Apr")
  if month == 5:
    return cast[ptr uint8]("May")
  if month == 6:
    return cast[ptr uint8]("Jun")
  if month == 7:
    return cast[ptr uint8]("Jul")
  if month == 8:
    return cast[ptr uint8]("Aug")
  if month == 9:
    return cast[ptr uint8]("Sep")
  if month == 10:
    return cast[ptr uint8]("Oct")
  if month == 11:
    return cast[ptr uint8]("Nov")
  if month == 12:
    return cast[ptr uint8]("Dec")
  return cast[ptr uint8]("???")

# Get day of week name (3 letter abbreviation)
proc get_day_name(day: int32): ptr uint8 =
  if day == 0:
    return cast[ptr uint8]("Thu")
  if day == 1:
    return cast[ptr uint8]("Fri")
  if day == 2:
    return cast[ptr uint8]("Sat")
  if day == 3:
    return cast[ptr uint8]("Sun")
  if day == 4:
    return cast[ptr uint8]("Mon")
  if day == 5:
    return cast[ptr uint8]("Tue")
  if day == 6:
    return cast[ptr uint8]("Wed")
  return cast[ptr uint8]("???")

proc main() =
  # Get current time (Unix epoch seconds)
  var epoch: int32 = syscall1(SYS_time, 0)

  if epoch < 0:
    print(cast[ptr uint8]("date: cannot get time\n"))
    discard syscall1(SYS_exit, 1)

  # Calculate date/time from epoch
  # Unix epoch starts at Jan 1, 1970 00:00:00 UTC (Thursday)

  var seconds: int32 = epoch % 60
  var minutes: int32 = (epoch / 60) % 60
  var hours: int32 = (epoch / 3600) % 24
  var total_days: int32 = epoch / 86400

  # Calculate day of week (epoch starts on Thursday = 0)
  var day_of_week: int32 = (total_days + 4) % 7

  # Calculate year, month, day
  var year: int32 = 1970
  var days_left: int32 = total_days

  # Skip complete years
  var days_in_year: int32 = 365
  while days_left >= days_in_year:
    days_left = days_left - days_in_year
    year = year + 1
    var leap: int32 = is_leap_year(year)
    if leap == 1:
      days_in_year = 366
    else:
      days_in_year = 365

  # Calculate month and day
  var month: int32 = 1
  var dim: int32 = days_in_month(month, year)
  while days_left >= dim:
    days_left = days_left - dim
    month = month + 1
    dim = days_in_month(month, year)

  var day: int32 = days_left + 1

  # Format: "Wed Dec 18 12:34:56 2024" or simpler "2024-12-18 12:34:56"
  # Using simpler format for easier parsing

  # Print day name
  print(get_day_name(day_of_week))
  print(cast[ptr uint8](" "))

  # Print month name
  print(get_month_name(month))
  print(cast[ptr uint8](" "))

  # Print day
  if day < 10:
    print(cast[ptr uint8](" "))
  print_int(day)
  print(cast[ptr uint8](" "))

  # Print time HH:MM:SS
  print_int_pad2(hours)
  print(cast[ptr uint8](":"))
  print_int_pad2(minutes)
  print(cast[ptr uint8](":"))
  print_int_pad2(seconds)
  print(cast[ptr uint8](" "))

  # Print year
  print_int(year)
  print(cast[ptr uint8]("\n"))

  discard syscall1(SYS_exit, 0)
