# tsort - Topological sort
# Usage: tsort [FILE]
# Reads pairs "A B" meaning A depends on B
# Outputs sorted order, detects cycles

const SYS_read: int32 = 3
const SYS_write: int32 = 4
const SYS_open: int32 = 5
const SYS_close: int32 = 6
const SYS_exit: int32 = 1
const SYS_brk: int32 = 45

const STDIN: int32 = 0
const STDOUT: int32 = 1
const STDERR: int32 = 2

const O_RDONLY: int32 = 0

extern proc syscall1(num: int32, arg1: int32): int32
extern proc syscall2(num: int32, arg1: int32, arg2: int32): int32
extern proc syscall3(num: int32, arg1: int32, arg2: int32, arg3: int32): int32
extern proc get_argc(): int32
extern proc get_argv(index: int32): ptr uint8

proc strlen(s: ptr uint8): int32 =
  var i: int32 = 0
  while s[i] != cast[uint8](0):
    i = i + 1
  return i

proc print(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDOUT, cast[int32](msg), len)

proc print_err(msg: ptr uint8) =
  var len: int32 = strlen(msg)
  discard syscall3(SYS_write, STDERR, cast[int32](msg), len)

# Compare strings
proc strcmp(s1: ptr uint8, s2: ptr uint8): int32 =
  var i: int32 = 0
  while s1[i] != cast[uint8](0):
    if s1[i] != s2[i]:
      return 1
    i = i + 1
  if s2[i] != cast[uint8](0):
    return 1
  return 0

# Copy string
proc strcpy(dest: ptr uint8, src: ptr uint8) =
  var i: int32 = 0
  while src[i] != cast[uint8](0):
    dest[i] = src[i]
    i = i + 1
  dest[i] = cast[uint8](0)

# Node in dependency graph (max 64 nodes, 16 char names)
const MAX_NODES: int32 = 64
const NAME_LEN: int32 = 16

# Find or add node, return index
proc find_or_add_node(nodes: ptr uint8, node_count_ptr: ptr int32, name: ptr uint8): int32 =
  var node_count: int32 = node_count_ptr[0]
  var i: int32 = 0

  # Search for existing node
  while i < node_count:
    var node_name: ptr uint8 = cast[ptr uint8](cast[int32](nodes) + i * NAME_LEN)
    var cmp: int32 = strcmp(node_name, name)
    if cmp == 0:
      return i
    i = i + 1

  # Add new node
  if node_count >= MAX_NODES:
    return -1

  var new_node: ptr uint8 = cast[ptr uint8](cast[int32](nodes) + node_count * NAME_LEN)
  strcpy(new_node, name)
  node_count_ptr[0] = node_count + 1
  return node_count

# Parse input and build graph
# Returns 1 on success, 0 on error
proc parse_input(fd: int32, nodes: ptr uint8, edges: ptr int32, node_count_ptr: ptr int32, edge_count_ptr: ptr int32): int32 =
  # Allocate input buffer
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 8192
  discard syscall1(SYS_brk, new_brk)
  var buffer: ptr uint8 = cast[ptr uint8](old_brk)
  var word1: ptr uint8 = cast[ptr uint8](old_brk + 4096)
  var word2: ptr uint8 = cast[ptr uint8](old_brk + 4096 + 64)

  var bytes_read: int32 = syscall3(SYS_read, fd, cast[int32](buffer), 4096)
  if bytes_read <= 0:
    return 1

  var pos: int32 = 0
  while pos < bytes_read:
    # Skip whitespace
    while pos < bytes_read:
      if buffer[pos] == cast[uint8](32):
        pos = pos + 1
      else:
        if buffer[pos] == cast[uint8](9):
          pos = pos + 1
        else:
          if buffer[pos] == cast[uint8](10):
            pos = pos + 1
          else:
            break

    if pos >= bytes_read:
      break

    # Read first word
    var w1_len: int32 = 0
    while pos < bytes_read:
      if buffer[pos] != cast[uint8](32):
        if buffer[pos] != cast[uint8](9):
          if buffer[pos] != cast[uint8](10):
            word1[w1_len] = buffer[pos]
            w1_len = w1_len + 1
            pos = pos + 1
          else:
            break
        else:
          break
      else:
        break
    word1[w1_len] = cast[uint8](0)

    if w1_len == 0:
      break

    # Skip whitespace
    while pos < bytes_read:
      if buffer[pos] == cast[uint8](32):
        pos = pos + 1
      else:
        if buffer[pos] == cast[uint8](9):
          pos = pos + 1
        else:
          break

    # Read second word
    var w2_len: int32 = 0
    while pos < bytes_read:
      if buffer[pos] != cast[uint8](32):
        if buffer[pos] != cast[uint8](9):
          if buffer[pos] != cast[uint8](10):
            word2[w2_len] = buffer[pos]
            w2_len = w2_len + 1
            pos = pos + 1
          else:
            break
        else:
          break
      else:
        break
    word2[w2_len] = cast[uint8](0)

    if w2_len == 0:
      break

    # Add nodes and edge
    var node1: int32 = find_or_add_node(nodes, node_count_ptr, word1)
    var node2: int32 = find_or_add_node(nodes, node_count_ptr, word2)

    if node1 < 0:
      return 0
    if node2 < 0:
      return 0

    # Store edge (node1 depends on node2)
    var edge_count: int32 = edge_count_ptr[0]
    var edge_ptr: ptr int32 = cast[ptr int32](cast[int32](edges) + edge_count * 8)
    edge_ptr[0] = node1
    edge_ptr[1] = node2
    edge_count_ptr[0] = edge_count + 1

  return 1

# Topological sort using Kahn's algorithm
proc topo_sort(nodes: ptr uint8, edges: ptr int32, node_count: int32, edge_count: int32, in_degree: ptr int32, output: ptr int32): int32 =
  # Calculate in-degrees
  var i: int32 = 0
  while i < node_count:
    in_degree[i] = 0
    i = i + 1

  i = 0
  while i < edge_count:
    var edge_ptr: ptr int32 = cast[ptr int32](cast[int32](edges) + i * 8)
    var from: int32 = edge_ptr[0]
    var to: int32 = edge_ptr[1]
    in_degree[from] = in_degree[from] + 1
    i = i + 1

  # Find nodes with no incoming edges (queue)
  var queue: ptr int32 = output
  var queue_start: int32 = 0
  var queue_end: int32 = 0

  i = 0
  while i < node_count:
    if in_degree[i] == 0:
      queue[queue_end] = i
      queue_end = queue_end + 1
    i = i + 1

  var sorted_count: int32 = 0

  # Process queue
  while queue_start < queue_end:
    var node: int32 = queue[queue_start]
    queue_start = queue_start + 1
    sorted_count = sorted_count + 1

    # Output this node
    var node_name: ptr uint8 = cast[ptr uint8](cast[int32](nodes) + node * NAME_LEN)
    print(node_name)
    print(cast[ptr uint8]("\n"))

    # Remove edges from this node
    i = 0
    while i < edge_count:
      var edge_ptr: ptr int32 = cast[ptr int32](cast[int32](edges) + i * 8)
      var from: int32 = edge_ptr[0]
      var to: int32 = edge_ptr[1]

      if to == node:
        in_degree[from] = in_degree[from] - 1
        if in_degree[from] == 0:
          queue[queue_end] = from
          queue_end = queue_end + 1

      i = i + 1

  # Check for cycles
  if sorted_count < node_count:
    return 0

  return 1

proc main() =
  var argc: int32 = get_argc()
  var fd: int32 = STDIN

  # Open file if provided
  if argc >= 2:
    var filename: ptr uint8 = get_argv(1)
    fd = syscall3(SYS_open, cast[int32](filename), O_RDONLY, 0)
    if fd < 0:
      print_err(cast[ptr uint8]("tsort: cannot open file\n"))
      discard syscall1(SYS_exit, 1)

  # Allocate data structures
  var old_brk: int32 = syscall1(SYS_brk, 0)
  var new_brk: int32 = old_brk + 16384
  discard syscall1(SYS_brk, new_brk)

  var nodes: ptr uint8 = cast[ptr uint8](old_brk)
  var edges: ptr int32 = cast[ptr int32](old_brk + 1024)
  var in_degree: ptr int32 = cast[ptr int32](old_brk + 5120)
  var output: ptr int32 = cast[ptr int32](old_brk + 5376)

  var node_count: int32 = 0
  var node_count_ptr: ptr int32 = cast[ptr int32](old_brk + 8192)
  node_count_ptr[0] = 0

  var edge_count: int32 = 0
  var edge_count_ptr: ptr int32 = cast[ptr int32](old_brk + 8196)
  edge_count_ptr[0] = 0

  # Parse input
  var parse_result: int32 = parse_input(fd, nodes, edges, node_count_ptr, edge_count_ptr)
  if parse_result == 0:
    print_err(cast[ptr uint8]("tsort: too many nodes\n"))
    discard syscall1(SYS_exit, 1)

  node_count = node_count_ptr[0]
  edge_count = edge_count_ptr[0]

  if fd != STDIN:
    discard syscall1(SYS_close, fd)

  # Perform topological sort
  var sort_result: int32 = topo_sort(nodes, edges, node_count, edge_count, in_degree, output)

  if sort_result == 0:
    print_err(cast[ptr uint8]("tsort: cycle detected\n"))
    discard syscall1(SYS_exit, 1)

  discard syscall1(SYS_exit, 0)
