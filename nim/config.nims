# Nim configuration for bare-metal kernel compilation

# No standard library
switch("os", "standalone")
switch("gc", "none")
switch("mm", "none")
switch("threads", "off")

# Compiler flags for freestanding
switch("passC", "-ffreestanding")
switch("passC", "-nostdlib")
switch("passC", "-fno-stack-protector")
switch("passC", "-m32")
switch("passC", "-O2")

# Don't use standard library
switch("define", "danger")
switch("define", "noSignalHandler")
switch("define", "useMalloc")

# Output C code for inspection
switch("nimcache", "nimcache")
